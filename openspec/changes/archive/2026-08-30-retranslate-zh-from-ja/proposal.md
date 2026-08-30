## Why

`data/cards.zh-TW.json` 目前的翻譯基準不明確。比對新建立的權威日文來源(`data/cards_ja.csv`,經 `tools/scrape_ja_effects.py` 抓取並用真實頁面逐項核對過)後,發現至少 29 張卡(約 22%)的 `name_ja` 就跟權威來源對不上(如 E-021 現存 `ひと安心!`,權威來源實際是 `敵じゃない人がいる`)——顯示這不是零星筆誤,是整份翻譯檔案的來源本身有系統性偏差。既然權威來源已經確立且逐項核對過真實頁面,翻譯檔案應該以此為準全面重新核對/翻譯,而不是只修那 29 張表面對不上的。

## What Changes

- `name_ja`(日文原名):134 張既有卡全部改為 `cards_ja.csv` 的 `name_ja`(直接取用,無翻譯判斷)。
- `name`(中文譯名):逐卡核對是否仍貼合修正後的 `name_ja`;不符合的重新翻譯,措辭合理的維持不動。
- `attr`(屬性或《技能名》中譯):術卡依 `cards_ja.csv` 的 `attr_ja`(元素屬性)翻譯;魔物/夥伴卡依 `effect_ja` 開頭的《技能名》段落翻譯(未拆成獨立欄位,人工從 `effect_ja` 開頭讀取)。
- `effect`(效果全文中譯):依 `cards_ja.csv` 的 `effect_ja` 重新核對/翻譯(該欄位已排除 `related_mamodo_ja`/`related_partner_ja`/收錄產品等身分尾行,不需要再手動處理)。
- **範圍:134 張既有卡**(`cards.zh-TW.json` 現有卡號)。S-042(權威來源有、英文資料沒有的卡)不在此範圍,另案處理。
- **不影響**:`data/cards.json` 的數值與遊戲邏輯——`card-data` spec 既有需求已保證翻譯檔修改不影響引擎行為,此次沿用該保證,不重新驗證。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `card-data`:「中文翻譯檔獨立」需求明確化翻譯依據——由含糊的「依版日 j 文意」改為明確指向 `data/cards_ja.csv`(權威來源試算表的抓取結果)。

## Impact

- `data/cards.zh-TW.json`:134 張卡的 `name_ja`/`name`/`attr`/`effect` 四欄位全面核對更新
- `openspec/specs/card-data/spec.md`:「中文翻譯檔獨立」需求文字明確化翻譯依據
- 不影響:`data/cards.json`、遊戲引擎、`tools/scrape_ja_effects.py`
