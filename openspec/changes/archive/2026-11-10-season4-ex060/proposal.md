## Why

第 4 賽季的 Ex-060 アポロ《自由人》影響許多既有效果,使用者 2026-11-10 決定獨立一批。

## What Changes

- Ex-060「このカードが場にある→」:持有者的對手
  - 不能使用「使用自己魔書今のページ以外的卡」的效果(P-015、P-025、P-037、PR-006、M-037、S-145、Ex-037):效果本身不能發動,Ex-060 上場前就建立的待命也不能再從其他頁使用卡片(使用者決定)。
  - 不能把自己魔書今のページ以外的卡放出(含重疊,使用者決定)、棄掉、移到別頁:從任意頁放出的效果只能選翻開的兩頁;M-016 不能使用。持有者自己的 E-027 讓對手放出時也受限(使用者決定)。
- 資料:Ex-060 從尚未開放清單移除。
- 不在範圍:Ex-053 沒有擋 S-043、S-048、S-086 從魔書放出同名卡的遺漏,使用者決定另開 change。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `game-engine`:新增「今のページ以外的卡的限制」。
- `card-effects`:新增「第 4 賽季 Ex-060」。

## Impact

- 引擎:`engine.py`(使用限制與待命)、`effects/primitives.py`、`effects/registry.py`、`effects/tree.py`(魔書頁的選項規格)、`effects/cards/partners.py`。
- 前端:新的錯誤碼翻譯。
- 資料:`data/pending_cards.json`。
