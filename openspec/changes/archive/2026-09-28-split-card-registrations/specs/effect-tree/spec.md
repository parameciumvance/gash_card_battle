## MODIFIED Requirements

### Requirement: 效果樹與既有註冊方式並存
所有卡片 SHALL 以效果樹註冊,登記只放在 `effects/cards/` 套件(依卡片類別分檔,見「註冊檔逐卡集中登記」)。系統 SHALL 仍接受既有 `@reg.xxx` 裝飾器 / `CHOICE_RESOLVERS` 字串 key 註冊(裝飾器只剩測試使用,引擎內部的決策 resolver 仍以字串 key 登記);同一張卡 MUST NOT 同時以兩種方式註冊同一個掛鉤。遷移本身為內部重構;遷移過程中依日文效果文修正的行為記錄於 `card-effects` spec,其餘可觀察行為(事件、pending、結算結果)MUST 與遷移前一致。

#### Scenario: 效果樹卡與裝飾器登記並存
- **WHEN** 以效果樹註冊的事件卡與測試用裝飾器註冊的事件卡在同一局各使用一次
- **THEN** 兩者都正常解決

#### Scenario: 重複註冊被拒絕
- **WHEN** 同一張卡的同一掛鉤先後以效果樹與裝飾器各註冊一次
- **THEN** 註冊時拋出錯誤,不靜默覆蓋

#### Scenario: 沒有逐卡 handler 檔
- **WHEN** 檢視 `effects` 套件
- **THEN** `effects/` 下只有機制檔(`registry.py`、`primitives.py`、`tree.py`)與 `cards/` 登記套件;遷移前的逐卡 handler 檔(`effects/events.py` 等)已刪除

#### Scenario: 遷移前後行為一致或依效果文修正
- **WHEN** 比較遷移前後的卡片行為
- **THEN** 未依效果文修正的卡,既有測試與遷移前補上的特徵測試皆全數通過;依效果文修正的卡,修正前先寫的測試在舊寫法上失敗、修正後通過

### Requirement: 註冊檔逐卡集中登記
以效果樹註冊的卡片,登記 SHALL 依卡片類別分檔:`effects/cards/` 的 `events.py`(E)、`mamodo.py`(M)、`partners.py`(P)、`spells.py`(S),每個檔案只含該類別的卡並依卡號排序,每張卡的登記集中在一處;同一張卡有多種掛鉤或資料登記(如登場效果加疊放規則、術相容加啟動效果)時,每種一個 `reg.xxx(...)` 呼叫且彼此相鄰。效果邏輯(含使用前置條件與查詢)MUST 位於 `tree.py` 的節點、條件與規格物件及 primitives,不在註冊檔內以 lambda 或具名函式定義。

#### Scenario: 註冊行不含邏輯
- **WHEN** 檢視 E-001 的註冊
- **THEN** 為單一 `reg.event("E-001", when=has_own_mamodo, effect=…)` 呼叫,`when` 引用 `tree.py` 中的具名條件函式,註冊檔內無 lambda 或 handler 函式定義

#### Scenario: 同一張卡的多個登記相鄰
- **WHEN** 檢視 M-027(疊放規則 + 無術攻擊規格)的登記
- **THEN** 為相鄰的 `reg.stack_on("M-027", …)` 與 `reg.mamodo_attack("M-027", …)` 兩個呼叫,前後都是卡號不同的卡

#### Scenario: 依卡片類別分檔
- **WHEN** 檢視 `effects/cards/mamodo.py`
- **THEN** 只有 `M-` 開頭卡號的登記,且依卡號排序;事件卡、夥伴卡、術卡各在自己的檔案

### Requirement: 決策種類依選擇內容命名
效果樹節點建立的決策種類(`Choose` 與 `CoinWithPaidReflip` 的 `prompt`,即 pending 與 `choice_required` 的 `kind`)SHALL 依選擇的內容命名,MUST NOT 含卡號;不同卡片的相同選擇 SHALL 共用同一種類。每個決策種類 MUST 在前端 i18n 有對應的標題。

#### Scenario: 相同選擇共用種類
- **WHEN** 玩家使用 E-001 或 E-009,場上有 2 隻以上自己的魔物
- **THEN** 兩者的 pending `kind` 都是 `pick_own_mamodo`

#### Scenario: 登記中的決策種類不含卡號
- **WHEN** 檢視 `effects/cards/` 中所有節點的 `prompt`
- **THEN** 沒有任何一個含卡號樣式(如 `e001`、`M-011`)

#### Scenario: 每個決策種類都有標題
- **WHEN** 檢視所有效果樹決策種類與引擎內建決策種類
- **THEN** 每個都有 `choice.title.<kind>` 的 i18n 標題
