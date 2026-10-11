## Why

牌組編輯器中,點選已選中的有卡頁位就會移除該卡,連點兩下就誤刪,容易誤操作。

## What Changes

- 再點選已選中的頁位改為取消選取,不再移除。
- 選中有卡的頁位時,頁位上顯示「移除」按鈕,按下才移除;移除後該頁仍為選中,可直接從卡池補卡。選中時按 Delete 也可移除。
- 金手指編輯器不變(魔書不能有空頁,本來就沒有移除)。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `deck-builder`:修改「對頁編輯」。

## Impact

- `frontend/app.js`(`togglePage`、`bookPageSlotEl`)、`frontend/style.css`、i18n。
- 測試:瀏覽器測試。
