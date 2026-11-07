# Proposal

## Why

新手試玩回饋(todo「新手評論 10」):開始階段初見只有「不翻頁」,要先按魔書的箭頭才出現「翻 N 張」,新手不知道可以翻頁。使用者決定維持「依魔書翻閱位置選張數」的做法(battle-ui「開始階段依魔書翻閱選擇翻頁張數」),但要清楚提醒可以翻頁。

## What Changes

- 開始階段停在目前頁、還能翻頁時,「不翻頁」按鈕加附註「按魔書的 › 往後翻閱,選擇翻幾張(最多 N 張)」。
- 開始階段還能再往後翻閱時,回合玩家魔書的「›」按鈕發光;翻閱到最多能翻的對頁、或已經不能翻頁時不發光。
- 四種語言。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `battle-ui`:新增「開始階段的翻頁提醒」。

## Impact

- `frontend/app.js`(行動欄的開始階段按鈕、魔書的翻閱按鈕)、`frontend/style.css`、`frontend/i18n/*.json`。新增瀏覽器測試。
