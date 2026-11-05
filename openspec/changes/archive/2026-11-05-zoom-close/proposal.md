# Proposal

## Why

新手試玩回饋(todo「新手評論 10」,v1.3.0):卡片放大檢視沒有明顯的關閉鈕,按 Esc 也關不掉。現在只能點卡面以外的背景關閉,但這件事畫面上沒有任何提示;卡面在手機上幾乎佔滿畫面,背景可以點的地方也不明顯。放大檢視是每局都會用到的畫面(行動選單的「詳情」、沒有行動的卡、行動記錄的卡名、構築器的「詳情」都會開它),關不掉會直接打斷操作。

## What Changes

- 放大檢視右上角加固定的「×」關閉鈕,觸控尺寸足夠,四種語言的無障礙名稱沿用既有的「關閉」文字。
- 按 Esc 關閉放大檢視。只關閉放大檢視,底下的視窗(棄牌區、魔書網格、檢視對手頁面的對話框等)維持開啟。
- 保留點背景關閉。
- 對局與牌組構築器共用同一個放大檢視,一起適用。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `battle-ui`:新增「放大檢視的關閉」需求。「卡片放大檢視」本身的內容與行動按鈕不變。

## Impact

- `frontend/index.html`(`#zoom-overlay` 加關閉鈕)、`frontend/app.js`(關閉鈕與 Esc 處理)、`frontend/style.css`。
- 新增瀏覽器測試 `tests/test_zoom_close_ui.py`。
- 不動引擎、API 與 i18n 檔(`ui.close` 四語已存在)。
