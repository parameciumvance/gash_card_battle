# Design

## Context

- 勝負判定:`_game_over`(`engine.py`),原因 `book_out` / `no_mamodo`;魔書位置 `ps.pos`(翻開對頁的左頁,奇數),`book_exhausted()` 為 `pos > BOOK_SIZE`。
- 結束階段強制翻頁(`engine.py` 約 2970 行):先檢查 `pos + 2 > BOOK_SIZE + 2`(實際上翻開最後一對頁時不成立),接著 `pos += 2`、`mp += 2`、發 `pages_flipped`,之後才以 `book_exhausted()` 判負。
- 魔書傷害 `pos += 2 * amount`,可能超過 `BOOK_SIZE + 1`;快照 `pos` 夾在 `BOOK_SIZE + 2`,頂欄 `ui.book_progress` 直接顯示。
- 待命 `skip_end_flip`(M-030「本回合結束階段不翻魔書」)是公開的作用中效果。
- 牌桌已有 `tableChoiceEl`(再戰/離開)放在動作列;NPC 牌組名稱接在頂欄勝負文字後。
- 更新公告 `maybeShowRelease`:`localStorage` 的確認版本 ≠ 最新版就跳出。

## Goals / Non-Goals

- Goals:終局記錄與顯示正確、敗方看得懂原因、事前提示最後一對頁、每種模式都有明確的結算與下一步、新訪客不先看到更新紀錄。
- Non-Goals:朋友對戰的再戰(需雙方同意與新房間流程)、「關鍵戰鬥」摘要(需另訂判斷標準)、教學(todo 另列)。

## Decisions

### D1 強制翻頁無頁可翻時直接敗北

`pos + 2 > BOOK_SIZE` 時(翻開最後一對頁)直接 `_game_over(book_out)` 並 return,不改 `pos`、`mp`,不發 `pages_flipped`。勝負結果與原本相同,只修正記錄;M-030 的待命在這之前消耗,照舊可以避免。

### D2 `end_flip_loses` 由伺服器算

條件(回合玩家、未結束、`pos + 2 > BOOK_SIZE`、沒有自己的 `skip_end_flip` 待命)放在 `views.py` 的玩家快照,與 D1 的判定共用同一個引擎函式,前端不重複規則。只看公開資訊,所有視角相同。

替代方案:前端自己從 `pos` 與 `effects` 推算。不採用:規則重複在兩處,之後有新的跳過翻頁效果時容易漏改。

### D3 最後一對頁警示的位置

提示放在動作列上方(與其他對局提示同一區),只對自己操控的玩家顯示;本機測試兩方都操控,依回合玩家顯示。Pass 按鈕的說明沿用 `ui.pass_note.*` 的位置,條件是非戰鬥、輪到自己、`consecutive_passes === 1`(此時 pass 即結束戰鬥階段)。

### D4 魔書耗盡的顯示

`pos > BOOK_SIZE` 時 `ui.book_progress` 換成 `ui.book_exhausted`。剩餘頁數也以 0 計。

### D5 勝負原因點名敗方

`ui.reason.*` 改為帶 `{player}` 的模板,敗方為 `1 - winner`,名稱用 `pname`(暱稱/NPC 名稱)。行動記錄的 `log.game_ended` 用同一組文字。

### D6 結算面板

- 新的 `#result-overlay`,在 `phase` 第一次變成 `game_over` 且終局演出(聚焦展示、魔力對決)播完後打開;關閉後頂欄的勝負文字旁出現「結算」按鈕重新打開。接回已結束的房間時也打開。
- 內容只用快照:勝敗、原因、`turn_no`、雙方剩餘頁數(`BOOK_SIZE + 1 - pos`,下限 0,與魔書區一致)、場上魔物數、NPC 牌組名稱(`R.npc.deck`)。
- 再戰:`startNpc` / `startLocal` 改成由「設定」物件開局,開局時把設定存進記憶體(`LAST_SETUP`,不寫進 localStorage);面板的「再戰」以同一個設定重新開局。NPC「隨機」牌組存的是候選清單,伺服器每次重新抽選。重新整理後沒有 `LAST_SETUP` 就不顯示再戰。
- 牌桌:`tableChoiceEl` 從動作列移到面板;對方選擇狀態的更新照舊經房間推送重繪。
- 返回首頁沿用既有的離開房間流程。
- 勝敗音效、聚焦展示不變。

### D7 新訪客不跳更新公告

`localStorage` 讀得到且沒有確認紀錄時,寫入最新版本並不跳出;讀取失敗(無法儲存)時維持原本「視為未確認」。

## Risks / Trade-offs

- 既有測試依賴終局在動作列找牌桌按鈕、依賴第一次進站跳公告:同步修改測試,公告測試先寫入舊版本的確認紀錄。
- 結算面板會蓋住盤面:面板可關閉,且在終局演出後才打開。
