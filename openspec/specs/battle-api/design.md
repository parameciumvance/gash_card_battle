# battle-api — 設計

目前只整理了快照中「公開 / 私有」的界線、前端資源快取與版本號;其餘(端點、WebSocket)以 `src/gash/api/app.py` 與測試為準。

## 視角過濾的單點

- 所有送出伺服器的狀態與事件都經 `api/views.py`:`snapshot(game, viewer)` 與 `filter_events(events, viewer)`。不存在「先送全量、由前端隱藏」的路徑。
- NPC 看得到什麼也以這裡為準(見 `npc-opponent/design.md`)。

## 快照中的公開脈絡

以下欄位對所有視角相同,因為內容本來就是公開資訊:

- `pending.info`:決策的公開脈絡(目前是擲幣結果,見 `game-engine/design.md`「中途決策」)。`pending.data` 永遠不送。
- `battle.attacker_breakdown` / `defender_breakdown`:合計魔力的即時明細,內容是場上的卡、已宣告的術與已公開的效果。
- `effects`:作用中的待命與持續效果(待命在前、持續效果在後,各自依建立順序)。
  - 待命與持續效果建立時都發過公開事件(`standby_set` / `modifier_added`),所以清單本身是公開資訊。
  - 只送整理過的欄位;效果的 `data` 只挑白名單 `_PUBLIC_EFFECT_DATA` 內、型別相符的欄位(`mamodo`、`card`、`power_delta`、`cost_delta`、`optional`),續體等內部資料一律不送。
  - 新增效果種類時,若要在清單顯示額外資訊,把欄位加進白名單並確認它是公開資訊。

`choice_required` 事件對非決策者仍去除 `options` / `item` / `results`;擲幣結果另有公開的 `coin_flipped` 事件與快照的 `pending.info`。

## 推送的行動者(`actor`)

- `update` 推送與指令回應帶 `actor`,前端用來決定聚焦展示(見 `battle-ui/design.md`)。
- 來源集中在 `app.py` 的呼叫端,`_broadcast(room, events, actor)`:
  - `post_command`:token 對應的玩家。
  - NPC 驅動:NPC 座位。
  - 逾時代打:`awaited_player`。
  - 金手指與開局:`None`。
- `actor` 只標明誰發起,不影響事件內容與視角過濾。

## 前端資源快取

- `app.py` 的 middleware 對 `/`、`/static/`、`/data/`(卡圖 `/static/assets/` 除外)加上 `Cache-Control: no-cache`:瀏覽器每次使用前以 `ETag` 確認,未變回 304。
  - 沒有 `Cache-Control` 時瀏覽器會自行推估快取時間,部署後曾出現新 `index.html` 配舊 `app.js` / `style.css` 的情況。
  - 不用版本號網址:`app.js` 在執行時還會載入 `i18n/*.json`、`data/*.json`、規則頁,全部帶版本號需要建置步驟;`no-cache` 一個 middleware 就涵蓋全部,代價只是幾個 304 往返。
  - 卡圖內容固定、由玩家另外安裝,維持瀏覽器自行快取。回應已有 `Cache-Control` 時不覆寫。
  - Cloudflare 依來源的 `Cache-Control` 不在邊緣快取這些檔案,VPS 與單機版行為相同。
  - Cloudflare 的 Browser Cache TTL 若不是 Respect Existing Headers,會把送給瀏覽器的 `Cache-Control` 改寫成 `max-age=14400`(見 `docker-deployment/design.md`)。

## 版本號

- `gash.version.app_version()` 依序取:環境變數 `GASH_VERSION`(Docker,CI 以 tag 名稱傳入)→ `data/version.txt`(單機版,`tools/build_release.py` 打包時寫入,不進版控)→ `git describe --tags --always --dirty`(開發環境)→ `dev`。行程內快取。
- 以 tag 為版本號是因為部署只由推送 `v*` tag 觸發,tag 就是「線上是哪一版」;`pyproject.toml` 的 `version` 沒有在更新,不採用。
- `/api/meta` 回傳 `version`;首頁免責聲明下方顯示,意見回報的環境資訊帶 `ver=`。
