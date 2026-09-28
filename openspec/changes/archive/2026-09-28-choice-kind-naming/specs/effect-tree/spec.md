## ADDED Requirements

### Requirement: 決策種類依選擇內容命名
效果樹節點建立的決策種類(`Choose` 與 `CoinWithPaidReflip` 的 `prompt`,即 pending 與 `choice_required` 的 `kind`)SHALL 依選擇的內容命名,MUST NOT 含卡號;不同卡片的相同選擇 SHALL 共用同一種類。每個決策種類 MUST 在前端 i18n 有對應的標題。

#### Scenario: 相同選擇共用種類
- **WHEN** 玩家使用 E-001 或 E-009,場上有 2 隻以上自己的魔物
- **THEN** 兩者的 pending `kind` 都是 `pick_own_mamodo`

#### Scenario: 登記中的決策種類不含卡號
- **WHEN** 檢視 `tree_cards.py` 所有節點的 `prompt`
- **THEN** 沒有任何一個含卡號樣式(如 `e001`、`M-011`)

#### Scenario: 每個決策種類都有標題
- **WHEN** 檢視所有效果樹決策種類與引擎內建決策種類
- **THEN** 每個都有 `choice.title.<kind>` 的 i18n 標題
