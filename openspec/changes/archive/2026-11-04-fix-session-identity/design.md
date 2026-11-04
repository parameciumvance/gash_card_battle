# Design

## Decisions

### D1 分頁身分用 sessionStorage

`saveSession` 同時寫入 `sessionStorage["gash-session"]` 與 `localStorage["gash-room-<房號>"]`;`loadSession(code)` 先看分頁的身分是否同一房,是就用它,否則用 `localStorage`。`sessionStorage` 依分頁區分、重新整理後保留,正好對應「這個分頁是誰」;`localStorage` 保留給「這個瀏覽器記得哪些房間」(首頁返回、新分頁開房間連結)。

替代方案:`localStorage` 依房號 + 座位分開記。不採用:新分頁開 `?room=` 時仍無法判斷要用哪個座位,首頁清單也要改;分頁層級的問題用分頁層級的儲存解決最直接。

### D2 限制

同一個瀏覽器的兩方都存在時,`localStorage` 仍只記最後寫入的一方:從首頁或新分頁返回時接回的是最後加入的那一方。一般玩家一個瀏覽器只有一方,影響只在測試或代理環境。`sessionStorage` 無法使用時退回原本行為。

## 測試備註

多分頁的瀏覽器測試中,背景分頁的 requestAnimationFrame 會暫停,`wait_for_function` 改用固定間隔輪詢(`polling=100`)。
