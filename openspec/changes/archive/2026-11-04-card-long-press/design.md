# Design

## Decisions

### D1 時間與移動門檻

長按 450ms、移動 10px:介於系統長按(Android 約 400–500ms)之間,10px 足以分辨手指微動與捲動。計時在 `pointerdown`(非滑鼠)開始,`pointermove` 超過門檻、`pointerup` / `pointercancel` / `pointerleave` 取消。

### D2 吞掉放開後的 click

長按觸發時標記卡片,放開後的 click 以捕獲階段的監聽 `stopImmediatePropagation`,所以行動選單與決策對話框卡片另外設定的 `onclick` 都不觸發。標記在下一次 `pointerdown` 重設,瀏覽器沒送出 click 時下一次點擊照常。

### D3 右鍵與原生選單

`contextmenu` 一律 `preventDefault`(Android 長按也會發 contextmenu);事件來自滑鼠時直接開放大檢視,觸控則交給長按計時,避免開兩次。`.card` 設 `user-select: none` 與 `-webkit-touch-callout: none`(iOS 長按圖片的儲存選單),卡圖設 `-webkit-user-drag: none`。`-webkit-touch-callout` 只有 iOS Safari 支援,Chromium 的自動測試驗證不到,需實機確認。

### D4 範圍

所有以 `cardEl` 建立的卡(盤面、魔書網格、棄牌區、決策提示與對話框中的卡)都支援;牌組構築器的卡(`opts.detail`)已有「i」詳情按鈕且有拖曳,不加長按。
