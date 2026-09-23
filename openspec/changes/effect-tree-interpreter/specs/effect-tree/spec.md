## ADDED Requirements

### Requirement: 效果以不可變節點樹描述
系統 SHALL 提供效果樹:效果由不可變(frozen)節點組合而成,節點命名 MUST 以語意為主、不含卡號;卡號 MUST 僅出現在註冊處。效果樹 SHALL 在註冊時建立並存入 `EFFECTS[effect_id]`,對局期間不得被修改。

#### Scenario: 節點與函式名不含卡號
- **WHEN** 檢視效果樹節點類別與其建構函式名稱
- **THEN** 名稱皆為語意命名(如 `Choose`、`Standby`、`AddPower`),不含 `e001` 這類卡號

#### Scenario: source 由註冊層注入
- **WHEN** 以 `reg.event("E-001", effect=<樹>)` 註冊並使用該卡
- **THEN** 直譯器的 `ctx["source"]` 為 `"E-001"`,樹內節點不需自行寫入卡號

### Requirement: 停點續體為純資料
效果解決過程中遇到停點(等待玩家選擇、擲幣確認、待命)時,系統 SHALL 僅儲存 `(effect_id, path, ctx)` 作為續體,MUST NOT 儲存閉包或函式物件於遊戲狀態。`ctx` MUST 僅含可 JSON 序列化的值。

#### Scenario: 停點時狀態可序列化
- **WHEN** 效果因 `Choose` 進入 pending
- **THEN** `PendingChoice.data["tree_choice"]` 只含 `effect_id`(字串)、`path`(整數 tuple)與 JSON 可序列化的 `ctx`

#### Scenario: 從停點之後繼續
- **WHEN** 玩家回應 `Choose` 的 pending
- **THEN** 直譯器依 `effect_id` 與 `path` 找回該節點,把選擇值寫入 `ctx` 後,只解決該節點之後的節點,不重跑之前的節點

#### Scenario: 續體經序列化往返後仍可恢復
- **WHEN** 停點的續體經 `json.dumps` 再 `json.loads` 後交給 `resume`
- **THEN** 效果照常繼續,結果與未經序列化相同

### Requirement: 停點完成後上溯續行外層節點
停點節點完成後,直譯器 SHALL 沿 `path` 由深往淺上溯:父節點為 `Sequence` 時,依序解決該節點之後尚未執行的兄弟節點,再繼續上溯;上溯途中再次遇到停點時,MUST 存入新續體並停止。每個節點的副作用 MUST 恰好執行一次,不得漏做或重做。擲幣的同步 callback(無 M-012 / M-019 時立即回呼)MUST NOT 造成外層 `Sequence` 重複續行。

#### Scenario: Choose 之後的兄弟節點仍會執行
- **WHEN** `Sequence(A, Choose(…, then=B), C)` 在 `Choose` 停下,玩家回應
- **THEN** 依序執行 B、C,A 不會重做

#### Scenario: 連續兩次 Choose
- **WHEN** 一個效果依序包含兩個 `Choose`
- **THEN** 第一次回應後進入第二個 pending,第二次回應後才完成,兩次選擇值分別綁定於各自的名稱

#### Scenario: 巢狀 Sequence
- **WHEN** 內層 `Sequence` 中的 `Choose` 停下,外層 `Sequence` 在內層之後還有節點
- **THEN** 回應後內層剩餘節點與外層剩餘節點皆依序執行各一次

#### Scenario: Coin 同步完成時外層節點只執行一次
- **WHEN** `Sequence(A, Coin(…), B)` 執行時雙方場上皆無 M-012 / M-019
- **THEN** A、Coin 分支、B 各執行一次

#### Scenario: Coin 進入確認鏈時外層節點只執行一次
- **WHEN** `Sequence(A, Coin(…), B)` 執行時自己場上有可用 M-012,玩家於確認 pending 選擇保留
- **THEN** A 只在停點之前執行一次,Coin 分支與 B 在確認結束後各執行一次

### Requirement: pending 依專屬標記分派
系統 SHALL 僅在 `PendingChoice` 由效果樹的 `Choose` 節點建立(`pending.data` 含專屬鍵 `tree_choice`)時,把玩家回應交給 `resume`。`Coin` 與 `Standby` 攜帶的續體 MUST 使用不同的鍵(`tree_cont`),只作為 callback payload;內部確認 pending(`coin_confirm`、`opp_coin_redo`)MUST 依 `pending.kind` 交給原 resolver。`Choose` 的 `prompt` MUST NOT 與引擎保留的 pending kind 相同,註冊時檢查並拒絕。

