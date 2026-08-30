## REMOVED Requirements

### Requirement: 卡片資料抽取
**Reason**: `data/cards.json` 的權威來源由 xlsx(英文,經 e/j 版本選擇)改為 `data/cards_ja.csv`(日文,經 `tools/scrape_ja_effects.py` 抓取並逐項核對真實頁面),不再需要這條 xlsx 抽取管線。已證實此來源不可靠(S-017/E-027/M-013 等多筆數值與權威日文來源不一致)。
**Migration**: 改用新的「卡片資料轉換」需求(見下)。`tools/extract_cards.py` 一併刪除;`openspec/specs/card-data/Zatch Bell CCG List for TTS.xlsx` 保留作為歷史快照,不再是任何工具的輸入。

抽取腳本 SHALL 讀取 xlsx「The Table」工作表,過濾 Sets 含 "Level 1"、**"Level 2" 或 "Series 1 Level 2"(資料例外標籤)** 的卡,自 HYPERLINK 顯示文字取得卡號;同卡號存在 e/j 兩版時 MUST 只保留 j 版並以基礎卡號(去除尾碼)入庫;**同卡號同時符合多個過濾產品時 MUST 只入庫一筆,sets 取聯集**。產出 `data/cards.json`,每張卡含:卡號、類型(魔物/夥伴/術/事件)、卡名(英)、對應魔物、費用、A/D、級別(無/中級/上級)、屬性/效果名、效果原文、魔力、傷害、收錄產品清單(Sets 欄逗號拆分)、卡圖連結。

#### Scenario: e/j 去重採日版
- **WHEN** 抽取遇到 S-019e 與 S-019j 兩列
- **THEN** cards.json 僅含一筆 S-019,其效果文為 j 版內容

#### Scenario: Level 2 的 e/j 差異卡採日版
- **WHEN** 抽取遇到 E-018e 與 E-018j(效果文不同)
- **THEN** cards.json 的 E-018 效果文為 j 版(含「上一回合已減過對手 MP 則不減」條款)

#### Scenario: 抽出 134 種卡
- **WHEN** 抽取腳本執行完成
- **THEN** cards.json 恰含 134 種唯一卡號(第一彈 67 + Level 2 新增 67:M×16+P×10+S×29+E×12)

#### Scenario: 收錄產品入庫
- **WHEN** 某卡的 Sets 欄為 "Series 1, Level 1, The Best Booster 1"
- **THEN** cards.json 該卡的 sets 為三個產品標籤的清單

#### Scenario: Series 1 Level 2 標籤例外
- **WHEN** 某卡 Sets 欄僅含 "Series 1 Level 2"(缺逗號的資料例外)
- **THEN** 該卡被納入抽取範圍

## ADDED Requirements

### Requirement: 卡片資料轉換
`data/cards.json` SHALL 由 `data/cards_ja.csv`(日文權威來源的抓取結果)轉換產生,而非由 xlsx 抽取。轉換 MUST 涵蓋該檔全部列(含未存在於舊 xlsx 來源的卡號),欄位對應規則:

- `related_mamodo`(魔物家族識別鍵,術卡/夥伴卡/事件卡與其對應魔物卡必須相等以供引擎比對陣營歸屬)術卡/夥伴卡/事件卡 MUST 直接對應 `related_mamodo_ja`(空字串視為 null);魔物卡 MUST 以「`name_ja` 去除括號後綴(如「（変身後）」)」推導,使變身/形態卡(如 M-007「ゴフレ（変身後）」)的 `related_mamodo` 與其基礎家族名(「ゴフレ」)一致,並與同家族術卡/夥伴卡的 `related_mamodo_ja` 相等。
- `power`(單一字串欄位)MUST 解析回結構化格式:純數字(無加號)→ `{base: N}`;加號+數字 → `{bonus: N}`;「特殊」→ `{special: true}`;數字+倍率後綴(×)→ `{special: true, per_heads: N}`;空字串(夥伴/事件卡通常無 power)→ `{}`。
- `ad`/`class`/`cost`/`damage` MUST 直接對應同名或同語意欄位。
- `attr_name` MUST 僅在卡片類型為術時填入該卡的 `attr_ja`(元素);魔物卡與夥伴卡的 `attr_name` MUST 為 null——此欄位在引擎中僅用於術卡的屬性相容性判定,不承擔任何顯示職責(顯示由 `data/cards.zh-TW.json` 的 `attr` 欄位負責)。
- `image_url` MUST 沿用轉換前既有 `data/cards.json` 中同卡號的舊值;沒有對應舊值的卡號(不存在於轉換前的資料集)`image_url` MUST 為 null,不得因此中止轉換或報錯。
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

#### Scenario: 新卡沿用不到舊卡圖連結
- **WHEN** 轉換一張不存在於轉換前 `cards.json` 的卡號
- **THEN** 該卡的 `image_url` 為 null,轉換正常完成不中止

#### Scenario: 轉換涵蓋來源全部卡號
- **WHEN** 轉換執行完成
- **THEN** `cards.json` 的卡號集合與 `cards_ja.csv` 完全一致(卡數相同,無遺漏、無多餘)
