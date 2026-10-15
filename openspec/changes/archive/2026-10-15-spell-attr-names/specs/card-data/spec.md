## MODIFIED Requirements

### Requirement: 日文與英文卡片文字
日文與英文的卡片文字 SHALL 各存於獨立檔 `data/cards.ja.json`、`data/cards.en.json`,與 `data/cards.zh-TW.json` 相同結構(以卡號為 key,含 `name`、`name_ja`、`attr`、`effect`),涵蓋 `cards.json` 的全部卡號。修改這兩個檔 MUST NOT 影響 `cards.json` 的數值與邏輯。

- `cards.ja.json` SHALL 由工具自 `data/cards_ja.csv` 產生,不手動編輯:`name` 與 `name_ja` 為 `name_ja`;`effect` 為 `effect_ja`;`attr` 對戰術卡為 `attr_ja`(元素),對魔物卡與搭檔卡為 `effect_ja` 中第一個《》括起的效果名,沒有時為 null。
- `cards.en.json` 的 `name` 與 `attr` SHALL 取自 `card-data` 的 TTS 卡表(`Zatch Bell CCG List for TTS.xlsx`)的英文卡名與 Attribute / Effect Name;卡表的屬性欄為「-」而該戰術卡在日文資料有元素時,`attr` SHALL 為卡表中同一元素其他戰術的英文,卡表沒有該元素的英文時為 null。`effect` SHALL 依 `effect_ja` 翻譯,MUST NOT 以卡表或卡圖上的英文效果文為依據(兩者與日文效果文有出入)。`name_ja` MUST 與 `data/cards_ja.csv` 一致。

#### Scenario: 日文文字與權威來源一致
- **WHEN** 比對 `cards.ja.json` 與 `data/cards_ja.csv`
- **THEN** 每張卡的 `name` 與 `effect` 與該檔的 `name_ja`、`effect_ja` 完全相同

#### Scenario: 魔物的日文效果名
- **WHEN** 產生 M-001 的日文文字
- **THEN** `attr` 為「やさしい王様」(取自效果文開頭的《やさしい王様》)

#### Scenario: 英文涵蓋全部卡片
- **WHEN** 檢查 `cards.en.json`
- **THEN** `cards.json` 的每個卡號都有非空的英文 `name` 與 `effect`,M-001 的 `name` 為「Zatch Bell」

#### Scenario: 卡表缺漏的戰術元素
- **WHEN** 產生 S-091 的英文文字(卡表屬性欄為「-」,日文元素為「雷」)
- **THEN** `attr` 為「Thunder」(卡表中其他雷屬性戰術的英文)

## ADDED Requirements

### Requirement: 戰術屬性譯名一致
同一個日文元素(戰術卡的 `attr_name`)在 `cards.zh-TW.json` 與 `cards.en.json` 中 SHALL 各只對應一種譯名;有元素的戰術卡,這兩個檔的 `attr` MUST NOT 為空;日文資料沒有元素的戰術卡(含指令戰術),`attr` MUST 為空,不另訂屬性。簡體中文由繁體中文轉換,隨之一致。

#### Scenario: 雷屬性的繁中譯名
- **WHEN** 檢查所有日文元素為「雷」的戰術卡(含 S-001、S-029)的繁中 `attr`
- **THEN** 全部為「雷」

#### Scenario: 沒有元素的戰術沒有屬性
- **WHEN** 檢查 S-058(傑昂的「ザケル」,日文資料沒有元素)與指令戰術 S-026 的繁中 `attr`
- **THEN** 兩者皆為空