#### Scenario: 確認 pending 不被誤送進樹
- **WHEN** 效果樹的 `Coin` 造成 `coin_confirm` pending,玩家回應保留(`None`)或重擲第幾枚(整數)
- **THEN** 由既有 M-012 resolver 處理(含能力消耗與重擲事件),確認鏈結束後才回到樹

#### Scenario: M-019 串接 M-012
- **WHEN** 對手場上有可用 M-019、玩家場上有可用 M-012,效果樹擲幣
- **THEN** 依序出現 `opp_coin_redo`(決策者為對手)與 `coin_confirm`(決策者為玩家)兩個 pending,各自依原流程解決,最後才進入樹的分支

#### Scenario: 保留 kind 被拒絕
- **WHEN** 註冊一個 `Choose(prompt="coin_confirm")`
- **THEN** 註冊時拋出錯誤

### Requirement: Choose 節點自動驗證與自動解決
`Choose` 節點 SHALL 依選項規格自動產生選項與驗證:僅有一個選項時 MUST 自動解決、不進入 pending;有多個選項時進入 pending;玩家回應的值不在選項內時 MUST 拒絕並保留 pending,不得修改遊戲狀態。

#### Scenario: 單一選項自動解決
- **WHEN** 玩家使用 E-001,場上僅有 1 隻魔物
- **THEN** 不產生 pending,直接以該魔物繼續解決後續節點

#### Scenario: 多個選項進入 pending
- **WHEN** 玩家使用 E-001,場上有 2 隻魔物
- **THEN** 產生 pending,選項為該 2 隻魔物

#### Scenario: 無效選擇保留 pending
- **WHEN** 玩家對 E-001 的 pending 回應不在選項內的值
- **THEN** 指令被拒絕,pending 保留,可重新選擇,遊戲狀態不變

### Requirement: Standby 節點跨回合續體與時效
`Standby` 節點 SHALL 排程待命效果,於指定觸發時機從其 `then` 節點繼續解決。`expires` 為 `"turn"` 時,待命 MUST 於建立當回合結束時移除;為 `"next_start"` 時,MUST 保留到觸發為止。

#### Scenario: E-001 於下回合開始階段觸發
- **WHEN** 玩家使用 E-001 選定魔物,直到下回合開始階段
- **THEN** 該魔物於下回合開始階段獲得 +3000 魔力(持續 `DUR_TURN`),行為與遷移前一致

#### Scenario: 待命不因建立當回合結束而消失
- **WHEN** E-001 的待命(`expires="next_start"`)建立後當回合結束
- **THEN** 待命仍保留,直到下回合開始階段觸發

#### Scenario: 排程後外層節點照常續行
- **WHEN** `Sequence(Standby(…), B)` 執行
- **THEN** 排程完成後立即執行 B,不等待待命觸發;待命觸發時只解決 `Standby.then`,不再重跑 B

### Requirement: Standby.then 限定同步完成
本次 `Standby.then` 子樹 MUST 只含不會停下的節點(不含 `Choose`、`Coin`)。註冊時 SHALL 檢查並拒絕違反者,不得在開始階段執行時才發現。

#### Scenario: 含 Choose 的待命子樹被拒絕
- **WHEN** 註冊 `Standby(…, then=Choose(…))`
- **THEN** 註冊時拋出明確錯誤

### Requirement: 延遲效果重新檢查目標
`Choose` 綁定的目標 SHALL 為穩定的 slot UID。延遲節點(如待命觸發的 `AddPower`)MUST 於執行當下依 UID 重新查找目標;目標已不存在時 MUST 無效果、不建立 modifier、不發出任何事件,且不得改選其他魔物。

#### Scenario: 目標於待命期間離場
- **WHEN** 玩家用 E-001 選定魔物 X,X 於下回合開始階段前離場
- **THEN** 開始階段待命觸發時不建立加魔力 modifier,也不發出 `modifier_added` 事件

#### Scenario: 兩筆待命各指定不同魔物
- **WHEN** 兩筆 E-001 待命分別指定魔物 X 與 Y,下回合開始階段一併觸發
- **THEN** X 與 Y 各自獲得 +3000,互不影響

