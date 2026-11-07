# Design

## Context

- 等待者與預設回應:`engine/awaiting.py` 的 `awaited_player` 與 `default_command`(逾時代打用):戰鬥開始確認為 `battle_in_response allow`、防禦步驟為 `no_defense`、效果步驟與非戰鬥中為 `pass`。
- 合法行動:`npc/candidates.py` 的 `candidates(game, player)` 列出決策點的候選指令(含魔物效果防禦),`npc/settle.py` 的 `clone` / `try_submit` 在副本上試送判斷合法(副本已設 `previewing`,不做保護的後果預告)。
- 對手翻開的頁的卡片內容是隱藏的(battle-api design「翻開頁的公開例外」),所以「有沒有可用行動」是私有資訊。

## Decisions

### D1 判斷放在 NPC 模組,快照只給該玩家

`npc/candidates.py` 新增 `other_actions_available(game, player)`:候選中排除等於 `default_command` 的那一個,其餘逐一在副本上試送,有任一合法即為真。`views.snapshot` 在「戰鬥階段、沒有 pending、等待的是非回合玩家、觀看者看得到該玩家」時附 `idle = {"has_actions": bool, "auto": 指令或 null}`。
- 放在 NPC 模組:候選列舉本來就在那裡,引擎不反向依賴 NPC;`views` 已在 API 層,可以同時用引擎與 NPC。
- 只在等待非回合玩家時計算,每次快照最多十幾個副本,成本可接受。
- 開始階段是回合玩家的、決策(pending)有各自的選項,都不計算。

### D2 自動送出在前端

開關記在瀏覽器(`localStorage`,預設開),倒數、暫停、等演出都是畫面的事;斷線時由既有的逾時代打處理。
- `scheduleAutoPass()` 在每次重繪行動欄後呼叫:開關開、`S.idle.auto` 存在、等待的是自己能操作的玩家時,以 `S.event_count` 為鍵建立倒數(同一鍵不重建);等 `Anim.idle()` 後開始。
- 計時以 100ms 的 tick 累計,放大檢視(`ZOOM`)或卡片行動選單(`CARD_MENU`)開著時重設為 0(關閉後重新倒數 2 秒)。
- 送出前再檢查:鍵仍相同、沒有送出中的指令(`SENDING`)、開關仍開;任一不符就不送。玩家自己送出時 `send` 會讓狀態前進,鍵改變,倒數自然失效。

### D3 開關與提示的位置

- 「自動 pass」勾選框放在行動欄 Pass 等回應按鈕旁;只要是對局中的玩家(含本機模式)就一直顯示,觀戰者不顯示。倒數中旁邊顯示「自動 pass 倒數中」。窄螢幕只顯示勾選框與「自動」。
- 有其他可用行動時,行動欄加提示「有可以使用的效果或行動」;不列內容(使用者決定)。

### D4 瀏覽器測試預設關閉

自動 pass 預設開啟會讓既有瀏覽器測試的回應被自動送出(例如驗證「迎戰」按鈕的測試)。比照既有的做法(`conftest` 的 init script 關閉聚焦展示、預設已讀更新內容),測試的 context 預設關閉自動 pass,自動 pass 的測試自行開啟;既有測試不改內容。

## Risks / Trade-offs

- [資訊外洩:回應速度透露有沒有可用行動] → 使用者知悉後決定所有模式預設開啟、2 秒延遲;想避免的玩家可以關閉。
- [副本試送與實際送出不一致] → 共用同一個 `submit`;測試以實際送出比對。
- [倒數期間狀態被推送更新] → 以事件序號為鍵,狀態改變即失效、依新狀態重新判斷。
