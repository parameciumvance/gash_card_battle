# Design

## Context

- 右欄 `#log-panel`(寬 300px)只有行動記錄;`@media (max-width: 700px)` 時改為底部抽屜。
- 卡片元件 `cardEl`(帶 `zoomCtx` 時點擊開行動選單,card-action-menu);放大檢視的明細由 `zoomDetails(num, ctx)` 產生,疊放清單在 `renderZoom` 內。
- 行動記錄中的卡名由 `linkCardNames` 包成可點的 span。

## Decisions

### D1 版面

`#detail-panel` 放在 `#log-panel` 內、記錄標題之前,`flex: 0 0 45%`、`overflow-y: auto`,下方記錄 `flex: 1`。窄螢幕 `display: none`。面板高度固定(explore 選 A):懸停頻繁換卡時,記錄不會被推動。

### D2 選定與懸停

- `DETAIL = {num, ctx}`(選定)與 `DETAIL_HOVER`(懸停);顯示 `DETAIL_HOVER ?? DETAIL`。
- `cardEl` 的點擊先 `setDetail(num, ctx)` 再開選單或放大檢視;卡片元素記 `_num`。
- 懸停以事件委派:`#board` 與 `#log` 上的 `mouseover` 找最近的帶 `_num` 的元素(卡片或卡名 span),`mouseout` 離開該元素時清除懸停。卡背沒有 `_num`,不改變面板。魔書網格等浮層蓋住盤面時事件到不了盤面,不需特別處理。

### D3 內容

- 卡面:`cardEl(num, {fullName, power / cost 同放大檢視})`,不帶 ctx(點了直接放大檢視)。
- 明細:`zoomDetails(num, ctx)`;疊放清單抽成共用函式,放大檢視與面板共用。
- `render()` 結束時重繪面板;`zoomActions(ctx)` 回 `gone` 時把選定卡的 ctx 清為 null(仍顯示卡面)。`leaveRoom` 時清空。

## Risks / Trade-offs

- 右欄的記錄變短:面板高度固定 45%,記錄仍可捲動。
- 每次 `render()` 重繪面板:內容只有一張卡與明細,成本可忽略。
