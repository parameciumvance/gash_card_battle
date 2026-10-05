## Context

卡片效果目前由 `src/gash/engine/effects/{spells,mamodo,partners,events}.py` 以「一卡一函式 + 字串 key」實作。以 E-001 為例,一個效果被手動拆成三段:

```
e001 ──choose_or_auto(kind="e001_pick")──► e001_pick(驗證、取 slot)
        └─ schedule_standby(kind="start_phase", data={callback:"e001_fire", ...})
                                    engine.py 開始階段 ──► CHOICE_RESOLVERS["e001_fire"] ──► add_power
```

續體(「停下來之後接著做什麼」)由 `CHOICE_RESOLVERS` 的字串 key 與 `Standby.data["callback"]` 隱含地串接。這些 key 同時被引擎(`engine.py:256/964/1020/1117`)、前端 i18n(`choice.title.e009_pick` 等)與測試使用。

現況限制:

- 引擎狀態目前沒有序列化(無 `deepcopy` / `asdict` / `json` / `pickle`),但 todo 有 history / 重播,state 應維持純資料。
- 硬幣判定 `flip_coins` 內含 M-012 / M-019 的互動式重擲確認鏈,會在中途進入 pending。
- pending 的 resolver 拋出 `IllegalCommand` 時,引擎保留 pending 讓玩家重選,此行為需維持。
- `Standby.data["expires"]` 預設 `"turn"`(建立當回合結束即移除),`"next_start"` 表示存活到下回合開始階段。

## Goals / Non-Goals

**Goals:**

- 效果以不可變節點組成的「效果樹」描述,節點命名語意化、不含卡號。
- 停點的續體存為純資料 `(effect_id, path, ctx)`,不存閉包。
- 註冊層逐卡一行、依卡號排序;`source` 卡號在註冊時注入。
- 新舊並存,逐卡遷移,每批以既有 248 個測試回歸。
- `Choose` 依選項規格自動驗證與單一選項自動解決。

**Non-Goals:**

- 不遷移全部卡片:本 change 只做直譯器骨架、E-001、擲幣類卡片(S-004 / S-014 / S-021 / S-025 / S-026)。
- 不改前端、i18n、API 格式;`choice.title.*` 改為依節點種類另案處理。
- 不改任何遊戲規則與可觀察行為。
- 不做 `>>` 串接式 DSL,只用呼叫式節點。

## Decisions

### 1. 節點為 frozen dataclass,樹是資料

每種節點是 `@dataclass(frozen=True)`,子節點放在欄位裡(`then`、`steps`)。整棵樹在註冊時建好,存入 `EFFECTS[effect_id]`。

- **替代方案:閉包 / lambda 組合(做法 A)。** 實作最簡單,但停點時必須把閉包存進 state,state 不再是純資料,history / 重播會被卡住。故不採用。
- **代價:** 節點不能夾帶任意 lambda。無法用通用節點表達的邏輯,以「專屬節點」處理(節點類別本身仍是資料,行為寫在其 `run` 內)。

### 2. 續體 = `(effect_id, path, ctx)`

- `effect_id`:字串,格式 `"<卡號>:<掛鉤>"`(例:`"E-001:event"`),由註冊層產生,對應 `EFFECTS` 中的樹。
- `path`:從根節點往下的子節點索引 tuple,例如 `(0, 1)`。
- `ctx`:JSON 可序列化的 dict,至少含 `player`、`source`;`Choose(bind="slot")` 選到的值、擲幣結果 `results` 以名稱寫入。節點以 `Ref("slot")` 引用。

停點只存這三樣。醒來時 `resume` 依 `effect_id` 取樹、沿 `path` 找回節點、把玩家輸入 / 觸發資料寫入 `ctx` 後繼續往下跑。

### 3. 直譯器介面與控制流程

節點的 `run(game, batch, ctx, path)` 回傳 `DONE`(已完成,呼叫端可繼續同層下一個節點)或 `SUSPENDED`(已停下,續體已存入 state)。`resume(game, batch, value, data)` 為單一入口。

**子節點索引與 `path`。** 每個節點以固定順序暴露子節點(`Sequence.steps` 依序為 0…n-1;單子節點的 `then` 為 0;`Coin` 的 `then` 為 0、`otherwise` 為 1)。`path` 是**停點節點本身**的位置(從根到該節點的索引 tuple),不是「下一步」。

**續行規則(避免漏做 / 重做)。** 停點節點完成後,直譯器沿 `path` 由深往淺「上溯」:

