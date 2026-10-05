## ADDED Requirements

### Requirement: 日文與英文卡片文字
日文與英文的卡片文字 SHALL 各存於獨立檔 `data/cards.ja.json`、`data/cards.en.json`,與 `data/cards.zh-TW.json` 相同結構(以卡號為 key,含 `name`、`name_ja`、`attr`、`effect`),涵蓋 `cards.json` 的全部卡號。修改這兩個檔 MUST NOT 影響 `cards.json` 的數值與邏輯。

- `cards.ja.json` SHALL 由工具自 `data/cards_ja.csv` 產生,不手動編輯:`name` 與 `name_ja` 為 `name_ja`;`effect` 為 `effect_ja`;`attr` 對術卡為 `attr_ja`(元素),對魔物卡與搭檔卡為 `effect_ja` 中第一個《》括起的效果名,沒有時為 null。
- `cards.en.json` 的 `name` 與 `attr` SHALL 取自 `card-data` 的 TTS 卡表(`Zatch Bell CCG List for TTS.xlsx`)的英文卡名與 Attribute / Effect Name;`effect` SHALL 依 `effect_ja` 翻譯,MUST NOT 以卡表或卡圖上的英文效果文為依據(兩者與日文效果文有出入)。`name_ja` MUST 與 `data/cards_ja.csv` 一致。

#### Scenario: 日文文字與權威來源一致
- **WHEN** 比對 `cards.ja.json` 與 `data/cards_ja.csv`
- **THEN** 每張卡的 `name` 與 `effect` 與該檔的 `name_ja`、`effect_ja` 完全相同

#### Scenario: 魔物的日文效果名
- **WHEN** 產生 M-001 的日文文字
- **THEN** `attr` 為「やさしい王様」(取自效果文開頭的《やさしい王様》)

#### Scenario: 英文涵蓋全部卡片
- **WHEN** 檢查 `cards.en.json`
- **THEN** `cards.json` 的每個卡號都有非空的英文 `name` 與 `effect`,M-001 的 `name` 為「Zatch Bell」