### Requirement: Coin 節點包住重擲確認鏈
`Coin` 節點 SHALL 擲指定數量硬幣並沿用既有互動式確認鏈(對手 M-019 令整組重擲、自己 M-012 重擲確認),確認鏈全部結束後才依結果分支繼續。`Coin` MUST 僅在第一次執行該節點時消耗 `game.rng` 做初始擲幣;效果樹的 resume 不得再次初始擲幣。玩家依規則要求的 M-012 / M-019 重擲仍照原流程消耗 RNG。

#### Scenario: 擲幣結果決定分支
- **WHEN** 防守方宣告 S-025,擲 1 枚硬幣為正面
- **THEN** 攻擊被無效化,事件與遷移前一致

#### Scenario: 確認鏈期間停下
- **WHEN** 玩家場上有可用的 M-012,其效果樹擲幣後進入重擲確認
- **THEN** 進入 pending 等待玩家決定,決定後才繼續解決 `Coin` 之後的節點

#### Scenario: RNG 消耗次數與遷移前相同
- **WHEN** 以會在超額呼叫時失敗的 RNG 重跑各擲幣入口(傷害後、宣告時、非戰鬥)
- **THEN** 遷移前後 RNG 呼叫次數與結果相同;有重擲時,額外消耗僅來自玩家合法的重擲

### Requirement: 效果樹與既有註冊方式並存
系統 SHALL 同時支援以效果樹註冊與既有 `@reg.xxx` 裝飾器 / `CHOICE_RESOLVERS` 字串 key 註冊;同一張卡 MUST NOT 同時以兩種方式註冊同一個掛鉤。遷移為內部重構,遊戲可觀察行為(事件、pending、結算結果)MUST 與遷移前一致。

#### Scenario: 已遷移與未遷移的卡並存
- **WHEN** E-001 以效果樹註冊、E-002 仍以裝飾器註冊,雙方各使用一次
- **THEN** 兩者都正常解決,既有測試全數通過

#### Scenario: 重複註冊被拒絕
- **WHEN** 同一張卡的同一掛鉤先後以效果樹與裝飾器各註冊一次
- **THEN** 註冊時拋出錯誤,不靜默覆蓋

### Requirement: 效果樹掛鉤入口
系統 SHALL 提供下列效果樹註冊入口,並沿用既有引擎入口與檢查:`reg.event(number, effect=…, when=…)`(事件卡)、`reg.spell_rider(number, on_damage=<樹>)`(`rider.on_damage`)、`reg.spell_rider(number, on_declare=<樹>)`(`rider.on_declare`,`ctx` 含 `side`)、`reg.spell_nonbattle(number, effect=<樹>)`(非戰鬥術)。重複註冊以 `(卡號, 掛鉤)` 判定。經 `spell_nonbattle` 註冊的卡 MUST 仍受非戰鬥術的費用、時機與使用次數檢查。

#### Scenario: 宣告時效果僅防禦方生效
- **WHEN** 以 `When(SideIs("defense"), Coin(…))` 註冊的 `on_declare` 效果,以 `side="attack"` 執行
- **THEN** 不擲幣、無任何效果;以 `side="defense"` 執行時才擲幣(S-021 / S-025 為防禦專用術卡,引擎只會以防禦側呼叫)

#### Scenario: 傷害後效果的擁有者
- **WHEN** S-004 以 `rider.on_damage` 註冊並造成傷害
- **THEN** 效果的 `ctx["player"]` 為造成傷害的一方,禁術對象為其對手

#### Scenario: 非戰鬥術經引擎入口使用
- **WHEN** 玩家透過 `use_book_card` 使用以 `reg.spell_nonbattle("S-026", …)` 註冊的 S-026
- **THEN** 費用、時機與使用次數檢查與遷移前一致,不會得到 `spell.not_implemented`

### Requirement: 註冊檔逐卡一行
以效果樹註冊的卡片,註冊檔 SHALL 每張卡一行 `reg.xxx(...)` 呼叫並依卡號排序;效果邏輯 MUST 位於節點與 primitives,不在註冊檔內定義。

#### Scenario: 註冊行不含邏輯
- **WHEN** 檢視 E-001 的註冊
- **THEN** 為單一 `reg.event("E-001", when=…, effect=…)` 呼叫,無任何具名 handler 函式定義
