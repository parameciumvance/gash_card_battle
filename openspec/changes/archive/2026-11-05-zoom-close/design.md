# Design

## Context

- `#zoom-overlay` 全站共用(對局、行動記錄、檢視對手頁面、構築器),`renderZoom` 每次重繪 `#zoom-card` 與 `#zoom-actions`。關閉只有 `#zoom-overlay` 的 `onclick = closeZoom`,卡面以 `stopPropagation` 避免點卡面就關閉。
- 現有的 Esc 處理:
  - 卡片行動選單:document 的 keydown capture,選單開著時先處理並 `stopImmediatePropagation`。開啟放大檢視時選單已經關閉,兩者不會同時存在。
  - 可關閉的 `#dialog-overlay`(棄牌區視窗等):bubble 階段,已經在放大檢視開著時不處理。
  - 魔書翻閱的 `BOOK_KEYS`(Esc 回到目前頁):`BLOCKING_OVERLAYS` 包含 `zoom-overlay`,放大檢視開著時不處理,也檢查 `defaultPrevented`。
  - 金手指是 top layer 的 `<dialog>`,放大檢視不會疊在它上面(見 battle-ui design「卡片詳情」)。

## Goals / Non-Goals

**Goals:** 放大檢視有看得到的關閉方式,鍵盤可關閉,而且只關最上層。

**Non-Goals:** 不改放大檢視的內容與行動按鈕;不替其他視窗(規則頁、魔書檢閱等)補關閉鈕或 Esc。

## Decisions

### 關閉鈕貼著卡面右上角的外側

- 寬螢幕在卡面右側、與卡面上緣對齊;寬度 ≤420px(卡面固定 300px,右側放不下 44px 的按鈕)改在卡面右上角的正上方。
- 不放在卡面裡:戰術卡的卡圖右上角是費用,會被蓋住。
- 最初放在畫面右上角(`position: fixed`),使用者實際操作後回饋寬螢幕離卡面太遠,改為貼著卡面(Confirmed)。
- 結構:`#zoom-frame`(`position: relative`)包住 `#zoom-card` 與 `#zoom-close`,按鈕以 frame 為基準絕對定位。不能放進 `#zoom-card`:它有 `overflow-y: auto`(長卡面捲動),超出卡面的按鈕會被裁掉、點不到;`renderZoom` 也會清空 `#zoom-card`。
- 點擊冒泡到 overlay 的 `closeZoom`。`aria-label` 與 `title` 在 `renderZoom` 以 `t("ui.close")` 設定。

### Esc:document keydown capture,放大檢視開著時先處理並停止傳遞

放大檢視開著時,在 capture 階段 `closeZoom()`,並 `preventDefault` + `stopImmediatePropagation`。這樣:
- 底下的 `#dialog-overlay`(棄牌區視窗)的 Esc 不會收到這次按鍵,視窗保持開啟;下一次 Esc 才關閉它。
- 魔書翻閱的 Esc 不會被觸發。
- 掛在卡片行動選單的 capture 監聽之後註冊;兩者不會同時開著,順序不影響結果。
- 打字中(焦點在 input)時:放大檢視開著代表焦點不在構築器的輸入框上,仍一律關閉。

## Risks / Trade-offs

- [關閉鈕被裁掉或蓋住而點不到] → 瀏覽器測試以 `elementFromPoint` 確認按鈕中心命中按鈕本身(寬螢幕與 390px)。
- [窄螢幕下方內容很長時卡面被推高,上方的按鈕超出畫面] → 測試以對局中有行動與明細的戰術卡檢查按鈕在畫面內。
