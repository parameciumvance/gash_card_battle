## MODIFIED Requirements

### Requirement: 房間的賽季
建房請求 SHALL 可指定賽季(1、2、3、4,見 `card-data`「賽季定義」);未指定時為第 4 賽季,其他值回 422 `room.bad_season` 且不建立房間。線上、NPC、本機房都適用。房間 meta SHALL 含賽季。

#### Scenario: 指定賽季建房
- **WHEN** 客戶端 POST 建房(mode=online, season=1)
- **THEN** 建房成功,房間 meta 的賽季為 1

#### Scenario: 未指定賽季
- **WHEN** 客戶端 POST 建房且沒有指定賽季
- **THEN** 房間 meta 的賽季為 4

#### Scenario: 不存在的賽季
- **WHEN** 客戶端 POST 建房(season=5)
- **THEN** 回應 422 `room.bad_season`,不建立房間
