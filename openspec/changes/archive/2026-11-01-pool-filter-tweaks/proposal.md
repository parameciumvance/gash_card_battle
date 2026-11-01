## Why

使用者 2026-11-01 對卡池篩選提出三點改善:單選的篩選要能再點一次取消;「全部」按鈕太小不好點;產品篩選要能一次選出所有 Ex 卡(目前分散在魔本拡張シート LEVEL:1 / LEVEL:2 兩個產品)。

## What Changes

- 魔物、產品、賽季三組單選篩選:在網格再點一次已選取的項目時取消選擇(等同「全部」),網格收起。
- 「全部」按鈕放大(高度至少 40px、字級較大)。
- 產品網格新增「Ex 卡」:範圍是卡號以 `Ex-` 開頭的所有卡,與特典カード(PR)並排在最後一排;圖示比照 PR,以介面配色產生「Ex」字樣圖。兩個魔本拡張シート產品照樣保留。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `deck-builder`:修改「卡池篩選的選取方式」「產品篩選分排」。

## Impact

- `frontend/app.js`(篩選的選取、產品項目與篩選條件)、`frontend/style.css`(「全部」按鈕)
- `frontend/pool-filters.json`(最後一排加入 `ex`)、`frontend/products/ex.webp`(新圖示)與 `frontend/products/README.md`
- 四語 i18n(`product.ex`)
- 測試:`tests/test_pool_filters_ui.py`
