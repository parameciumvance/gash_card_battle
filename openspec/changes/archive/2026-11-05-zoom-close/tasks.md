# Tasks

## 1. 測試(先寫,確認修改前失敗)

- [x] 1.1 新增 `tests/test_zoom_close_ui.py`:「×」可見、尺寸 ≥44px、`aria-label` 為目前語言的「關閉」、按下後關閉;Esc 關閉;棄牌區視窗上開放大檢視時 Esc 只關放大檢視、再按一次才關棄牌區視窗;點背景仍關閉;構築器「詳情」的放大檢視可用「×」與 Esc 關閉且魔書不變;窄螢幕(390px)下「×」不與卡面重疊。確認修改前「×」與 Esc 的測試失敗

## 2. 實作

- [x] 2.1 `index.html` 在 `#zoom-overlay` 加關閉鈕,`app.js` 設定四語 `aria-label` / `title` 與 click,`style.css` 固定在右上角(≥44px)。1.1 中「×」相關的測試通過
- [x] 2.2 `app.js` 加放大檢視的 Esc 處理(capture、`stopImmediatePropagation`)。1.1 全部通過,`tests/test_card_action_menu_ui.py`、`tests/test_card_long_press_ui.py`、`tests/test_builder_card_info_ui.py`、`tests/test_book_browse_ui.py` 照舊通過

## 3. 驗證與文件

- [x] 3.1 `python -m pytest tests -m "not slow and not browser" -q` 通過;battle-ui design「卡片放大檢視」相關段落補上關閉鈕與 Esc 的做法;`openspec validate zoom-close --strict` 通過(1569 passed、9 skipped;新測試與相關瀏覽器測試 47 passed)
- [x] 3.2 本機實際操作抽查(使用者):桌面按 Esc 與「×」、手機寬度按「×」。使用者回饋寬螢幕上畫面右上角離卡面太遠,改為貼著卡面右上角外側(窄螢幕在正上方);改位置時發現 #zoom-card 會捲動而裁掉按鈕,改以不捲動的 #zoom-frame 定位,測試補 elementFromPoint 檢查

## Workflow follow-up

- 歸檔前依指南 §13:同步 battle-ui delta spec 與 design;在 `zoom-close` branch 上歸檔提交,合併回 main 與推送等使用者指示。
