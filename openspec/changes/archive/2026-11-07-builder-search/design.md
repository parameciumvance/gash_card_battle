# Design

## Context

構築器(`B`)與金手指(`editor`)各自持有篩選狀態(`newPoolFilters()` 展開),共用 `renderCardPoolFilters` 畫篩選列、`poolCardMatches(def, filters)` 判斷。篩選列只畫一次,之後以 `sync()` 更新按鈕,變更時呼叫 `onChange` 重畫卡池;所以搜尋框不會在輸入時被重建而失去焦點。

## Decisions

- 篩選狀態加 `fquery`(字串)。`poolCardMatches` 在其他條件之後比對:`normalize(q)` 包含於該卡的比對字串。
- 比對字串:`number`、`number` 去掉連字號、`TEXT[num]` 的 `name`、`name_ja`、`attr`、`effect`,以換行串接後 `normalize`。`normalize` = `NFKC` + 小寫(全形英數、全形連字號轉半形)。以卡號與語言為 key 快取,語言切換會重新載入頁面,不必處理失效。
- 搜尋框放在篩選列上方獨立一行(`type="search"`,寬度 100%):篩選列的規格是「一行」,窄螢幕放不下再多一個輸入框。`input` 事件即時篩選;`Esc` 在有文字時清空(不關閉金手指視窗,同篩選網格的處理)。
- 搜尋文字不記住(與其他篩選一致,重新開啟回到空白)。

## Risks / Trade-offs

- [效果文比對會帶出很多卡(例如「傷害」)] → 這是使用者輸入的範圍,搭配類型篩選縮小;不另做排序。
