## Context

- `renderActionBar` 在 `timing === "start"` 時,為 0..`maxFlip`(`min(3, floor((32 - pos) / 2))`)各加一個按鈕,最大值為主要按鈕。
- 場上魔書翻閱狀態 `BOOK_BROWSE[p]`(`browseStart(p)` 回傳檢視中的對頁起點,在目前頁時為 null);翻頁後 `pos` 改變即自動回到目前頁。

## Goals / Non-Goals

**Goals:** 開始階段以翻閱的對頁決定顯示哪個翻頁按鈕。

**Non-Goals:** 不做滑鼠移到按鈕上預覽;不改引擎、逾時代打與 NPC。

## Decisions

### D1:對應方式

- `const start = browseStart(tp) ?? pos; const n = (start - pos) / 2;`
- `0 <= n <= maxFlip` 時只加一個按鈕(`n === 0` 為 `ui.flip_0`,否則 `ui.flip_n`),設為主要按鈕;否則加提示文字 `ui.flip_browse_hint`(`{max}` 為 `maxFlip`),不加按鈕。
- `tp` 為開始階段的回合玩家;行動欄本來就只在 `mine`(輪到自己)時顯示操作。
- 翻閱的上限仍是第 32 頁,`n` 可能大於 `maxFlip`,以提示處理。

### D2:提示的呈現

提示放在行動欄按鈕的位置(與其他行動欄文字相同樣式),不額外跳出。

### D3:i18n

新增 `ui.flip_browse_hint`(「用左右鍵選擇要翻到的頁(最多翻 {max} 張)」),加到 `zh-TW` / `en` / `ja`,簡中以工具產生。

## Risks / Trade-offs

- [玩家不知道要用左右鍵] → 不翻頁時仍有按鈕可直接按;往前或超出範圍時以提示說明;行動欄的詳細提示也可補一句。
- [窄螢幕要按多次右鍵] → 最多 3 次;鍵盤也可用 → 鍵。
