# Proposal

## Why

新手試玩回饋(todo「新手評論 6、10」):構築器的卡池很長,有類型、對應魔物、產品、賽季的圖示篩選,但沒有文字搜尋,想找特定的卡只能捲動或逐一篩選。

## What Changes

- 構築器與金手指的卡池篩選列上方加一個搜尋框:依卡號、目前語言的卡名、日文原名、效果名與效果文(目前語言)比對;不分大小寫、全形與半形視為相同;卡號可省略連字號(`S092`)。
- 搜尋與其他篩選同時套用(且);搜尋框空白時不篩選。
- 不比對日文效果文(雜訊太多);不做「目前魔物可用戰術」篩選(既有的對應魔物篩選已涵蓋)——使用者決定。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `deck-builder`:新增「卡池文字搜尋」。

## Impact

- `frontend/app.js`(`newPoolFilters`、`poolCardMatches`、`renderCardPoolFilters`)、`frontend/style.css`、`frontend/i18n/*.json`(搜尋框的提示文字,四語)。
- 新增瀏覽器測試 `tests/test_pool_search_ui.py`。
