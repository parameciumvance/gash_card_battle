## ADDED Requirements

### Requirement: 關閉房間
系統 SHALL 提供關閉房間端點(以玩家 token):自由調查時間的玩家、NPC 房的真人玩家,以及對手尚未加入的朋友房建房者 SHALL 可關閉房間——刪除房間、停止 NPC 的驅動、以關閉碼 4404 關閉仍連著的 WebSocket,房號之後不再有效。已開局或已結束的朋友房 MUST NOT 以此關閉(回 409 `room.close_started`,對局中可棄權);牌桌的房間 MUST NOT 以此關閉(回 409 `room.close_table`,依牌桌的離開規則);觀戰者回 403;無效 token 回 401。

#### Scenario: 關閉自由調查時間
- **WHEN** 自由調查時間的玩家呼叫關閉
- **THEN** 房間被刪除,之後以該房號查詢回 404

#### Scenario: 對局中的朋友房不能關閉
- **WHEN** 雙方都已加入的朋友房,一方呼叫關閉
- **THEN** 回 409 `room.close_started`,對局繼續

#### Scenario: 沒人加入的朋友房
- **WHEN** 朋友房建立後對手還沒加入,建房者呼叫關閉
- **THEN** 房間被刪除,之後以該房號加入回 404
