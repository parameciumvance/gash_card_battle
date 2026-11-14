## Why

v1.4 對應第 4 賽季(次版本號 = 賽季)。第 4 賽季的卡片(LEVEL:4、魔本拡張シート LEVEL:3、電撃フェスタ2004春の陣 プロモーションシート、PR-011〜013、MJ12)都已收錄並實作完成,尚未開放清單為空;使用者 2026-11-14 要求做 1.4 發布準備。

## What Changes

- `data/seasons.json`:`selectable` 加入 4,`default` 改為 4。建房、開桌、設定頁的賽季選單都可選第 4 賽季,缺省為第 4 賽季。
- 規則頁賽季表出現第 4 賽季;Ex-000、Ex-099 的註明不再寫「目前不能選」(既有情境「開放新賽季」)。
- 第 4 賽季的預組(第 2 回魔界王決定戦三副)在選第 4 賽季時可用。
- README 的賽季說明更新。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `online-room`:修改「房間的賽季」(1~4,缺省 4)。
- `game-tables`:修改「牌桌的賽季」(缺省 4)。
- `battle-ui`:修改「設定頁的賽季選單」(1~4,缺省 4)、「規則頁的賽季段落」(例子與情境更新)。

## Impact

- `data/seasons.json`、`README.md`。
- 測試:`tests/test_room_seasons.py`、`tests/test_tables.py`、`tests/test_season_reference_ui.py`、`tests/test_seasons_ui.py`、`tests/test_pool_filters_ui.py` 的缺省賽季與賽季清單。
