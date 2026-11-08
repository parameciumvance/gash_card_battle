## Why

盤面改版後(board-side-zones),玩家區標題列的資訊大多和盤面重複:MP 托盤已寫「MP N」、魔書書皮下方印著頁碼、行動方有區塊外框與行動欄的「行動玩家」標示。使用者要求拿掉重複的資訊,並把「查閱魔書」移到魔書旁。

## What Changes

- 標題列只留玩家名稱(與「(你)」);拿掉「▶ 行動中」標籤、MP 數字、魔書進度(第 N 頁 / 共 32 頁)、「查閱魔書」。
- 行動權仍以區塊外框標示,行動欄的標示不變。
- 「查閱魔書」改為魔書書皮下緣的按鈕(與上緣的「回到目前頁」相對),只在可查閱自己魔書時出現。
- 「魔書耗盡」改顯示在魔書書皮上(翻開的頁超過最後一頁時)。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `battle-ui`:修改「行動權標示」(不再有「行動中」標籤)、「魔書耗盡的進度顯示」(顯示在魔書上);新增「查閱魔書的入口」。

## Impact

- 前端:`frontend/app.js`(`renderPlayerZone`、`renderBookBlock`)、`frontend/style.css`。i18n 鍵不變(`ui.book_progress`、`ui.acting_label` 不再使用,留待確認後移除)。
- 測試:`tests/test_timing_ui.py`(行動中標籤)、`tests/test_endgame_clarity_ui.py`(魔書耗盡)、新增入口測試。
- 引擎、伺服器不變。
