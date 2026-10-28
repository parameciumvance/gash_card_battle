# Spec Delta

## ADDED Requirements

### Requirement: 預組的賽季
`GET /api/decks` 的每個預組 SHALL 含 `season`:該預組魔書的賽季(見 `card-data`「魔書的賽季」)。

#### Scenario: 預組清單含賽季
- **WHEN** 前端請求 `GET /api/decks`
- **THEN** level1 的 `season` 為 1、level2 為 2、zeon 為 3
