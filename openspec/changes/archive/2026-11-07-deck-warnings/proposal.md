# Proposal

## Why

新手試玩回饋(todo「新手評論 6」):希望有組牌提示。使用者認為組牌策略應由玩家自己發掘,只檢查「不合理」的組合:魔書中的卡一定不能運作的情況。

## What Changes

- 構築器在構築規則的違規之外,另外顯示組合的**提醒**:
  - 戰術卡:魔書中沒有任何魔物能使用它(指令戰術除外)。
  - 搭檔卡:魔書中沒有它對應的魔物。
- 提醒不是違規:以不同的樣式顯示,MUST NOT 影響儲存與使用魔書。
- 「能使用」由引擎判斷(家族相符、魔物的戰術相容規則如 M-023 / M-029 / M-036、搭檔讓家族使用某屬性戰術的效果如 P-029),構築器向伺服器取得。
- 不做「對應魔物排太後面」等屬於策略的檢查(使用者決定)。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `deck-builder`:新增「魔書組合的提醒」。

## Impact

- `src/gash/engine/deck.py`(`deck_warnings`)、`src/gash/api/app.py`(`POST /api/decks/warnings`)、`frontend/app.js`(構築器的驗證列)、`frontend/style.css`、`frontend/i18n/*.json`。
- 測試:引擎、API 與瀏覽器測試。
