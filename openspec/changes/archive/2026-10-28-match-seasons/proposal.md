# Proposal

## Why

卡片會依發售時間逐批加入,玩家想重現某個時期的環境(例如只用 LEVEL:1、LEVEL:2 的卡對戰),目前沒有辦法限制對局可用的卡。加入「賽季」讓對局可以限定卡片範圍,NPC 隨機魔書也只從符合範圍的魔書中抽。之後補第三賽季其餘卡片(PR、Ex、スペシャルボックス等)時,各賽季的範圍也已經定好。

## What Changes

- 新增賽季定義 `data/seasons.json`:各賽季每種卡號前綴的最大編號(第 1~3 賽季,依使用者提供的上限),以及特別歸屬的卡號(Ex-000 屬第 4 賽季)。一張卡的賽季是包含它的最早賽季;一副魔書的賽季是其中卡片賽季的最大值。
- 構築規則驗證可以指定賽季:魔書含超出賽季的卡時拒絕,原因碼 `deck.season`。
- 房間設定新增賽季(1 / 2 / 3,缺省為最新的 3,沒有「不限」):建房(線上、NPC、本機)時指定;加入、本機雙方、指定的 NPC 魔書與每副 NPC 候選都依房間賽季驗證。房間 meta 含賽季。
- 牌桌:開桌者入座時與計時一起選賽季;牌桌列表、`table.taken` 回應顯示賽季;加入方的魔書依該桌賽季驗證;再戰沿用賽季。
- `GET /api/decks` 的每個預組附上它的賽季。
- 前端:
  - 設定頁(與朋友對戰的建立模式、NPC 對戰、本機)與牌桌頁的開桌設定加上賽季選單,並記在瀏覽器。
  - 牌組選單中超出所選賽季的魔書禁用並標示「第 N 賽季起」;NPC「隨機」只以符合賽季的魔書為候選。
  - 牌桌頁顯示各桌賽季;所選魔書不符等待中牌桌的賽季時,該桌的「對戰」禁用。
  - 加入被 `deck.season` 拒絕時,錯誤訊息說明房間的賽季。
  - 構築器在魔書名稱旁顯示「第 N 賽季起」;卡池新增賽季篩選(單選 1 / 2 / 3,顯示該賽季可用的卡,與其他篩選取交集),與金手指的卡池共用。
  - 四語字串。
- 不在此範圍:第三賽季其餘 95 張卡的資料(M-054~069、P-036~043、S-107~112、E-044~049、PR-001~011、Ex-001~048)與其效果實作,由後續 change 處理;目前資料中的卡都屬第 1~3 賽季。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `card-data`:新增賽季定義(卡號範圍與特別歸屬),一張卡與一副魔書的賽季;預組資料的賽季。
- `online-room`:建房新增賽季設定,加入、本機雙方與 NPC 魔書(含隨機候選)依賽季驗證,房間 meta 含賽季。
- `game-tables`:入座時選賽季、列表與 `table.taken` 含賽季、加入方依該桌賽季驗證、再戰沿用賽季。
- `battle-api`:`GET /api/decks` 回傳預組的賽季。
- `battle-ui`:設定頁與牌桌頁的賽季選單、牌組選單依賽季禁用、NPC 隨機候選依賽季篩選、牌桌賽季顯示與「對戰」禁用、`deck.season` 的錯誤訊息、記住賽季。
- `deck-builder`:魔書的賽季標示、卡池賽季篩選。

## Impact

- 資料:新增 `data/seasons.json`(前端經 `/data/seasons.json` 讀取,同 `pending_cards.json`)。
- 引擎:`src/gash/engine/deck.py`(`validate_deck` 加賽季)、`src/gash/engine/cards.py` 或新模組(讀取賽季定義、計算卡片 / 魔書賽季)。
- API:`src/gash/api/app.py`(`CreateRoom`、`JoinBody` 的驗證、`SitBody`、`_resolve_deck`、`_npc_seat`、`_new_table_room`、`preset_list`)、`src/gash/api/tables.py`(列表與 meta)、房間 meta。
- 前端:`frontend/app.js`(設定頁、牌組選單、牌桌頁、錯誤訊息、卡池篩選)、`frontend/decks.js`(魔書賽季計算)、`frontend/pool-filters.json`、`frontend/style.css`、`frontend/i18n/*.json`。
- 測試:API(`tests/test_tables.py`、房間相關測試)、引擎構築驗證、瀏覽器測試(設定頁、牌桌頁、構築器、卡池篩選)。
