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

### 3. 直譯器介面

`run(game, batch, effect_id, ctx, path=())` 從指定節點起解決;節點的 `run` 回傳「已完成」或「已停下」(停下時該節點已把續體存好)。`resume(game, batch, value, data)` 為單一入口,從 `data["cont"]` 取續體。

**停點對應現有機制,盡量不動引擎:**

| 停點 | 使用既有機制 | 引擎改動 |
|---|---|---|
| `Standby` | `Standby(kind=..., data={"callback": "effect_tree_resume", "cont": ...})`,開始階段(`engine.py:256`)原本就以 `CHOICE_RESOLVERS[callback]` 呼叫 | 無 |
| `Coin` | `flip_coins(..., callback="effect_tree_resume", data={"cont": ...})`,確認鏈結束後原本就呼叫 callback | 無 |
| `Choose` | `PendingChoice`,`kind` 為節點的 `prompt` | `choose` 指令處理(`engine.py:1117`)增加:若 `pending.data` 含 `cont`,改呼叫 `resume` |

`effect_tree_resume` 以 `CHOICE_RESOLVERS["effect_tree_resume"]` 註冊為單一通用 resolver。

### 4. 節點清單(本 change 需要的最小集合)

| 節點 | 作用 |
|---|---|
| `Sequence(steps=…)` | 依序解決子節點 |
| `Choose(target=<選項規格>, bind=…, prompt=…, then=…)` | 玩家選擇;選項規格自動產生選項與驗證;單一選項自動解決;`prompt` 為 pending `kind`(遷移期沿用既有 i18n key) |
| `Standby(at=<觸發時機>, expires=…, then=…)` | 排程待命,觸發時從 `then` 繼續;`expires` 對應 `Standby.data["expires"]`(`"turn"` / `"next_start"`) |
| `Coin(count=…, on=<結果條件>, then=…, otherwise=…)` | 擲幣並包住 M-012 / M-019 確認鏈,結果寫入 `ctx["results"]`,依條件分支 |
| `AddPower` / `Restrict` / `MakeUndefendable` / `NegateAttack` | 包裝現有 `add_power` / `add_restriction` 等積木的葉節點 |

選項規格(`OwnMamodo()` 等)與觸發時機(`NextStartPhase()`)也是 frozen dataclass,各自提供 `options(game, ctx)` / `validate` 或 `matches(...)`。

### 5. 註冊層

- 樹以 `reg.event("E-001", when=<條件>, effect=<樹>)` 形式直接呼叫註冊(既有裝飾器形式維持不變)。註冊時把樹存入 `EFFECTS`,並把一個薄包裝寫入既有表(`EVENT["E-001"] = lambda game, batch, player, page: run(...)`),引擎的入口因此不需改動。
- 術卡附加效果沿用 `SPELL_RIDERS`:`reg.spell_rider("S-004", on_damage=<樹>)`,由註冊層把樹包成既有 `SpellRider` 期待的 `fn(game, batch, player)`。
- `source` 由註冊層寫入 `ctx["source"]`,節點內部一律讀 `ctx["source"]`,節點與函式名不含卡號。
- 註冊檔逐卡一行、依卡號排序。

### 6. 擲幣的確定性

`Coin` 只在「第一次執行到該節點」時消耗 `game.rng`。resume 只從停點之後的節點繼續,不重跑之前的節點,因此固定 seed 的既有測試序列不變。

- **替代方案:每次 resume 從頭重播並快取結果。** 較容易實作續體,但會使 rng 消耗順序不可預測、且有副作用重複的風險。不採用。

### 7. 驗證失敗保留 pending

`Choose` 產生的驗證失敗時拋出 `IllegalCommand`(沿用現有錯誤碼與訊息),引擎既有邏輯(`engine.py:1117` 附近)會保留 pending。`resume` 不得在驗證前修改 state。

## Risks / Trade-offs

- **[並非每張卡都是乾淨的樹]** M-011(檢視對手魔本、`per_game` 限制)、S-043(融合 / 分裂二選一)、E-011(擲反面問是否付 MP 重擲)等需要專屬節點 → 只在通用節點組不出來時才新增專屬節點,並允許暫時保留舊寫法,不強求全部遷移。
- **[擲幣確認鏈整合]** `Coin` 需完整包住 M-012 / M-019 互動並可在中途停下 → 直接呼叫既有 `flip_coins`,只換 callback 為通用 resolver;以既有涉及 M-012 / M-019 的測試回歸。
- **[續體 path 與樹版本不一致]** 若樹在對局進行中被改動,舊 path 可能失效 → 房間狀態存在單一行程記憶體(重啟即清空),樹只在啟動時建立一次,實務上不會發生;直譯器遇到找不到節點時拋出明確錯誤而非靜默略過。
- **[兩套機制並存的認知負擔]** 舊 `@reg.xxx` 與樹並存期間,新增卡片可能寫回舊風格 → 在 README / 註冊檔開頭註明新卡一律用樹;遷移進度以 tasks 記錄。
- **[遷移期 `prompt` 仍含卡號]** 為不動前端,E-001 的 `Choose.prompt` 暫沿用 `"e001_pick"` → 這是刻意的過渡,待後續 change 統一改為依節點種類命名。

## Migration Plan

1. 先落地直譯器與節點,不遷移任何卡;既有測試全數通過。
2. 遷移 E-001,驗證 `Choose → Standby → AddPower` 整條路徑(含跨回合與 `expires`)。
3. 遷移擲幣類卡片(S-004 / S-014 / S-021 / S-025 / S-026),驗證 `Coin` 與確認鏈。
4. 每一步以完整測試套件回歸;任何一步失敗可單獨回退該卡的註冊行,改回舊裝飾器寫法。不涉及資料 / API 遷移,無需部署回滾計畫。

## Open Questions

- 一張卡有多個掛鉤時(如魔物同時有 `on_play` 與 `activated`),`effect_id` 的 `<掛鉤>` 命名是否需要統一列舉?暫以註冊表名稱(`event` / `on_play` / `activated` / `rider.on_damage` …)為準,實作時視需要收斂。
- `Choose` 的選項規格是否要支援「魔本頁面」「對手魔物」等更多來源?本 change 僅需 `OwnMamodo()`,其餘留待遷移其他卡時再加。
