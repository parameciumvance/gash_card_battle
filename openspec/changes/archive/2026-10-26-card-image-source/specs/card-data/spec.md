## MODIFIED Requirements

### Requirement: 卡片資料轉換
`data/cards.json` SHALL 由 `data/cards_ja.csv`(日文權威來源的抓取結果)轉換產生,而非由 xlsx 抽取。轉換 MUST 涵蓋該檔全部列(含未存在於舊 xlsx 來源的卡號),欄位對應規則(`cards.json` 不含卡圖連結;卡圖來源見「卡圖資產與備援」):

- `related_mamodo`(魔物家族識別鍵,戰術卡/搭檔卡/事件卡與其對應魔物卡必須相等以供引擎比對陣營歸屬)戰術卡/搭檔卡/事件卡 MUST 直接對應 `related_mamodo_ja`(空字串視為 null);魔物卡 MUST 以「`name_ja` 去除括號後綴(如「（変身後）」)」推導,使變身/形態卡(如 M-007「ゴフレ（変身後）」)的 `related_mamodo` 與其基礎家族名(「ゴフレ」)一致,並與同家族戰術卡/搭檔卡的 `related_mamodo_ja` 相等。
- `name_ja`/`effect_ja`(欄位命名反映實際內容為日文,對應 `CardDef.name_ja`/`effect_ja`)MUST 直接對應 `cards_ja.csv` 的 `name_ja`/`effect_ja`。
- `power`(單一字串欄位)MUST 解析回結構化格式:純數字(無加號)→ `{base: N}`;加號+數字 → `{bonus: N}`;「特殊」→ `{special: true}`;數字+倍率後綴(×)→ `{special: true, per_heads: N}`;空字串(搭檔/事件卡通常無 power)→ `{}`。
- `ad`/`class`/`cost`/`damage` MUST 直接對應同名或同語意欄位;`damage` 為「?」(傷害依效果決定)時 `damage` MUST 為 null 並另設 `damage_variable: true`。
- `attr_name` MUST 僅在卡片類型為戰術時填入該卡的 `attr_ja`(元素);魔物卡與搭檔卡的 `attr_name` MUST 為 null——此欄位在引擎中僅用於戰術卡的屬性相容性判定,不承擔任何顯示職責(顯示由 `data/cards.zh-TW.json` 的 `attr` 欄位負責)。
- `effect_icon` MUST 對應 `cards_ja.csv` 的 `effect_icon_ja`,轉為英文枚舉值:「バトル」→ `"battle"`、「非バトル」→ `"nonbattle"`、「ジャマー」→ `"jammer"`、空字串 → `null`。
- `sets`(前端依產品篩選卡片所讀取的收錄產品清單)MUST 沿用轉換前既有 `data/cards.json` 中同卡號的舊值;沒有對應舊值的卡號 MUST 取 xlsx 對應列的 Sets 欄(以「, 」分隔);兩者都沒有時 `sets` MUST 為空陣列,不得因此中止轉換或報錯。

#### Scenario: 變身形態魔物卡的家族識別鍵推導
- **WHEN** 轉換 M-007(`name_ja` 為「ゴフレ（変身後）」)
- **THEN** 該卡 `related_mamodo` 為「ゴフレ」,與 M-006(基礎形態,`related_mamodo` 亦為「ゴフレ」)及該家族戰術卡/搭檔卡(如 S-012、P-004,其 `related_mamodo_ja` 為「ゴフレ」)相等

#### Scenario: power 格式還原
- **WHEN** `cards_ja.csv` 某卡的 `power` 為「+4000」
- **THEN** 轉換後 `cards.json` 該卡的 `power` 為 `{"bonus": 4000}`

#### Scenario: 戰術卡以外不填屬性
- **WHEN** 轉換一張魔物卡或搭檔卡
- **THEN** 該卡 `attr_name` 為 null,不論其 `effect_ja` 開頭是否含《技能名》

#### Scenario: 非バトル術卡的 effect_icon 轉換
- **WHEN** 轉換一張 `effect_icon_ja` 為「非バトル」的戰術卡(如 S-041)
- **THEN** 該卡 `effect_icon` 為 `"nonbattle"`

