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
- **THEN** `PendingChoice.data["cont"]` 只含 `effect_id`(字串)、`path`(整數 tuple)與 JSON 可序列化的 `ctx`

#### Scenario: 從停點之後繼續
- **WHEN** 玩家回應 `Choose` 的 pending
- **THEN** 直譯器依 `effect_id` 與 `path` 找回該節點,把選擇值寫入 `ctx` 後,只解決該節點之後的節點,不重跑之前的節點

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

### Requirement: Coin 節點包住重擲確認鏈
`Coin` 節點 SHALL 擲指定數量硬幣並沿用既有互動式確認鏈(對手 M-019 令整組重擲、自己 M-012 重擲確認),確認鏈全部結束後才依結果分支繼續。`Coin` MUST 僅在第一次執行該節點時消耗 `game.rng`,resume 不得重新擲幣。

#### Scenario: 擲幣結果決定分支
- **WHEN** 防守方宣告 S-025,擲 1 枚硬幣為正面
- **THEN** 攻擊被無效化,事件與遷移前一致

#### Scenario: 確認鏈期間停下
- **WHEN** 玩家場上有可用的 M-012,其效果樹擲幣後進入重擲確認
- **THEN** 進入 pending 等待玩家決定,決定後才繼續解決 `Coin` 之後的節點

#### Scenario: 固定 seed 的擲幣序列不變
- **WHEN** 以固定 seed 重跑既有涉及擲幣的測試
- **THEN** 遷移前後每次擲幣結果相同,測試全數通過

### Requirement: 效果樹與既有註冊方式並存
系統 SHALL 同時支援以效果樹註冊與既有 `@reg.xxx` 裝飾器 / `CHOICE_RESOLVERS` 字串 key 註冊;同一張卡 MUST NOT 同時以兩種方式註冊同一個掛鉤。遷移為內部重構,遊戲可觀察行為(事件、pending、結算結果)MUST 與遷移前一致。

#### Scenario: 已遷移與未遷移的卡並存
- **WHEN** E-001 以效果樹註冊、E-002 仍以裝飾器註冊,雙方各使用一次
- **THEN** 兩者都正常解決,既有測試全數通過

#### Scenario: 重複註冊被拒絕
- **WHEN** 同一張卡的同一掛鉤先後以效果樹與裝飾器各註冊一次
- **THEN** 註冊時拋出錯誤,不靜默覆蓋

### Requirement: 註冊檔逐卡一行
以效果樹註冊的卡片,註冊檔 SHALL 每張卡一行 `reg.xxx(...)` 呼叫並依卡號排序;效果邏輯 MUST 位於節點與 primitives,不在註冊檔內定義。

#### Scenario: 註冊行不含邏輯
- **WHEN** 檢視 E-001 的註冊
- **THEN** 為單一 `reg.event("E-001", when=…, effect=…)` 呼叫,無任何具名 handler 函式定義
