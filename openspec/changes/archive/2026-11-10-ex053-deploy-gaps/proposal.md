## Why

Ex-053「相手は、このターン中に捨て札にしたカードとカード名が同じカードを、場に出すことができない」在 season4-mamodo-b 只套用到一般放出與部分效果放出的選項規格。2026-11-10 實作 Ex-060 時發現 S-043、S-048、S-086 沒有檢查,使用者決定另開 change;盤點後 M-020、M-021、M-041、Ex-032 也有同樣的遺漏。

## What Changes

- 效果放出的選項規格補上 Ex-053 的同名檢查:`OwnBookPartnerNamed`(M-020、M-021、M-041、Ex-032)、`OwnBookCopiesOf`(S-043、S-048)、`CanStackFromBook`(S-086)。
- 結束階段場上沒有魔物時依規則強制放出,同名的魔物也不算候選(使用者決定)。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `card-effects`:修改「第 4 賽季魔物與搭檔第 2 批」,補上 Ex-053 適用的放出路徑。

## Impact

- 引擎:`effects/tree.py`、`engine.py`(強制放出)。
