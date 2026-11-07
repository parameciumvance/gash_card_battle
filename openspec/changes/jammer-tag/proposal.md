## Why

ジャマー(中文「干擾」,2026-11-07 起)是有使用時機規定的效果圖示,但卡片資訊目前完全不顯示效果圖示,玩家要看卡圖上的「CUT-IN」才知道這張卡有干擾效果;缺卡圖時看不出來。使用者希望干擾標籤顯示在卡片資訊。

## What Changes

- 卡片資訊列(放大檢視、卡池、魔書構築頁位、金手指)對有干擾圖示的卡加上「干擾」標籤,樣式比照「中級」「上級」標籤。
- 依卡片資料判斷:`effect_icon` 為 `jammer`,或 `effect_icons` 含 `jammer`(M-080 有兩個效果圖示)。
- 四語標籤:繁中「干擾」、日文「ジャマー」、英文「Jammer」(簡中由轉換產生)。
- 盤面卡面照舊不顯示資訊列。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `battle-ui`:新增「資訊列的干擾標籤」。

## Impact

- 前端:`frontend/app.js` 的 `cardEl`、`frontend/style.css`、四語 i18n。
- 測試:卡面資訊列的瀏覽器測試。
- 伺服器、引擎、卡片資料不變。
