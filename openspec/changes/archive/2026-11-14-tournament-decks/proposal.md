## Why

使用者 2026-11-14 要求把魔界王決定戦(官方大會)第 1、2 回的優勝牌組放進參考牌組(atwiki pages/1878)。

## What Changes

- 新增 6 副預組 `ref-makai-{1,2}-{junior,middle,senior}`:第 1 回(2003-11-15)與第 2 回(2004-03-21)各組(ジュニア、ミドル、シニア)優勝的魔本,依 atwiki 各優勝魔本頁的「魔本リスト」頁序。
- 名稱的組別保留英文(使用者決定):繁中「參考牌組-第1回魔界王 Junior」、英文「Reference Deck - Mamodo King Tournament #1 Junior」、日文「参考デッキ-第1回魔界王決定戦 ジュニア」;簡中由繁中產生。
- 第 1 回三副為第 2 賽季。第 2 回三副含第 4 賽季的卡(M-068、M-081、MJ-001、MJ-003 等),為第 4 賽季;目前可選賽季是 1~3,依既有的「牌組選單依賽季」,在設定頁的牌組選單呈禁用並標示「第 4 賽季起可用」,構築器仍可複製起手。
- 當年是舊規則(ルールブック Ver1~2)的大會,與本遊戲採用的規則不完全相同,只作參考。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `card-data`:修改「預組魔書資料」,加入魔界王決定戦的優勝魔本。

## Impact

- `data/decks/ref-makai-*.json`(6 個)、四語 `deck.ref-makai-*`。
- 測試:`tests/test_preset_decks.py`;`tests/test_npc_ui.py`、`tests/test_seasons_ui.py` 的 NPC 隨機候選清單(多了第 2 賽季的三副;第 4 賽季的三副依賽季被排除)。