1. 取得目前節點的父節點;若父節點是 `Sequence`,依序解決該節點**之後**尚未執行的兄弟節點;若父節點是單子節點容器(`Choose` / `Coin` 分支等),不需額外動作,繼續上溯。
2. 上溯途中任一節點回傳 `SUSPENDED`,即停止並存入新續體(`path` 為新的停點)。
3. 到達根節點即整個效果完成。

```
Sequence(A, Choose(..., then=B), C)      Choose 停下 → 存 path=(1,)
                                          玩家回應 → 執行 B(path=(1,0)) → 上溯到 Sequence → 執行 C
```

**同步 callback 只執行一次。** 沒有 M-012 / M-019 時,`flip_coins` 會在呼叫當下同步呼叫 callback。為避免「callback 內的 resume 上溯續行,`Coin.run` 返回後外層 `Sequence` 又續行」的重複執行,`Coin.run` 使用一個**行程內暫存、不進 state** 的 in-flight 記號:

1. `Coin.run` 在呼叫 `flip_coins` 前登記記號,callback payload 帶該記號。
2. `effect_tree_resume` 若發現記號仍在登記中(表示同步進入),只把結果寫入暫存並返回,**不上溯**。
3. `Coin.run` 在 `flip_coins` 返回後檢查暫存:有結果 → 視為同步完成,就地執行分支並回傳 `DONE`(由外層 `Sequence` 照常續行);無結果 → 已進入確認鏈 pending,回傳 `SUSPENDED`。
4. 非同步恢復時記號已不在登記中,`effect_tree_resume` 才執行分支並上溯。

**`Standby` 是脫離式(detached)續體。** `Standby.run` 排程完成後立即回傳 `DONE`,外層 `Sequence` 不等待觸發、照常續行。觸發時只解決 `Standby.then` 子樹,**不再上溯**到祖先(續體標記 `detached=True`),避免把「排程當下」與「觸發當下」兩種生命週期混在一起。

**停點與既有機制的對應,以及 pending 分派標記。** 三種停點使用**不同**的資料鍵,引擎只依專屬標記分派,不能只檢查續體是否存在(否則會跳過 M-012 / M-019 確認 resolver):

| 停點 | 建立的 pending / 待命 | 續體鍵 | 引擎如何分派 |
|---|---|---|---|
| `Choose` | `PendingChoice(kind=<prompt>)` | `data["tree_choice"]` | `choose` 指令處理(`engine.py:1117` 附近)**僅**在 `pending.data` 含 `tree_choice` 時呼叫 `resume`;否則維持依 `pending.kind` 找 resolver |
| `Coin` | `flip_coins(..., callback="effect_tree_resume", data={"tree_cont": …})`;確認鏈可能建立 `opp_coin_redo` / `coin_confirm` pending | `data["tree_cont"]`(僅作為 callback payload) | 確認 pending 的 `kind` 為 `coin_confirm` / `opp_coin_redo`,依原 resolver 處理;確認鏈全部完成後,由 `flip_coins` 呼叫 callback `effect_tree_resume` 才回到樹 |
| `Standby` | `Standby(data={"callback": "effect_tree_resume", "tree_cont": …})` | `data["tree_cont"]` | 開始階段既有的 `CHOICE_RESOLVERS[callback]` |

`Choose.prompt` MUST NOT 與保留的 pending kind(`coin_confirm`、`opp_coin_redo`、`deploy_page` 等引擎內建 kind)相同;註冊時檢查並拒絕。`effect_tree_resume` 以 `CHOICE_RESOLVERS["effect_tree_resume"]` 註冊為單一通用 resolver。

### 4. 節點清單(本 change 需要的最小集合)

| 節點 | 作用 |
|---|---|
| `Sequence(steps=…)` | 依序解決子節點 |
| `Choose(target=<選項規格>, bind=…, prompt=…, then=…)` | 玩家選擇;選項規格自動產生選項與驗證;單一選項自動解決;`prompt` 為 pending `kind`(遷移期沿用既有 i18n key) |
| `Standby(at=<觸發時機>, expires=…, then=…)` | 排程待命(脫離式,見決策 3);觸發時只解決 `then`;`expires` 對應 `Standby.data["expires"]`(`"turn"` / `"next_start"`)。**`then` 子樹只能同步完成**(見決策 8) |
| `Coin(count=…, on=<結果條件>, then=…, otherwise=…)` | 擲幣並包住 M-012 / M-019 確認鏈,結果寫入 `ctx["results"]`,依條件分支 |
| `When(cond, then)` | 條件成立才解決 `then`;條件如 `SideIs("defense")` 讀 `ctx["side"]` |
| `AddPower(target=Ref("slot"), …)` / `RestrictOpponent` / `MakeNextAttackUndefendable` / `NegateAttack` | 包裝現有 `add_power` / `add_restriction` 等積木的葉節點;`AddPower` 執行時重新查找目標,見決策 9 |

