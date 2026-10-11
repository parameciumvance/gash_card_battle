## MODIFIED Requirements

### Requirement: Choose 節點自動驗證與自動解決
`Choose` 節點 SHALL 依選項規格自動產生選項與驗證:僅有一個選項時 MUST 自動解決、不進入 pending,但登記時指定不自動解決(`auto_single=False`)的 `Choose` 仍進入 pending,由玩家選擇(實體操作上必須由玩家做的選擇,如 S-043 分裂的第二張、檢視對手魔書挑卡);有多個選項時進入 pending;玩家回應的值不在選項內時 MUST 拒絕並保留 pending,不得修改遊戲狀態。

#### Scenario: 單一選項自動解決
- **WHEN** 玩家使用 E-001,場上僅有 1 隻魔物
- **THEN** 不產生 pending,直接以該魔物繼續解決後續節點

#### Scenario: 多個選項進入 pending
- **WHEN** 玩家使用 E-001,場上有 2 隻魔物
- **THEN** 產生 pending,選項為該 2 隻魔物

#### Scenario: 無效選擇保留 pending
- **WHEN** 玩家對 E-001 的 pending 回應不在選項內的值
- **THEN** 指令被拒絕,pending 保留,可重新選擇,遊戲狀態不變

#### Scenario: 指定不自動解決時仍由玩家選
- **WHEN** S-043 分裂的第二次選擇只剩 1 張 M-024
- **THEN** 產生 pending,選項只有那一頁,玩家選了才繼續
