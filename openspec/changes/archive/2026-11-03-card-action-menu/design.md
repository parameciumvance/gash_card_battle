# Design

## Context

- 所有卡片元件由 `cardEl` 產生,帶 `zoomCtx` 的卡點了呼叫 `zoom(num, ctx)`;放大檢視的按鈕來自 `pickButtons(ctx)` 與 `zoomActions(ctx)`,`renderZoom` 在狀態更新時重算,`zoomActions` 回 `gone` 時關閉。
- 停用原因(`reason`)、預估合計魔力等明細在放大檢視的明細區。
- 指令送出中以 `body.sending` 的 CSS 暫停操作入口(command-busy)。

## Decisions

### D1 單一入口

`cardEl` 的點擊改呼叫 `openCardMenu(el, num, ctx)`:按鈕 = `pickButtons(ctx)` + `zoomActions(ctx).buttons`(與放大檢視同一套,決策中只有 `pickButtons`,同 `renderZoom`)。沒有按鈕時直接 `zoom(num, ctx)`;有按鈕時顯示選單,最後加「詳情」(`ui.details`)。不帶 `zoomCtx` 的純展示卡維持直接放大。

### D2 選單內容

- 按鈕文字與放大檢視相同;停用的按鈕以小字附原因(寬窄螢幕都顯示;之後寬螢幕有詳情面板時再改為只在面板顯示)。
- 執行行動:關閉選單後送出(同放大檢視的按鈕)。「詳情」關閉選單、開放大檢視。
- 預估合計魔力等明細只在放大檢視(選單保持精簡)。

### D3 位置與關閉

- 選單 `position: fixed`,依卡片的 `getBoundingClientRect()` 放在下方置中;下方空間不足時放上方;左右夾在畫面內 8px。魔書網格、棄牌區等浮層中的卡也可用,選單的 z-index 高於這些浮層、低於決策對話框以外的放大檢視。
- 點選單外(含點另一張卡:直接換成該卡的選單)、Esc、執行行動、開啟放大檢視時關閉。`render()` 後依 `CARD_MENU.ctx` 重算按鈕:`gone` 或沒有按鈕時關閉,否則更新內容並重新定位到新的卡片元素(以 `data-card` 與 ctx 找回元素,找不到就關閉)。

### D4 送出中

`body.sending .card-menu button` 一併 `pointer-events: none`(command-busy 的 CSS)。

## Risks / Trade-offs

- 既有瀏覽器測試有「點卡 → 找 `#zoom-actions` 按鈕」的寫法:改成點選單按鈕或先按「詳情」;直接呼叫 `zoom(...)` 的測試不受影響。
- 重繪後找回卡片元素:場上魔物以槽 uid、翻開頁以頁碼、網格以頁碼 / 索引標在元素的 dataset 上;找不到時關閉選單,不顯示在錯的位置。
