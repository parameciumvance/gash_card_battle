## Why

非戰鬥中 pass 一次後,回合轉盤旁會出現「已 pass 一次,再 pass 就換…的回合」的提示。提示所在的欄位(`#turn-cluster .turn-side`)只有最大寬度,寬度隨提示出現、消失與文字長短改變,行動欄的選項按鈕(`#action-main`)因此左右移動。使用者回報按鈕被提示推得跳來跳去,不容易點(2026-11-01)。

## What Changes

- 轉盤旁的提示欄改為固定寬度(桌機 170px、窄螢幕 84px,沿用原本的最大寬度),提示文字在欄內換行。
- 行動欄的選項按鈕不再隨提示移動。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `battle-ui`:「回合轉盤的 pass 傾斜」加上提示不推動選項按鈕的要求與情境。

## Impact

- `frontend/style.css`:`#turn-cluster .turn-side`。
- 測試:`tests/test_turn_dial_ui.py` 新增按鈕位置不變的瀏覽器測試。
