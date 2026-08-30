## 1. 改名

- [x] 1.1 `frontend/i18n/zh-TW.json` 的 `ui.landing.local`(及 `ui.landing.local_desc` 若涉及)改為「本機測試模式」相關文案
- [x] 1.2 `README.md` 對應的「本機對戰」描述改名並補充金手指說明

## 2. 金手指端點

- [x] 2.1 `src/gash/api/app.py` 新增 `GET /api/rooms/{code}/debug-state`:`room.mode != "local"` 時回 403;否則回傳 `{players: [{book, mp}, {book, mp}]}`(取自 `room.game.state.players[i].book`/`.mp`)
- [x] 2.2 新增 `POST /api/rooms/{code}/debug-state`:同樣的 mode 檢查;驗證每個 `book` 長度為 32 且每個卡號存在於 `card_db()`,不符則回 4xx 且不套用;驗證通過後取代對應玩家的 `book`/`mp`,`emit` 一筆 `cheat_applied` 事件並呼叫既有 `_broadcast(room, events)`

## 3. 前端金手指面板

- [x] 3.1 `frontend/app.js` 新增金手指面板元件:僅 `mode==="local"` 渲染;雙方各一個 book 文字框(JSON 陣列)+ MP 數字輸入框,「套用」/「重新整理」按鈕
- [x] 3.2 「套用」呼叫 `POST /api/rooms/{code}/debug-state`;失敗時顯示錯誤訊息且不清空使用者輸入
- [x] 3.3 套用成功或收到 WS 推播含 `cheat_applied` 事件時,盤面依現有的 update 管線正常重繪(不需要額外處理)

## 4. 測試與收尾

- [x] 4.1 新增後端測試:`online` 房請求 debug-state 端點回 403;`local` 房可讀寫 book/mp 並在事件流看到 `cheat_applied`;不存在的卡號與長度不符的 book 被拒
- [x] 4.2 執行 `python -m pytest` 確認全數通過
- [x] 4.3 執行 `openspec validate local-test-cheat-mode` 確認格式正確
