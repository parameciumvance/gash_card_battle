## ADDED Requirements

### Requirement: 對戰中人數
系統 SHALL 提供 `GET /api/online`,不需 token,回傳 `{"count": N}`。N 為所有房間目前的 WebSocket 連線換算的人數:玩家連線 SHALL 依 (房號, 座位) 去重,同一座位的多條連線只算一人;觀戰連線 SHALL 每條算一人。NPC 座位沒有連線,MUST NOT 計入;沒有任何連線的房間不計入。等待對手中的建房者與對局已結束但仍連線者 SHALL 計入。連線關閉後 SHALL 不再計入。回應 MUST NOT 含房號、暱稱或其他房間資訊。

#### Scenario: 玩家與觀戰者都計入
- **WHEN** 線上房的雙方玩家各有一條連線,另有兩條觀戰連線
- **THEN** `GET /api/online` 回傳 `{"count": 4}`

#### Scenario: 同一座位多條連線只算一人
- **WHEN** 同一位玩家以同一個 token 開了兩條連線
- **THEN** 該玩家只算一人

#### Scenario: NPC 不計入
- **WHEN** NPC 房的玩家有一條連線,且沒有其他房間有連線
- **THEN** 回傳 `{"count": 1}`

#### Scenario: 等待對手的建房者計入
- **WHEN** 線上房建立後、對手加入前,建房者有一條連線
- **THEN** 建房者計入人數

#### Scenario: 沒有連線的房間不計入
- **WHEN** 存在本機房與線上房,但都沒有任何連線
- **THEN** 回傳 `{"count": 0}`

#### Scenario: 斷線後不再計入
- **WHEN** 玩家關閉其唯一的連線
- **THEN** 之後回傳的人數少一人

#### Scenario: 不洩漏房間資訊
- **WHEN** 任何人請求 `GET /api/online`
- **THEN** 回應只有 `count`,沒有房號、暱稱或其他房間資訊
