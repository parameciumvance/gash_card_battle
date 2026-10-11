## Context

- `togglePage(i)`:再點選中的有卡頁 → 移除;其他情況選取或互換。`bookPageSlotEl` 由牌組編輯器與金手指共用,行為以 `actions` 傳入。

## Goals / Non-Goals

**Goals:** 移除改由明確的按鈕;連點不會刪卡。

**Non-Goals:** 不改互換、拖拉、放卡;不改金手指。

## Decisions

### D1:選取與移除分開

- `togglePage`:再點選中的頁 → 取消選取(不論有無卡)。
- `actions.remove`(只有牌組編輯器提供):選中且有卡時,頁位內加 `.slot-remove` 按鈕(「移除」),`stopPropagation` 後移除該頁的卡,選取維持在該頁;頁位 `onkeydown` 的 Delete / Backspace 同樣呼叫。
- 金手指不傳 `remove`,不顯示按鈕。

## Risks / Trade-offs

- [移除要多一步] → 刪除本來就該是明確的動作;按鈕就在選中的頁位上。
