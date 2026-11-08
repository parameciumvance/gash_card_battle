## Why

第 4 賽季加入新卡片種類 MJ12(MJ-001~006),資料與卡圖已收錄(season4-card-data),盤面也已預留獨立卡區(board-side-zones),但引擎還不能放出 MJ12、也沒有它們的效果。這一批實作 MJ12 的規則與 6 張卡,以及以 MJ12 為對象的 Ex-074。

## What Changes

- 引擎:新增獨立卡區(`PlayerState.field_cards`,不裝在魔物上的場上卡片;之後的獨立バルカン也放這裡)。
  - MJ12 依規則書:自己或對手的戰鬥階段從魔書今のページ放出(1 個行動 1 張),張數不限,同名在自己場上限 1 張。
  - 場上 MJ12 的效果以 `use_field_ability`(`zone: "field"`)使用:雙方的戰鬥階段、每個效果每回合 1 次;沒有戰鬥圖示,只在非戰鬥中。「このカードを捨て札にする→」把該卡移入棄牌區。
- 卡片效果(依日文效果文與 atwiki 卡頁 FAQ):MJ-001 對手魔書 1 傷害(可保護)、MJ-002 / 005 這回合自己所有防禦 / 攻擊的合計魔力 +4000 / +2000、MJ-003 從自己魔書任一頁放出魔物或搭檔、MJ-004 看對手魔書今のページ、MJ-006 被對手的效果減少 MP 時對手也減同樣數量(雙方都有時各適用 1 次)、Ex-074 棄掉對手場上 1 張 MJ12。
- 快照:每位玩家的 `field_cards`(uid、卡號、效果的使用可否 / 已使用);翻開頁的 MJ12 附放出可否。
- 前端:翻開頁的 MJ12 可放出;獨立卡區的卡在放大檢視提供效果按鈕;決策目標可在獨立卡區選;放出與棄掉的飛卡動畫。
- NPC:候選指令包含放出 MJ12 與使用其效果。
- 資料:MJ-001~006、Ex-074 從尚未開放清單移除(第 4 賽季仍未開放選用)。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `game-engine`:新增「獨立卡區與 MJ12」。
- `card-effects`:新增 MJ-001~006 與 Ex-074 的效果。
- `battle-api`:新增「獨立卡區快照」。
- `battle-ui`:新增「MJ12 的放出與效果操作」。

## Impact

- 引擎:`state.py`、`engine.py`(放出、場上效果、棄掉、合計魔力)、`effects/tree.py`(新節點)、`effects/cards/mj12.py`(新檔)、`effects/cards/events.py`(Ex-074)、`effects/primitives.py`(MJ-006)。
- 伺服器:`api/views.py`。NPC:`npc/candidates.py`。
- 前端:`app.js`、`anim.js`、i18n。
- 資料:`data/pending_cards.json`。
