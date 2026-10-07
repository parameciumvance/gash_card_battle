## Context

前端事件管線在 `frontend/anim.js`:每批事件依序做量測 → 時間軸(聚焦展示格與擲硬幣 / 魔力對決的阻塞演出)→ 重繪 → 疊加動畫。行動者(`actor`)由伺服器標明,`selfPlayer()` 在本機模式與觀戰為 null。音效掛在同一條管線上,與畫面同步。

## Decisions

### D1:Web Audio 合成,不用音檔

- 新增 `frontend/sound.js`,模組 `Sfx`。每個音效是幾個短音(振盪器的波形、起訖頻率、長度、音量包絡)與噪音(翻頁、硬幣)的組合,播放時才建立節點。
- 不新增音檔:沒有授權問題、不增加下載量,也不必改卡圖以外的靜態資源快取規則。
- `AudioContext` 在第一次使用時建立;瀏覽器要求使用者互動後才能出聲,所以在第一次 `pointerdown` / `keydown` 時建立並 `resume()`。重新整理後直接回到對局、尚未點擊時,音效靜默略過,不報錯。
- 總音量固定(主增益約 0.25),不提供音量滑桿;要靜音用設定關掉。

### D2:事件 → 音效種類與優先順序

| 音效 | 事件 |
|---|---|
| `win` / `lose` | `game_ended`:有「自己」時依 `winner` 分勝負;本機模式與觀戰一律 `win` |
| `damage` | `damage_dealt` |
| `hurt` | `mamodo_injured`、`mamodo_discarded`、`card_discarded`(`reason` 不是 `cost`) |
| `block` | `protected`、`damage_prevented`、`damage_negated`、`attack_negated`、`defense_negated`、`effect_negated` |
| `heal` | `mamodo_healed` |
| `attack` | `battle_in_check` |
| `defense` | `defense_declared` |
| `effect` | `book_card_used`、`ability_used` |
| `card` | `card_played` |
| `coin` | `coin_flipped`(開局決定先攻的除外) |
| `showdown` | `showdown` |
| `page` | `pages_flipped`、`pages_turned`(張數不為 0) |
| `pass` | `passed`、`no_defense` |

- 表格由上而下即優先順序。同一時間點有多個事件時只響最重要的一個,避免一批事件(例如攻擊結算的傷害 + 翻頁 + MP)疊成雜音。
- `mp_changed`、`turn_started`、`standby_*`、`modifier_added` 等不響:前者太頻繁,回合開始由「輪到你」涵蓋。
- 對照表放在 `sound.js`(`CUES`、`cueFor(ev, me)`),與 `anim.js` 的聚焦分類表各自獨立:聚焦只展示對手行動與對自己不利的結果,音效則自己的行動也響。

### D3:與畫面同步的時間點

- 時間軸的每一格記錄它包含的事件(`step.events`)。該格展示時,播放這些事件中最重要的音效。
- 擲硬幣與魔力對決在阻塞演出開始時播放。
- 沒有被任何一格或演出用掉的事件(自己的行動、聚焦關閉、分頁在背景、動畫關閉時的擲硬幣等),在重繪時合為一個時間點播放。
- `actor` 為 null 的批次(開局、金手指、重連時的全量快照)不播放行動音效。
- 音效不受「聚焦」與「動畫」設定影響,只看「音效」設定。

### D4:「輪到你」

- 重繪後比較這批事件前後的等待玩家:`awaitedPlayer(prevState)` 不是自己、`awaitedPlayer(S)` 是自己時播放 `your_turn`。`awaitedPlayer` 改為可傳入快照(預設 `S`)。
- 只在有「自己」的視角(線上、NPC 對戰)播放;本機模式兩方都由自己操作、觀戰不操作,不播放。
- `prevState` 為 null(初次載入、重連)時不播放。
- 同一批若也有行動音效,`your_turn` 延後約 350ms,兩個音不重疊。

### D5:設定

- `PREFS` 加入 `sound: ["on", "off"]`,存於 `gash-sound`,缺省 `on`;演出設定面板新增一組按鈕。
- 測試用:`Sfx.played` 記錄每次決定播放的音效名稱(音效開啟時才記,不論瀏覽器是否允許出聲),瀏覽器測試據此驗證,不必量測實際聲音。

## Risks / Trade-offs

- 合成音效的音色有限,但足以區分種類;之後要換成音檔只需改 `sound.js` 的播放部分。
- 分頁在背景時瀏覽器會延後計時器,`your_turn` 可能晚約 1 秒,不影響提醒的目的。
