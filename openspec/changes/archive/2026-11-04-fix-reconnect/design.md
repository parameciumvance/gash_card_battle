# Design

## Decisions

### D1 「房間不在了」只認兩個錯誤碼

`roomGone(err)` = `err.code` 為 `room.not_found` 或 `room.bad_token`。`api()` 收到非 JSON 回應(代理的錯誤頁)時拋出帶 `status` 的錯誤,`code` 為空;`fetch` 失敗原樣拋出。兩者都不是「房間不在了」。

### D2 接回失敗時重試

`resumeRoom` 遇到非 D1 的錯誤時,保留身分與網址,顯示 `#reconnect-overlay`(「連線失敗,重試中…」與「回首頁」),依 `RECONNECT_DELAYS_MS`(2、4、8、15、30 秒,之後固定 30 秒)重試;成功即關閉並照常進入畫面;重試中遇到 D1 的錯誤則照原本刪除身分回首頁。「回首頁」停止重試、網址改回 `/`、身分保留(首頁清單之後連得上時會列出)。延遲可由 `window.__reconnectDelays` 覆寫(測試用)。

### D3 首頁清單

`refreshResumeRooms` 查詢失敗時:D1 的錯誤移除記錄;其他錯誤保留記錄、這次不列出。

### D4 WebSocket 心跳

`ws.onopen` 開始每 25 秒送 `"ping"`(`window.__wsHeartbeatMs` 可覆寫),`onclose` 停止。伺服器的接收迴圈本來就忽略內容。間隔低於 Cloudflare 對閒置 WebSocket 的切斷時間(一般約 100 秒)。

## Risks / Trade-offs

- 伺服器重啟後房間消失:`/state` 回 `room.not_found`,照原本刪除身分;只有連不上伺服器時才會一直重試,使用者可按「回首頁」。
