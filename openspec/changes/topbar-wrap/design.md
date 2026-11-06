# Design

## Context

`#topbar` 是 `display: flex`,只有 `@media (max-width: 700px)` 才 `flex-wrap: wrap`。按鈕 `white-space: nowrap; flex-shrink: 0`(避免英日的長按鈕被擠成直排),文字欄位(`<span>`)可縮小,寬度不夠時被壓到 min-content,中日文字一字一行。`#title` 也可縮小,`.wm-text` 內的「CARD BATTLE」因此換行。

## Decisions

- `#topbar` 一律 `flex-wrap: wrap`(原本只在手機版),並加 `row-gap` 讓兩行之間有間距。
- 頂欄的文字欄位與 `#title` 設 `white-space: nowrap; flex-shrink: 0`:整個項目換到下一行,而不是在欄位內斷開。
- 例外:只靠 nowrap 時,單一欄位比整個畫面還寬就會超出畫面。頂欄的文字欄位都很短(最長的是日文的等待狀態),≥701px 不會發生;≤700px 的手機版維持原本的規則(徽章、可換行),不加 nowrap。
- 替代方案:中等寬度把次要按鈕收進選單(B)、固定兩行版面(C)。A 改動最小,同時解決直排與按鈕超出畫面;使用者選 A。

## Risks / Trade-offs

- [中等寬度頂欄變兩行,盤面少一行高度] → 之後若覺得太佔空間,再做 B。
