## Why

- S-043 分裂在魔書剛好有 2 張 M-024 時,玩家選了第一張,第二張因為只剩一個選項被自動放出,看起來像「只選一張就跳出兩張」。實體操作是選一張放出、再選一張放出。
- 從決策開啟的魔書網格與棄牌區只靠發光標示可選的卡,看不出這次要選的是什麼。

## What Changes

- S-043 分裂:選一張放出,再選一張放出;第二張只剩一張時也由玩家選(`Choose.auto_single=False`)。不做一次選多張。
- 魔書網格(標題下)與棄牌區對話框,在有決策目標時顯示決策的通用標題與來源卡名;單純查閱時不顯示。
- 自動開啟選擇網格要等這批事件的放卡、棄牌演出播完(原本立刻開啟,蓋住第一張的飛卡)。
- 卡片進入棄牌區時播放飛向棄牌區的演出(原本魔物只在原位淡出,搭檔與魔書的卡沒有演出);`card_discarded` 事件加來源魔物槽。
- 修正演出中 CSS 自訂屬性的設定方式:以 `Object.assign(style, {"--x": …})` 設定無效,傷害能量、保護、棄牌的轉場時間因此沒生效而瞬移;改用 `setProperty`。
- 補上 effect-tree「Choose 節點自動驗證與自動解決」的例外(上一個 change 已加 `auto_single=False`,spec 未同步)。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `card-effects`:修改「選不到對象的非戰鬥戰術不能使用」(S-043 分裂的順序)。
- `effect-tree`:修改「Choose 節點自動驗證與自動解決」(`auto_single=False` 例外)。
- `battle-ui`:修改「選書對話框」(選擇提示、演出播完才自動開啟)、「事件動畫」(棄牌飛向棄牌區)。
- `game-engine`:新增「棄牌事件標明來源魔物槽」。

## Impact

- `src/gash/engine/effects/cards/spells.py`(S-043)。
- `src/gash/engine/engine.py`、`effects/primitives.py`、`effects/tree.py`:`card_discarded` 加 `slot`。
- `frontend/app.js`(`showBookReview`、`showDiscard`、自動開啟延後)、`frontend/anim.js`(棄牌演出、自訂屬性)、`frontend/style.css`。
- 測試:引擎、瀏覽器。
