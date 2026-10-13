## Why

開始做第三彈。第一步是卡片資料:目前資料只到第二彈(M-031、P-019、S-058、E-027)。第三彈的 102 張分布在四個商品:LEVEL:3「金色の超呪文」、カードセット「ガッシュ・ベルと仲間達」「ゼオンと最凶魔物達」、魔本ファイル。抓取工具遇到新標記(元素「土」、傷害「ダメージ?」)會中止,也無法只抓指定範圍的卡。

效果要分好幾批實作,資料先進來時,還沒實作的卡不能讓玩家放進魔書。

## What Changes

- 抓取工具:新增元素「土」;「ダメージ?」存為「?」(傷害依效果決定);可指定卡號範圍(魔本ファイル頁還有後續彈的卡)。抓齊四個商品頁的 102 張。
- 轉換工具:「?」傷害轉為 `damage: null` + `damage_variable: true`;新卡的收錄產品取自 TTS 卡表的 Sets 欄。
- 卡片文字:日文由工具產生;英文卡名取自 TTS 卡表,英文效果文由 AI 起草;繁中卡名與效果文由 AI 起草(都標為初版,待校對);簡中由工具產生。
- 卡圖:以既有工具自 TTS 卡表的 Drive 連結下載(卡圖不進版控,正式站需另外上傳)。
- 尚未開放的卡:`data/pending_cards.json` 列出效果尚未實作的卡號(先放第三彈全部 102 張);構築規則拒絕(`deck.card_pending`);構築器與金手指的卡池不顯示,產品篩選只列有開放卡片的產品。之後每批效果實作完成時自清單移除。
- 卡面:傷害依效果決定的戰術顯示「傷害 ?」。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `card-data`:新增「第三彈卡片資料」「尚未開放的卡片」;修改「卡片資料轉換」「日文權威資料抓取(atwiki)」。
- `deck-builder`:新增「卡池不顯示尚未開放的卡」;修改「即時合法性提示」。

## Impact

- `tools/scrape_ja_effects.py`、`tools/build_cards_json.py`、`tools/build_card_texts.py`(視需要)。
- `data/cards_ja.csv`、`data/cards.json`、`data/cards.{zh-TW,zh-CN,en,ja}.json`、新增 `data/pending_cards.json`。
- `src/gash/engine/cards.py`(`damage_variable`、尚未開放清單)、`src/gash/engine/deck.py`(驗證)。
- `frontend/app.js`、`frontend/decks.js`(卡池、合法性、卡面傷害顯示)、i18n(`deck.err.pending`、錯誤碼)。
- 測試:資料、工具、構築規則、瀏覽器;`test_deck.py` 的卡片總數。
