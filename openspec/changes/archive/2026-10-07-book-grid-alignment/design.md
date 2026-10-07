## Context

- 查閱魔本:`showBookReview` 產生 `#book-review-grid > .review-spread > .review-cell > .card.small`;牌組構築與金手指:`renderBookGrid` 產生 `#book-grid` / `#cheat-book-grid > .spread > .page-slot`。三者都是 flex 換行,P1、P32 為 `.single`。
- 卡片 `.card` 高度由內容決定(`min-height` 而非固定高),`.ceffect` 最多 4 行。

## Decisions

### D1:固定欄寬的 CSS grid

- `grid-template-columns: repeat(auto-fill, <對頁寬>)`,每欄一組對頁,欄數由寬度決定,各列對齊。對頁寬由頁位寬計算:
  - 構築器 / 金手指:`--slot-w`(構築器 92px、手機 76px,金手指 100px),`.page-slot` 寬度改用此變數;對頁寬 = `2 × --slot-w + 12px`(頁縫 2、內距 4×2、框線 1×2)。
  - 查閱魔本:`.review-cell` 固定為卡寬 96px(頁碼與標記在下方換行,不撐寬),對頁寬 = `2 × 96 + 15px`(頁縫 3、內距 5×2、框線 1×2)。
- P1 與 P32 各佔一欄:P1 `justify-self: end`、P32 `justify-self: start`,像實體魔本的右頁與左頁;17 欄位排下來,P32 自然落在最後一列的第一欄。
- 手機上原本置中的網格維持 `justify-content: center`。

### D2:卡片等高

- grid 的列預設拉伸(`align-items: stretch`),對頁與頁位隨列高拉伸;`.review-cell .card` 設 `flex: 1` 填滿,同一列的卡片等高,頁碼列對齊在底部。
- 已離開魔本的頁以卡背(`.card.back`,預設寬 118px)呈現,原本就比卡寬 96px 寬;`.review-cell .card` 一律設為卡寬,卡背不超出對頁框。
- 構築器與金手指的頁位在對頁內本來就等高,但卡片在頁位中垂直置中、高度依內容;`.page-slot.filled` 改為 `align-items: stretch`,同一對頁的兩張卡等高。
- 不改成全網格固定卡高:各語言、各卡的自然高度差到約 160–255px,固定高度要嘛截斷要嘛大量留白;每列等高已足夠整齊。效果文仍最多 4 行。

### D3:不改程式

- 結構與互動不變(點選、拖拉、捲到當前頁、可選頁發光),只改樣式;既有的 DOM 與測試選擇器不受影響。