#### Scenario: 轉換涵蓋來源全部卡號
- **WHEN** 轉換執行完成
- **THEN** `cards.json` 的卡號集合與 `cards_ja.csv` 完全一致(卡數相同,無遺漏、無多餘)

#### Scenario: 傷害依效果決定的戰術卡
- **WHEN** 轉換 `damage` 為「?」的 S-061
- **THEN** 該卡 `damage` 為 null,`damage_variable` 為 true

#### Scenario: 新卡的收錄產品取自 xlsx
- **WHEN** 轉換一張轉換前 `cards.json` 沒有的卡(如 M-048)
- **THEN** 該卡 `sets` 為 xlsx 對應列 Sets 欄的各產品

#### Scenario: image_url 直接從 xlsx 抽取
- **WHEN** 轉換一張 xlsx 中存在對應列、A 欄有超連結的卡(如 M-001)
- **THEN** 該卡沒有 `image_url` 欄位:xlsx 的卡圖超連結不再讀取(本情境名稱沿用;卡圖來源見「卡圖資產與備援」)

#### Scenario: 卡號在 xlsx 中無對應列
- **WHEN** 轉換一張不存在於 xlsx 的卡號
- **THEN** 該卡 `sets` 依沿用舊值或空陣列的規則決定,轉換正常完成不中止

#### Scenario: S-042 改直接讀取後找回卡圖連結
- **WHEN** 轉換 S-042(xlsx 中為 `S-042e`/`S-042j` 兩列)
- **THEN** 該卡沒有 `image_url` 欄位,其卡圖由「卡圖資產與備援」的資料夾提供(本情境名稱沿用)

### Requirement: 卡圖資產與備援
卡圖檔 SHALL 為 WebP,檔名 `{卡號}.webp`,尺寸與原圖相同並保留透明通道(卡片圓角)。卡圖的來源 SHALL 為使用者維護的公開 Google Drive 資料夾(`https://drive.google.com/drive/folders/1cXx4gpa41HiycU4hIN74xbp1Aj3hiE-k`),其中每張卡的圖檔名為 `{卡號}.webp`。卡圖下載腳本 SHALL 取得該資料夾的檔名清單,依 `cards.json` 的卡號下載對應的 `{卡號}.webp`,存至 `frontend/assets/cards/{卡號}.webp`:下載到的內容已是 WebP 時 SHALL 原樣存檔;不是 WebP 時 SHALL 轉成 WebP 後存檔。已存在 `{卡號}.webp` 的卡 SHALL 跳過(續抓);資料夾中沒有該卡的檔案或下載失敗時 SHALL 寫入失敗清單並繼續。其他格式的卡圖檔(例如舊的 `{卡號}.jpg`)MUST NOT 被當作已安裝的卡圖。卡圖缺失 MUST NOT 影響遊戲功能(前端以文字卡面呈現)。

#### Scenario: 依卡號從資料夾下載
- **WHEN** 資料夾中有 `M-001.webp`,本機沒有 `M-001.webp`
- **THEN** 腳本下載該檔並存成 `frontend/assets/cards/M-001.webp`,內容與資料夾中的檔案相同

#### Scenario: 資料夾中沒有的卡
- **WHEN** `cards.json` 有某卡號,資料夾中沒有對應的 `{卡號}.webp`
- **THEN** 腳本把該卡記入失敗清單並繼續處理其他卡,遊戲中該卡以文字卡面顯示

#### Scenario: 下載失敗不阻塞
- **WHEN** 某卡的檔案無法下載(例如回傳的是登入頁而非圖檔)
- **THEN** 腳本記錄至失敗清單並繼續,遊戲中該卡以文字卡面顯示

#### Scenario: 下載後存為 WebP
- **WHEN** 腳本下載到某卡的 PNG(含透明圓角)
- **THEN** 存成 `{卡號}.webp`,內容為 WebP,尺寸與原圖相同,圓角仍為透明

#### Scenario: 續抓只認 WebP
- **WHEN** 某卡已有 `{卡號}.webp`,另一卡只有舊的 `{卡號}.jpg`
- **THEN** 前者跳過不下載,後者重新下載並存成 `{卡號}.webp`
