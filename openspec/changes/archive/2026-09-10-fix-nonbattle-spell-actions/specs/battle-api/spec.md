## ADDED Requirements

### Requirement: 非對戰術使用紀錄快照

玩家的持有者可見快照 SHALL 包含 used_nonbattle_spells，值為該玩家引擎狀態中本回合已使用非對戰術卡號的排序陣列；無紀錄時 SHALL 為空陣列。此欄位 SHALL 只在 can_see_player 對應的完整持有者視角提供，本機全視角 SHALL 包含雙方欄位，對手與觀戰者 SHALL 不含不可見玩家的此欄位。所有提供狀態快照的既有 HTTP 回應與 WebSocket 訊息 SHALL 使用同一視角化規則。使用後及引擎重置後 SHALL 反映最新集合，不以頁碼代替卡號，也不在 API 自行計算重置時機。

#### Scenario: 初始持有者快照
- **WHEN** 玩家取得尚未使用非對戰術的己方快照
- **THEN** used_nonbattle_spells 為空陣列

#### Scenario: 使用與重連恢復
- **WHEN** 玩家使用 S-026 後取得新快照或重新連線
- **THEN** 己方 used_nonbattle_spells 含 S-026，前端可直接恢復已使用狀態

#### Scenario: 引擎重置後更新
- **WHEN** 引擎依既有回合規則清除玩家的非對戰術使用紀錄
- **THEN** 後續快照的該玩家陣列同步清空

#### Scenario: 視角隔離
- **WHEN** 線上本人、對手、觀戰者與本機全視角取得同一對局的快照
- **THEN** 本人只獲得己方使用紀錄，對手與觀戰者不獲得他方欄位，本機全視角獲得雙方紀錄