每個節點宣告 `may_suspend`(是否可能停下):`Choose`、`Coin` 為真,葉節點為假,`Sequence` / `When` 依子節點推導。

選項規格(`OwnMamodo()` 等)與觸發時機(`NextStartPhase()`)也是 frozen dataclass,各自提供 `options(game, ctx)` / `validate` 或 `matches(...)`。

### 5. 註冊層

本次遷移的六張卡共用到四種掛鉤,每種都要有樹入口。`effect_id` 的 `<掛鉤>` 部分固定列舉如下,註冊時以 `(卡號, 掛鉤)` 檢查重複:

| 掛鉤(`effect_id` 後綴) | 註冊入口 | 既有表 / 引擎入口 | 包裝簽名 | 寫入 `ctx` | 用於 |
|---|---|---|---|---|---|
| `event` | `reg.event(number, effect=…, when=…)` | `EVENT` / `EVENT_CONDITION` | `fn(game, batch, player, page)` | `player`、`page`、`source` | E-001 |
| `rider.on_damage` | `reg.spell_rider(number, on_damage=<樹>)` | `SpellRider.on_damage`(`engine.py:1029`) | `fn(game, batch, player)` | `player`(效果擁有者)、`source` | S-004、S-014 |
| `rider.on_declare` | `reg.spell_rider(number, on_declare=<樹>)` | `SpellRider.on_declare`(`engine.py:625/688`) | `fn(game, batch, player, side)` | `player`、`side`(`"attack"` / `"defense"`)、`source` | S-021、S-025 |
| `spell_nonbattle` | `reg.spell_nonbattle(number, effect=<樹>)` | `SPELL_NONBATTLE`(`engine.py:434-443`) | `fn(game, batch, player)` | `player`、`source` | S-026 |

- 樹以直接呼叫形式註冊(既有裝飾器形式維持不變)。註冊時把樹存入 `EFFECTS`,並把薄包裝寫入上表的既有表;引擎入口與 S-026 的費用、時機、使用次數檢查因此完全沿用。
- `on_declare` 的 `side` 由包裝寫入 `ctx["side"]`,「僅防禦方」以 `When(SideIs("defense"), …)` 表達,不在包裝內硬寫。
- `source` 由註冊層寫入 `ctx["source"]`,節點內部一律讀 `ctx["source"]`,節點與函式名不含卡號。
- `reg.spell_rider` 每張卡只能呼叫一次(整筆記錄,不做部分更新):同一張卡再次呼叫(不論掛鉤或旗標)一律拒絕,避免整筆替換靜默清掉既有效果或旗標。所有檢查(樹驗證、掛鉤是否被佔用)先於任何寫入,失敗時 `TREE_HOOKS` / `EFFECTS` / `SPELL_RIDERS` 保持不變。
- 註冊檔逐卡一行、依卡號排序。

### 6. 擲幣的確定性

`Coin` 只在「第一次執行到該節點」時消耗 `game.rng` 做**初始擲幣**。resume 只從停點之後的節點繼續,不重跑之前的節點,因此不會有額外的初始擲幣。玩家合法要求的 M-012 / M-019 重擲仍照原流程消耗 RNG——「不重新擲幣」指的是效果樹恢復本身不得再擲,不是禁止重擲。

- **替代方案:每次 resume 從頭重播並快取結果。** 較容易實作續體,但會使 rng 消耗順序不可預測、且有副作用重複的風險。不採用。

### 7. 驗證失敗保留 pending

`Choose` 產生的驗證失敗時拋出 `IllegalCommand`(沿用現有錯誤碼與訊息),引擎既有邏輯(`engine.py:1117` 附近)會保留 pending。`resume` 不得在驗證前修改 state。

### 8. 本次 `Standby.then` 限定同步完成

現有開始階段(`engine.py:254-260`)會遍歷、移除並觸發所有到期待命,不檢查 callback 是否建立 pending,之後直接切換到戰鬥階段。若兩筆待命的 `then` 都會停下(`Choose` / `Coin`),第二筆會覆寫第一筆的 pending,續體遺失。

