## ADDED Requirements

### Requirement: 推送標明行動者
WebSocket 的更新推送與指令提交的回應 SHALL 帶 `actor`,標明發起這批事件的玩家(0 / 1):
- 玩家提交的指令:該玩家。
- NPC 送出的指令:NPC 的座位。
- 逾時代打:被代打的玩家。
- 金手指套用:`null`。

同一批事件經推送與回應兩條路徑到達時,`actor` MUST 相同。`actor` 只標明誰發起,不改變事件內容與視角過濾。

#### Scenario: 對手的指令標明對手
- **WHEN** 線上房中玩家 1 提交指令
- **THEN** 玩家 0 收到的推送 `actor` 為 1;玩家 1 的指令回應與推送 `actor` 也為 1

#### Scenario: NPC 與逾時代打
- **WHEN** NPC 送出指令,或伺服器替逾時的玩家 0 代送指令
- **THEN** 推送的 `actor` 分別為 NPC 的座位與 0

#### Scenario: 金手指沒有行動者
- **WHEN** 本機房或 NPC 房套用金手指
- **THEN** 推送的 `actor` 為 null
