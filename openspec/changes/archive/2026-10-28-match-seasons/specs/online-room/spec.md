# Spec Delta

## ADDED Requirements

### Requirement: 房間的賽季
建房請求 SHALL 可指定賽季(1、2、3,見 `card-data`「賽季定義」);未指定時為第 3 賽季,其他值回 422 `room.bad_season` 且不建立房間。線上、NPC、本機房都適用。房間 meta SHALL 含賽季。

#### Scenario: 指定賽季建房
- **WHEN** 客戶端 POST 建房(mode=online, season=1)
- **THEN** 建房成功,房間 meta 的賽季為 1

#### Scenario: 未指定賽季
- **WHEN** 客戶端 POST 建房且沒有指定賽季
- **THEN** 房間 meta 的賽季為 3

#### Scenario: 不存在的賽季
- **WHEN** 客戶端 POST 建房(season=4)
- **THEN** 回應 422 `room.bad_season`,不建立房間

### Requirement: 魔書依房間賽季驗證
建房者、加入者、本機房雙方的魔書,以及 NPC 房指定的 NPC 魔書與每副隨機候選,SHALL 以房間的賽季做構築規則驗證(見 `card-data`「構築規則的賽季限制」),預組也不例外。違規 MUST 回 422 `deck.season`,回應含房間的賽季;建房時不建立房間,加入時不佔用玩家位。

#### Scenario: 建房者的魔書超出賽季
- **WHEN** 以第 1 賽季建房並選用 level2 預組
- **THEN** 回應 422 `deck.season`,不建立房間

#### Scenario: 加入者的魔書超出賽季
- **WHEN** 第 1 賽季的線上房等待中,加入者附上 zeon 預組
- **THEN** 回應 422 `deck.season` 且含賽季 1,房間仍在等待中

#### Scenario: NPC 隨機候選含超出賽季的魔書
- **WHEN** 以第 2 賽季建 NPC 房,候選含 level1 與 zeon
- **THEN** 回應 422 `deck.season`,不建立房間

#### Scenario: NPC 隨機只抽到符合賽季的魔書
- **WHEN** 以第 2 賽季建 NPC 房,候選為 level1 與 level2
- **THEN** 建房成功,NPC 的魔書為 level1 或 level2

#### Scenario: 缺省魔書
- **WHEN** 以第 1 賽季建房且沒有指定魔書
- **THEN** 使用 level1,建房成功
