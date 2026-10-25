# battle-api — 設計

目前只整理了快照中「公開 / 私有」的界線、前端資源快取與版本號;其餘(端點、WebSocket)以 `src/gash/api/app.py` 與測試為準。

## 視角過濾的單點

- 所有送出伺服器的狀態與事件都經 `api/views.py`:`snapshot(game, viewer)` 與 `filter_events(events, viewer)`。不存在「先送全量、由前端隱藏」的路徑。
- NPC 看得到什麼也以這裡為準(見 `npc-opponent/design.md`)。

## 快照中的公開脈絡

以下欄位對所有視角相同,因為內容本來就是公開資訊:

- `consecutive_passes`:非戰鬥中雙方連續 pass 的次數(引擎判斷結束戰鬥階段用的同一個值),供回合轉盤顯示「再 pass 就換人」;pass 是公開的行動結果。戰鬥效果步驟的 `effect_passes` 不送。
- `pending.info`:決策的公開脈絡(擲幣結果、保護決策的目前這份傷害,見 `game-engine/design.md`「中途決策」)。傷害本來就是公開的(攻擊、戰術、傷害值都已公開),所以保護決策的內容對所有視角相同。`pending.data` 永遠不送。
- `battle.attacker_breakdown` / `defender_breakdown`:合計魔力的即時明細,內容是場上的卡、已宣告的戰術與已公開的效果。
- `effects`:作用中的待命與持續效果(待命在前、持續效果在後,各自依建立順序)。
  - 待命與持續效果建立時都發過公開事件(`standby_set` / `modifier_added`),所以清單本身是公開資訊。
  - 只送整理過的欄位;效果的 `data` 只挑白名單 `_PUBLIC_EFFECT_DATA` 內、型別相符的欄位(`mamodo`、`card`、`power_delta`、`cost_delta`、`optional`、`used`、`attr`、`amount`),續體等內部資料一律不送。
  - 新增效果種類時,若要在清單顯示額外資訊,把欄位加進白名單並確認它是公開資訊。

## 持有者私有的戰術使用資訊

- 翻開的戰術頁的 `users`(可使用此戰術的自己魔物:`slot_uid`、依該魔物計算的 `cost`、E-024 `locked`)與 `any_page_spells`(P-015 待命允許從魔書任意頁使用的戰術頁)只在 `can_see_player` 的持有者視角提供:前者洩漏自己場上的相容情況與待命,後者洩漏魔書未翻開的內容。
- 相容判定以引擎 `_spell_usable_by` 為準,前端不再自行判斷。
- `used_nonbattle_pages`(本回合已用的非戰鬥戰術所在頁)也只給持有者。以頁記錄:同名的另一頁仍可用,與戰鬥戰術的 `used_spell_pages` 一致。
- 翻開的事件卡與非戰鬥戰術的 `condition_ok`(使用條件是否成立)也只給持有者:條件可能依魔書未翻開的內容判斷(例如 S-048 看魔書有沒有 M-027)。
- 翻開的魔物 / 搭檔頁的 `play_block`(不能放出的錯誤碼,可以時為 null)與搭檔頁的 `targets`(可裝備的魔物槽 uid)也只給持有者。兩者由引擎 `play_block` / `partner_targets` 算出,`play_card` 指令經同一函式判斷,快照與指令不會分歧;前端曾以卡面 `related_mamodo` 自行比對搭檔對應,M-047(視為ガッシュ・ベル)在場時誤判,魔物卡則完全沒判斷(M-046 可按、按下才被拒)。不含時機,時機仍由前端依行動權判斷。指定裝備對象的驗證(`no_mamodo` / `partner_exists`)在 `play_block` 之前,錯誤碼與先前相同。

## 魔力 / 費用明細與常駐效果的失效(effect-visibility)

- `power_breakdown`(魔物槽,所有視角)直接取引擎的 `power_breakdown`,與對決明細的魔物部分相同。`cost_breakdown` 跟著 `cost` 出現(可見範圍相同),由 `spell_cost_breakdown` / `event_cost_breakdown` 算出;`spell_cost` / `event_cost` 只取它們的數字,兩者不會分歧。費用項目:`card`(卡面)、`last_page`、`base_zero`(S-088 / P-005,有多個時寫最後一個)、`cost_bonus`(待命的費用加減,與魔力的 `spell_bonus` 區分)、`opponent_event`(M-040)、`cost_floor`。
- `blocked_effects`(魔物槽,所有視角):頂層與搭檔中 `reg.has_passive` 且 `effect_block_sources` 不為空者;限制本身是公開資訊。`card_effect_blocked` 改由 `effect_block_sources` 判斷,`mamodo_effect_block` 與它共用 `_mamodo_effect_blocks`,錯誤碼與來源出自同一份判斷。
- `effect_blocked` 事件只在一次性時點(`play` / `discard` / `start_phase` / `damage`)發出;觸發型常駐效果對每個同類事件都會被呼叫,發事件會洗版,改由 `blocked_effects` 呈現。傷害免疫先算 `immunity(...)`,只在「會免疫但被擋」時發出。
- `damage_prevented.source`:免疫為該魔物、`no_damage` / `full_immune` / `guard_immune` 為 modifier 的來源;`no_target` 沒有。

