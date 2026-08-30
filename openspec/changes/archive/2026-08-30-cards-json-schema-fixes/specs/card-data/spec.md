## MODIFIED Requirements

### Requirement: 卡片資料轉換
`data/cards.json` SHALL 由 `data/cards_ja.csv`(日文權威來源的抓取結果)轉換產生,而非由 xlsx 抽取。轉換 MUST 涵蓋該檔全部列(含未存在於舊 xlsx 來源的卡號),欄位對應規則:

- `related_mamodo`(魔物家族識別鍵,術卡/夥伴卡/事件卡與其對應魔物卡必須相等以供引擎比對陣營歸屬)術卡/夥伴卡/事件卡 MUST 直接對應 `related_mamodo_ja`(空字串視為 null);魔物卡 MUST 以「`name_ja` 去除括號後綴(如「（変身後）」)」推導,使變身/形態卡(如 M-007「ゴフレ（変身後）」)的 `related_mamodo` 與其基礎家族名(「ゴフレ」)一致,並與同家族術卡/夥伴卡的 `related_mamodo_ja` 相等。
- `name_ja`/`effect_ja`(欄位命名反映實際內容為日文,對應 `CardDef.name_ja`/`effect_ja`)MUST 直接對應 `cards_ja.csv` 的 `name_ja`/`effect_ja`。
- `power`(單一字串欄位)MUST 解析回結構化格式:純數字(無加號)→ `{base: N}`;加號+數字 → `{bonus: N}`;「特殊」→ `{special: true}`;數字+倍率後綴(×)→ `{special: true, per_heads: N}`;空字串(夥伴/事件卡通常無 power)→ `{}`。
- `ad`/`class`/`cost`/`damage` MUST 直接對應同名或同語意欄位。
- `attr_name` MUST 僅在卡片類型為術時填入該卡的 `attr_ja`(元素);魔物卡與夥伴卡的 `attr_name` MUST 為 null——此欄位在引擎中僅用於術卡的屬性相容性判定,不承擔任何顯示職責(顯示由 `data/cards.zh-TW.json` 的 `attr` 欄位負責)。
- `effect_icon` MUST 對應 `cards_ja.csv` 的 `effect_icon_ja`,轉為英文枚舉值:「バトル」→ `"battle"`、「非バトル」→ `"nonbattle"`、「ジャマー」→ `"jammer"`、空字串 → `null`。
- `image_url` MUST 直接從 `openspec/specs/card-data/Zatch Bell CCG List for TTS.xlsx` 讀取(A 欄儲存格的 HYPERLINK 公式或儲存格超連結),以卡號(去除 e/j 版本尾碼)比對 `cards_ja.csv` 的卡號做對應;xlsx 中沒有對應卡號的,`image_url` MUST 為 null,不得因此中止轉換或報錯(注意:S-042 過去因 Sets 標籤格式不同於舊抽取腳本的過濾條件而被誤判為「xlsx 沒有這張卡」,實際上 xlsx 內有對應列,改直接讀取後已能正確取得其 `image_url`)。
- `sets`(前端依產品篩選卡片所讀取的收錄產品清單)MUST 沿用轉換前既有 `data/cards.json` 中同卡號的舊值;沒有對應舊值的卡號 `sets` MUST 為空陣列,不得因此中止轉換或報錯。

#### Scenario: 變身形態魔物卡的家族識別鍵推導
- **WHEN** 轉換 M-007(`name_ja` 為「ゴフレ（変身後）」)
- **THEN** 該卡 `related_mamodo` 為「ゴフレ」,與 M-006(基礎形態,`related_mamodo` 亦為「ゴフレ」)及該家族術卡/夥伴卡(如 S-012、P-004,其 `related_mamodo_ja` 為「ゴフレ」)相等

#### Scenario: power 格式還原
- **WHEN** `cards_ja.csv` 某卡的 `power` 為「+4000」
- **THEN** 轉換後 `cards.json` 該卡的 `power` 為 `{"bonus": 4000}`

#### Scenario: 術卡以外不填屬性
- **WHEN** 轉換一張魔物卡或夥伴卡
- **THEN** 該卡 `attr_name` 為 null,不論其 `effect_ja` 開頭是否含《技能名》

#### Scenario: 非バトル術卡的 effect_icon 轉換
- **WHEN** 轉換一張 `effect_icon_ja` 為「非バトル」的術卡(如 S-041)
- **THEN** 該卡 `effect_icon` 為 `"nonbattle"`

#### Scenario: image_url 直接從 xlsx 抽取
- **WHEN** 轉換一張 xlsx 中存在對應列的卡(如 M-001)
- **THEN** 該卡 `image_url` 為該列 A 欄儲存格的超連結目標,不依賴轉換前 `cards.json` 是否存在該卡

#### Scenario: 卡號在 xlsx 中無對應列
- **WHEN** 轉換一張不存在於 xlsx 的卡號
- **THEN** 該卡的 `image_url` 為 null,轉換正常完成不中止

#### Scenario: S-042 改直接讀取後找回卡圖連結
- **WHEN** 轉換 S-042(過去因 Sets 標籤格式被舊抽取腳本排除,沿用舊值時期 `image_url` 一直是 null)
- **THEN** 該卡的 `image_url` 為 xlsx 對應列(`S-042e`/`S-042j`)A 欄儲存格的超連結目標,不再是 null

#### Scenario: 轉換涵蓋來源全部卡號
- **WHEN** 轉換執行完成
- **THEN** `cards.json` 的卡號集合與 `cards_ja.csv` 完全一致(卡數相同,無遺漏、無多餘)
