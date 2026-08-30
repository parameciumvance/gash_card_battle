## MODIFIED Requirements

### Requirement: 中文翻譯檔獨立
中文文本 SHALL 存於獨立檔 `data/cards.zh-TW.json`,以卡號為 key,含:卡名中譯、卡名日文原名、效果名中譯、效果全文中譯、風味文中譯(可缺)。翻譯依據 SHALL 為 `data/cards_ja.csv`(權威來源試算表的抓取結果,見 `tools/scrape_ja_effects.py`):卡名日文原名 MUST 與該檔的 `name_ja` 一致;效果全文中譯 SHALL 依該檔的 `effect_ja` 翻譯(該欄位已排除身分尾行與收錄產品資訊)。修改翻譯 MUST NOT 影響 cards.json 的數值與邏輯。結構 SHALL 允許並列新增其他語言檔。

#### Scenario: 校對翻譯不動邏輯
- **WHEN** 修改 cards.zh-TW.json 中某術名的音譯
- **THEN** 遊戲數值行為完全不變,僅 UI 顯示文字更新

#### Scenario: 卡名日文原名以權威來源為準
- **WHEN** 核對某卡的 `name_ja` 與 `data/cards_ja.csv` 對應列的 `name_ja` 不一致
- **THEN** `cards.zh-TW.json` 的 `name_ja` MUST 更正為與 `data/cards_ja.csv` 一致
