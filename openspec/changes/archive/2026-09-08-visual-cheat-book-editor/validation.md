# 驗證紀錄

- `python -m pytest tests/test_cheat_editor.py tests/test_debug_state.py tests/test_custom_decks.py tests/test_deck.py -q`：23 passed。
- 調整過期回應測試等待時機後，重跑 `python -m pytest tests/test_cheat_editor.py -q -k 'stale_response or post_response'`：2 passed、6 deselected。
- `node --check frontend/app.js`、`node --check frontend/decks.js`、`git diff --check`：通過。
- `openspec validate visual-cheat-book-editor --strict`：通過。

## Chromium 檢查

使用真實本機 API 與隔離的瀏覽器 context；失敗、延遲及缺圖情境透過 Playwright 攔截指定請求。

- 32 頁魔本、135 張卡池、指定頁替換、再點取消、改點切換、拖曳交換。
- 雙方頁位與 MP 草稿切換保留；取消、Escape、關閉及離房清除；一般盤面 render 不覆蓋草稿。
- 一次送出雙方 book/mp，任意有效卡號配置可套用；成功立即更新盤面 MP 與事件。
- 無效卡號阻擋、POST／重新整理失敗保留內容、初次讀取失敗可重試、請求期間不能重複套用或編輯。
- 舊 GET／POST 回應不覆蓋重新開啟的草稿；套用成功但讀回盤面失敗有獨立訊息。
- 桌面 1280×900、窄螢幕 390×844 與 320×844 可編輯；卡池組合篩選、缺圖卡背、原生 modal 背景隔離、鍵盤選取焦點。
- 線上與觀戰身分不呈現入口，也無法透過 openCheat 開啟。
- 一般構築器仍可點選加入、移除、交換與拖曳，保留篩選、合法性提示及本機牌組／草稿儲存。

新增的瀏覽器測試需要測試環境安裝 Playwright 與 Chromium；缺少時明確 skip，不影響既有 Python 測試。應用程式未新增執行期依賴。
