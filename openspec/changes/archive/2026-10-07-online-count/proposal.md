## Why

玩家在首頁看不出網站上有沒有其他人在玩。顯示目前正在對戰的人數,能讓玩家知道網站有人在使用。todo 中「人次/在線人數」只先做這部分;累積人次需要持久儲存,這次不做。

## What Changes

- 伺服器以房間現有的 WebSocket 連線計算「對戰中」人數:玩家依 (房號, 座位) 去重,觀戰者依連線數計算;NPC 沒有連線,不計入。本機測試的前端不開 WebSocket,所以不計入。
- 新增 `GET /api/online`,不需 token,只回傳總數,不含房號或任何房間資訊。
- 首頁入口下方顯示「目前 N 人對戰中」,0 人時顯示「目前沒有人對戰」。進入首頁時抓取;停留在首頁時每 30 秒更新,分頁隱藏時暫停。四種語言。
- 不做:累積人次、持久化、首頁 / 構築器的在場偵測、對戰與觀戰分開顯示。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `online-room`:新增「對戰中人數」(計數規則與 `GET /api/online`)。
- `battle-ui`:新增「首頁對戰中人數」(顯示位置、0 人文字、更新時機)。

## Impact

- 後端:`src/gash/api/app.py`(新端點、計數函式);`rooms.py` 可能加入計數輔助。
- 前端:`frontend/app.js`(抓取與定時更新)、`index.html`、`style.css`、四種語言的 i18n 字典(簡中由 `tools/build_zh_cn.py` 產生)。
- 測試:`tests/test_api.py` 或新檔(計數規則)、首頁的瀏覽器測試。
- 部署、引擎、資料不變;不新增持久資料。
