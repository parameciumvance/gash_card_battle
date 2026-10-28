# Spec Delta

## ADDED Requirements

### Requirement: 牌桌的賽季
以為是空桌而入座時,請求 SHALL 可附上賽季(規則同 `online-room`「房間的賽季」,缺省 3,其他值回 422 `room.bad_season`);開桌建立的房間使用該賽季。`GET /api/tables` 的等待中、對戰中與結束後選擇中的牌桌 SHALL 含賽季;`table.taken` 回應 SHALL 附上該桌的賽季。入座者的魔書 SHALL 依該桌賽季驗證,違規回 422 `deck.season` 且 MUST NOT 改變牌桌狀態。再戰建立的新房 SHALL 沿用原本的賽季。

#### Scenario: 以賽季開桌
- **WHEN** 玩家在空的桌 4 以 60 秒、第 1 賽季入座
- **THEN** 桌 4 為等待中,列表中桌 4 的賽季為 1

#### Scenario: 加入方的魔書超出賽季
- **WHEN** 桌 2 以第 1 賽季等待中,另一位玩家以 level2 預組入座桌 2
- **THEN** 回應 422 `deck.season`,桌 2 仍為等待中

#### Scenario: 同時開桌的回應含賽季
- **WHEN** 玩家以為桌 2 是空桌而入座,但桌 2 已由小明以 60 秒、第 2 賽季開桌
- **THEN** 回應 409 `table.taken`,附上小明、60 秒與賽季 2

#### Scenario: 再戰沿用賽季
- **WHEN** 第 1 賽季牌桌的對局結束後雙方都選再戰
- **THEN** 新的一局賽季仍為 1
