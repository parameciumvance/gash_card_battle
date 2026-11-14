# Design

## Context

- 2026-11-11 explore:擲硬幣子階段依規則已是「沒有可用效果不詢問」,與戰鬥階段的自動 pass 開關分開,使用者確認維持現狀,不在範圍。

## Decisions

### D1:翻閱按鈕的發光

- 合法的翻閱位置:`[pos, pos + 2 × maxFlips(pos)]`。目前翻閱位置 `at`:`‹` 發光 ⇔ `at > pos`(往前還有合法位置);`›` 發光 ⇔ `at < pos + 2 × maxFlips`。`maxFlips = 0` 時都不發光。其餘條件(開始階段、回合玩家、可操作、沒有決策)不變。

### D2:目前頁的顏色

- `.review-cell.open` 外框與 `.review-tag.cur` 改用 `--accent-blue`;`.card.pickable` 維持 `--glow`。

### D3:手機的提示開關

- `@media (max-width: 700px)`:`.hint-toggle` 與 `.hint-details` 以 flex `order` 排到行動欄最後,開關在清單正上方(開關佔整列寬度起頭)。桌機 DOM 與排版不變。
