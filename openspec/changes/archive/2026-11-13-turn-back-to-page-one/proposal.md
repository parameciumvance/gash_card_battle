## Why

使用者 2026-11-13 回報:在第 2 頁回翻不會回到第 1 頁。`turn_back_pages` 以 `pos = 2`(第 2、3 頁)為下限,把規格的「回翻最多回到第一頁」理解成第一個有兩頁的對頁。依規則書「めくった1枚(2ページ)」,1 張 = 2 頁;實體魔書在第 2、3 頁往回翻 1 張,就是左邊封面內側、右邊第 1 頁的對頁。效果文(P-018「自分の魔本を1枚もどす」、E-005、PR-007)也沒有別的下限。

## What Changes

- 回翻(P-018 / E-005 / PR-007)可以從第 2、3 頁回到只翻開第 1 頁的位置(`pos = 0`);在那裡再回翻為 0 張。
- 「在第一頁時使用 P-018 / E-005」「回翻 0 張不觸發 P-019 / P-041」等既有決定照舊,只是「第一頁」改指第 1 頁(`pos = 0`)。
- 金手指面板的目前頁摘要:只翻開一頁時(第 1 頁或第 32 頁)只寫那一頁。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `card-effects`:修改「效果原語」,寫明回翻的下限。
- `battle-ui`:修改「金手指面板的目前頁提示」。

## Impact

- `src/gash/engine/effects/primitives.py`(`turn_back_pages`)、`frontend/app.js`(金手指摘要)、四語 `ui.cheat.current_page`。
- 測試:更新 `test_level2.py`、`test_cards.py`、`test_season3_effects_4.py` 中以 `pos = 2` 為第一頁的案例;新增 P-018 從第 2、3 頁回翻、從第 1 頁開始階段翻頁、魔書區與金手指的瀏覽器測試。
