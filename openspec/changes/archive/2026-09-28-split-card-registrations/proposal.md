## Why

`src/gash/engine/effects/tree_cards.py` 集中了全部卡片的效果登記(549 行,四種卡片類別),閱讀與修改時要在單一長檔中捲動找卡。專案負責人要求先依卡片類別拆分。

## What Changes

- 新增 `effects/cards/` 套件,依卡片類別分為 `events.py`(E)、`mamodo.py`(M)、`partners.py`(P)、`spells.py`(S);`tree_cards.py` 刪除。
- 排版規則移到 `cards/__init__.py` 開頭;各檔只匯入自己用到的名稱。
- 登記內容、順序與行為不變。
- `effect-tree` spec 中「`tree_cards.py` 為唯一的逐卡註冊檔」等敘述改為 `effects/cards/` 套件與分檔規則;靜態測試同步。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `effect-tree`:「效果樹與既有註冊方式並存」「註冊檔逐卡集中登記」「決策種類依選擇內容命名」三項需求中登記檔的位置與分檔規則。

## Impact

- 程式:`src/gash/engine/effects/cards/`(新)、`tree_cards.py`(刪)、`effects/__init__.py`。
- 測試:`tests/test_effect_tree.py` 的靜態檢查。
- 文件:`effect-tree/design.md`、README、AGENTS.md。