本次**不**把開始階段剩餘待命與階段切換改成可恢復流程,而是限定:`Standby.then` 子樹的 `may_suspend` 必須為假,註冊時檢查,違反者拋出明確錯誤。因此本次「開始階段不需修改引擎」的說法只在此限定範圍內成立;若日後要支援任意 `then`,需另案處理開始階段的可恢復流程。

- **替代方案:現在就支援任意 `then`。** 需要重構開始階段迴圈與階段切換,超出本次範圍且風險高。不採用。

### 9. 延遲效果的目標以 UID 綁定並於執行時重新檢查

`Choose(bind="slot")` 把選到的**穩定 slot UID** 寫入 `ctx["slot"]`(不是 slot 物件、不是索引)。`AddPower(target=Ref("slot"), …)` 於**執行當下**才以 `state.slot_by_uid(player, uid)` 重新查找;找不到(目標已離場)時**無效果、不建立 modifier、不發出任何事件**,也不得改選另一隻魔物。這保留 `e001_fire` 既有行為(`events.py:44-51`),而 `add_power` primitive 本身沒有這個檢查,所以檢查放在 `AddPower` 節點,不放進 primitive。

## Risks / Trade-offs

- **[並非每張卡都是乾淨的樹]** M-011(檢視對手魔本、`per_game` 限制)、S-043(融合 / 分裂二選一)、E-011(擲反面問是否付 MP 重擲)等需要專屬節點 → 只在通用節點組不出來時才新增專屬節點,並允許暫時保留舊寫法,不強求全部遷移。
- **[擲幣確認鏈整合]** `Coin` 需完整包住 M-012 / M-019 互動並可在中途停下 → 直接呼叫既有 `flip_coins`,只換 callback 為通用 resolver,續體用專屬鍵 `tree_cont`,`Choose` 用專屬鍵 `tree_choice`,兩者不混用(見決策 3)。**既有測試不足以證明等價**(沒有任何 M-019 / `opp_coin_redo` 案例,腳本 RNG 用完後固定回傳反面、抓不到額外消耗,`test_seed_reproducibility` 也只比較同一實作跑兩次),因此遷移前先補「特徵測試」固定行為,見 tasks 第 1 組。
- **[續體 path 與樹版本不一致]** 若樹在對局進行中被改動,舊 path 可能失效 → 房間狀態存在單一行程記憶體(重啟即清空),樹只在啟動時建立一次,實務上不會發生;直譯器遇到找不到節點時拋出明確錯誤而非靜默略過。
- **[兩套機制並存的認知負擔]** 舊 `@reg.xxx` 與樹並存期間,新增卡片可能寫回舊風格 → 在 README / 註冊檔開頭註明新卡一律用樹;遷移進度以 tasks 記錄。
- **[遷移期 `prompt` 仍含卡號]** 為不動前端,E-001 的 `Choose.prompt` 暫沿用 `"e001_pick"` → 這是刻意的過渡,待後續 change 統一改為依節點種類命名。

## Migration Plan

1. **先補特徵測試**:在遷移任何卡之前,對現行實作固定 M-019 / M-012 確認鏈、三種擲幣入口、E-001 目標離場等行為的事件序列與 pending 快照,並用會在超額呼叫時失敗的 RNG 驗證消耗次數。這些測試在遷移前後都必須通過。
2. 落地直譯器與節點,不遷移任何卡;既有與特徵測試全數通過。
3. 遷移 E-001,驗證 `Choose → Standby → AddPower` 整條路徑(含跨回合、`expires`、目標離場)。
4. 遷移擲幣類卡片(S-004 / S-014 / S-021 / S-025 / S-026),驗證 `Coin` 與確認鏈。
5. 每一步以完整測試套件回歸;任何一步失敗可單獨回退該卡的註冊行,改回舊裝飾器寫法。不涉及資料 / API 遷移,無需部署回滾計畫。

## Open Questions

- 本次只列舉六張卡用到的四種掛鉤(決策 5 的表)。魔物 / 搭檔的 `on_play`、`activated` 等掛鉤的 `effect_id` 命名,留待遷移那些卡時再依同一規則補入。
- `Choose` 的選項規格是否要支援「魔本頁面」「對手魔物」等更多來源?本 change 僅需 `OwnMamodo()`,其餘留待遷移其他卡時再加。
