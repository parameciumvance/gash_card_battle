# Proposal

## Why

公式大會與公認大會在 ADV ルール之外另加了兩條大會規則(atwiki「ルール」pages/87「大会ルール」;規則頁 pages/94 也提到「先攻の第1ターンのスタートフェイズには、ページをめくってもMPが増えない という大会ルールを使うことがあります」):

- 先攻の1ターン目はスタートフェイズにページをめくってもMPを増やせない。
- プロモーションカードは1種類につき1枚まで入れられる。

這兩條目前都沒有實作:先攻第 1 回合可以翻頁拿 MP,同一張 PR 卡也能放到 4 張。使用者決定不提供開關,所有模式一律套用,並把它們直接寫進基本規則。

## What Changes

- **BREAKING(遊戲行為)** 先攻玩家第 1 回合在開始階段翻頁時,頁照常翻開,但 MP 不增加。開局準備的 MP +2、第 1 回合結束階段的強制翻頁 +2、後攻玩家的第 1 回合不受影響。所有模式(線上、牌桌、NPC、自由調查時間)都適用。
- **BREAKING(構築)** 魔書中卡號以 `PR-` 開頭的卡,同一編號最多 1 張。伺服器的構築驗證(建房、加入、入座、預組、NPC 牌組)以 `deck.pr_copies` 拒絕;構築器的即時合法性提示也加上這條。瀏覽器裡已存的魔書若同一張 PR 卡放了 2 張以上,會變成不合法。
- 規則頁(四語)寫入這兩條。
- 開始階段的翻頁按鈕在先攻第 1 回合顯示「翻 N 張(MP +0)」,詳細提示改為說明這回合不得 MP。
- 開局特性測試的 golden(`tests/golden/battle_start.json`)若受第 1 回合 MP 影響,重新產生。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `game-engine`:「開始階段翻頁」加上先攻第 1 回合翻頁不增加 MP。
- `card-data`:新增「PR 卡同編號限 1 張」構築規則(所有構築驗證都適用,含預組)。
- `deck-builder`:「即時合法性提示」加上 PR 卡同編號 ≤1。
- `battle-ui`:「開始階段依魔書翻閱選擇翻頁張數」在先攻第 1 回合顯示 MP +0,詳細提示說明不得 MP。

## Impact

- 引擎:`src/gash/engine/engine.py` `_flip_pages`(P-035 依賴的 `start_phase_mp_gain` 也隨之為 0);`src/gash/engine/deck.py` `validate_deck`。
- 前端:`frontend/decks.js` 合法性檢查、四語 i18n(`deck.err.pr_copies`、`error.deck.pr_copies`)、規則頁內容檔 `frontend/i18n/rules.*.json`(簡中由 `tools/build_zh_cn.py` 產生)。
- 測試:先攻第 1 回合翻頁拿 MP 的既有測試與 golden 要調整;NPC 自我對戰的結果可能改變。
- 現有預組都沒有重複的 PR 卡,不受影響。
