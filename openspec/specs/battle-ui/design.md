# battle-ui — 設計

目前只整理了事件動畫與對手行動聚焦展示;其餘畫面設計以 `frontend/` 程式與測試為準。

## 事件動畫管線(`frontend/anim.js`)

```text
Anim.apply(events, prevState, renderFn, actor)   每批事件排隊,前一批播完才處理下一批
  量測(重繪前的位置)
  時間軸:依事件順序
    卡片聚焦 / 文字聚焦            ← 對手行動聚焦展示
    擲硬幣 / 魔力對決(阻塞式)     ← 動畫開啟時
  重繪
  疊加式動畫(翻頁、飛卡、MP、負傷、棄牌)← 動畫開啟時
```

- 同一批事件從指令回應與 WebSocket 推送各到一次,以 `seq` 去重,先到的播放;兩條路徑都帶同一個 `actor`(見 `battle-api/design.md`)。
- 盤面在整批的聚焦與阻塞式演出播完後才重繪,呈現「先因後果」。

## 對手行動聚焦展示

- **分類表集中在 `anim.js`**:
  - `CARD_EVENTS`:卡片聚焦的事件,以及要展示的卡號。
  - `TEXT_EVENTS`:文字聚焦的事件。
  - 未列入的事件不聚焦,只進行動記錄。新增事件時在這裡補上。
- **時間軸**:
  - 卡片事件開新的一格;之後的文字事件併入為結果行。
  - 擲硬幣 / 魔力對決會結束目前這格,之後的文字另起一格。
  - 說明文字沿用行動記錄的 `logLine(ev)`,卡圖、卡名、效果文取自 `CARDS` / `ZH`。
- **要不要聚焦**:
  - `actor` 不是自己:卡片與文字事件都聚焦。
  - `actor` 是自己:只取不利結果(`unfavorable`)。
  - `actor` 為 null(金手指、開局):不聚焦。
  - 本機模式與觀戰視為沒有自己(`selfPlayer()` 為 null)。
  - MP 增減只在 `reason` 為卡號(效果造成)時列出,支付費用不列。
- **停留時間**:標準 1000ms(只有 pass 的格 500ms),快為一半。
  - 排隊 ≥ 2 批時自動用快。
  - ≥ 5 批時跳過該批聚焦(最後一批仍播)。
  - 分頁在背景時不聚焦。
- **遮罩**:`#spotlight` 蓋住盤面,點擊即結束目前這格,也避免按到尚未重繪的過時按鈕。`data-ms` 記錄這格的停留時間(測試用)。

## 演出設定

- 存於 localStorage:`gash-spotlight`(normal / fast / off,缺省 normal)、`gash-motion`(on / off / system,缺省 system)。
- `motionOff()`:設定優先,system 時依 `prefers-reduced-motion`。
- CSS 動畫只看 `html.motion-off`(由 `applyMotionClass()` 在啟動、設定變更、系統偏好變更時切換),不直接用 media query,遊戲內的「開」才能蓋過系統偏好。
- 聚焦不屬於動畫:動畫關時仍顯示,只因 `motion-off` 而沒有淡入。
- 瀏覽器測試的 fixture 預設 `gash-spotlight=off`(本機模式雙方都會聚焦,遮罩會擋住操作);聚焦的測試另外開啟。
