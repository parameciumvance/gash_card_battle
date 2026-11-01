# Proposal

## Why

使用者提供兩副第 2 賽季的參考牌組,要加入預組選項,讓玩家在 NPC 對戰、對戰設定與構築器的「從預組複製」中直接選用。

## What Changes

- 新增預組 `ref-zeon-baltro-s2`(參考牌組-傑昂巴爾多羅S2)與 `ref-brago-s2`(參考牌組-布拉葛S2),頁序依使用者提供的牌組代碼。
- 四語名稱(`deck.<id>`;簡中由工具產生)。
- 預組清單本來就由 `data/decks/` 動態掃描,選單、NPC 隨機候選與構築器自動包含,不改程式。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `card-data`:「預組魔書資料」加入兩副參考牌組與其來源。

## Impact

- `data/decks/ref-zeon-baltro-s2.json`、`data/decks/ref-brago-s2.json`、`frontend/i18n/*.json`、`tests/test_preset_decks.py`。
