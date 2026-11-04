# Proposal

## Why

v1.3.2 的卡片行動選單讓有行動的卡點一下先出選單,手機上(窄螢幕沒有詳情面板)看詳情要再按「詳情」,變成點兩下。其他卡牌遊戲(Hearthstone、Legends of Runeterra、MTG Arena、遊戲王 Master Duel)普遍以「點一下操作、長按看詳情」處理。

## What Changes

- 觸控長按盤面上的卡(約 0.45 秒)直接開啟放大檢視,不出行動選單;放開後的 click 不再觸發選單或卡片原本的點擊動作;手指移動超過約 10px 視為捲動而取消。
- 滑鼠右鍵直接開啟放大檢視;卡片上不出瀏覽器的右鍵 / 長按選單,也不選取文字。
- 點一下的行為不變,選單的「詳情」保留(長按不易發現)。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `battle-ui`:新增「長按看詳情」。

## Impact

- `frontend/app.js`(`cardEl`、`bindLongPress`)、`frontend/style.css`(`.card`)、`tests/test_card_long_press_ui.py`。
- `frontend/i18n/releases.*.json`:v1.3.3 更新內容。
