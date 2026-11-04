# Proposal

## Why

使用者回報(v1.3.0):有時連線不穩而斷線;先進入牌桌,對方加入時自己斷線回到首頁,無法回到牌桌,自己的名字也一直佔著牌桌。

原因:
- 重新整理 / 回到頁面時 `resumeRoom` 把任何錯誤都當成房間不存在:網路失敗(`fetch` 失敗)或 Cloudflare 回錯誤頁(502 / 524 的 HTML,`res.json()` 失敗)都會刪除瀏覽器記得的身分並回首頁。房間其實還在,對戰中斷線不暫停也不判負,牌桌照樣顯示自己的名字,但身分已刪,首頁也列不出來,回不去。首頁「返回進行中的對局」的查詢也一樣,網路失敗就刪記錄。
- 對局的 WebSocket 只有伺服器往下送,瀏覽器從不送資料;部署經 Cloudflare Tunnel,一段時間沒有傳輸的 WebSocket 會被切斷(一般約 100 秒),對手長考時就出現「重連中」。

## What Changes

- 只有伺服器明確回應房間不存在(`room.not_found`)或身分無效(`room.bad_token`)時才刪除身分;網路或代理錯誤時保留身分,顯示「連線失敗,重試中」並自動重試(間隔 2、4、8、15、30 秒,之後每 30 秒),可按「回首頁」(身分保留,首頁可返回)。
- 首頁「返回進行中的對局」查詢失敗時,只有上述兩種回應才移除記錄;其他錯誤保留記錄、這次不列出。
- 對局的 WebSocket 連線後,瀏覽器每 25 秒送一個心跳訊息(伺服器本來就忽略收到的訊息)。
- 從 v1.3.0 的修正線(接在 fix-session-identity 之後),先不釋出。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `battle-ui`:新增「接回對局的連線失敗」與「連線心跳」;修改「返回進行中的對局」(只有房間不存在或身分無效才移除記錄)。

## Impact

- `frontend/app.js`(`api` 的錯誤、`resumeRoom`、`refreshResumeRooms`、`openWS`)、`frontend/index.html`、`frontend/style.css`、`frontend/i18n/*.json`(四語)。
- 瀏覽器測試。