## 翻開頁的公開例外與事件卡費用

- 對手翻開頁的卡片內容只在兩種情況出現:宣告中的攻防戰術頁(`in_use`),以及觀看者場上有 P-024(`engine.reveals_open_pages`,登記在 `reg.REVEAL_OPPONENT_PAGES`)。P-024 只對持有者公開,觀戰者與其他視角不變;持有者私有的 `users`、`condition_ok` 仍只給翻開頁的主人。
- 翻開的事件卡附 `cost`(`engine.event_cost`:卡面費用加上對手場上 M-040 等的加成),與戰術卡的 `cost` 一樣是公開資訊;前端以它顯示與判斷 MP。
- `_PUBLIC_EFFECT_DATA` 另含 `attr`(P-029)、`amount`(E-038 待命)與 `page`(S-098 選定要重用的戰術頁;本回合已用過、已公開)。待命資料帶 `card` / `page` 時,`standby_set` 事件也帶出(只有 S-098 的重用待命有),記錄據此寫出對象。

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
  - 回應已有 `Cache-Control` 時不覆寫。
  - Cloudflare 依來源的 `Cache-Control` 不在邊緣快取這些檔案。
  - Cloudflare 的 Browser Cache TTL 若不是 Respect Existing Headers,會把送給瀏覽器的 `Cache-Control` 改寫成 `max-age=14400`(見 `docker-deployment/design.md`)。
- 卡圖(`/static/assets/`)的成功回應(200、304)由同一個 middleware 加上 `Cache-Control: public, max-age=604800`。
  - 卡圖內容固定、另外安裝,不隨部署更新。沒有 `Cache-Control` 時瀏覽器依 `Last-Modified` 推估,剛下載的卡圖推估時間很短,重新渲染(例如牌組編輯器切換篩選)時會先向伺服器確認,卡面短暫空白。
  - 7 天而不是 `immutable`:同檔名仍可能換內容(重新下載),過期後以 `ETag` 確認;換內容時清 Cloudflare 快取(見 README「卡圖」)。
  - 404 不帶:Cloudflare 會依 `max-age` 快取 404,缺圖時帶長期快取的話,之後補上卡圖要等很久才看得到。
  - `.webp` 屬於 Cloudflare 預設在邊緣快取的副檔名,邊緣也依這個 `max-age` 快取,VPS 的卡圖流量隨之下降。
- 卡圖的 `Content-Type`:`app.py` 載入時以 `mimetypes.add_type("image/webp", ".webp")` 登記。Python 3.12 的 `.webp` 只在非嚴格的 `common_types`,`python:3.12-slim` 又沒有 `/etc/mime.types`,Starlette 以嚴格模式判斷不出就回 `application/octet-stream`。測試以子行程模擬這個環境(`tests/test_static_cache.py`)。

## 維護公告

- 公告檔在卡圖目錄(`GASH_ASSETS_DIR`,部署時是 volume)下的 `announcement.json`,`read_announcement` 每次請求即時讀取:編輯或刪除檔案就能發布 / 撤下,不需重新部署或重啟(重啟會讓對局消失,公告正是為了事先提醒)。
- 驗證:`id` 非空字串、`message` 為非空的「語言 → 文字」物件、`until`(可選)為 ISO 8601,沒有時區視為 UTC;過了 `until` 回傳 null。不合格一律回傳 null 並記警告,不讓請求失敗。
- 獨立端點 `GET /api/announcement`,不併入 `/api/meta`:前端每 2 分鐘查詢,端點保持輕量。`frontend/assets/template.announcement.json` 是發布用的範本(伺服器只讀 `announcement.json`)。

## 版本號

- `gash.version.app_version()` 依序取:環境變數 `GASH_VERSION`(Docker,CI 以 tag 名稱傳入)→ `git describe --tags --always --dirty`(開發環境)→ `dev`。行程內快取。
- 以 tag 為版本號是因為部署只由推送 `v*` tag 觸發,tag 就是「線上是哪一版」;`pyproject.toml` 的 `version` 沒有在更新,不採用。
- `/api/meta` 回傳 `version`;首頁免責聲明下方顯示,意見回報的環境資訊帶 `ver=`。
