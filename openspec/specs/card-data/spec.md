# card-data — 卡片資料庫與資產管線

## Purpose

資料以 `tools/scrape_ja_effects.py` 從 atwiki 日文權威來源抓取為 `data/cards_ja.csv`,再由 `tools/build_cards_json.py` 轉換為 repo 內版本化的 `data/cards.json`;翻譯與卡圖為獨立層。
## Requirements
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

### Requirement: 中文翻譯檔獨立
中文文本 SHALL 存於獨立檔 `data/cards.zh-TW.json`,以卡號為 key,含:卡名中譯、卡名日文原名、效果名中譯、效果全文中譯、風味文中譯(可缺)。翻譯依據 SHALL 為 `data/cards_ja.csv`(權威來源試算表的抓取結果,見 `tools/scrape_ja_effects.py`):卡名日文原名 MUST 與該檔的 `name_ja` 一致;效果全文中譯 SHALL 依該檔的 `effect_ja` 翻譯(該欄位已排除身分尾行與收錄產品資訊)。修改翻譯 MUST NOT 影響 cards.json 的數值與邏輯。結構 SHALL 允許並列新增其他語言檔。

#### Scenario: 校對翻譯不動邏輯
- **WHEN** 修改 cards.zh-TW.json 中某術名的音譯
- **THEN** 遊戲數值行為完全不變,僅 UI 顯示文字更新

#### Scenario: 卡名日文原名以權威來源為準
- **WHEN** 核對某卡的 `name_ja` 與 `data/cards_ja.csv` 對應列的 `name_ja` 不一致
- **THEN** `cards.zh-TW.json` 的 `name_ja` MUST 更正為與 `data/cards_ja.csv` 一致

### Requirement: 預組魔本資料
`ref/raw/deck/level1.txt` SHALL 轉為 `data/decks/level1.json`:32 個頁位依序對應卡號;載入時 MUST 驗證構築合法性(32 頁全滿、第 1 頁魔物、最後一頁術、中級 12 頁後、上級 22 頁後、同號 ≤4、魔物 ≤8)且每個卡號存在於 cards.json。

#### Scenario: 預組魔本通過驗證
- **WHEN** 引擎載入 level1.json
- **THEN** 驗證通過:P01=M-001、P32=S-005(上級,位於 22 頁後)、S-001×3 未超限

#### Scenario: 非法魔本被拒
- **WHEN** 載入一份第 1 頁不是魔物卡的魔本資料
- **THEN** 載入失敗並回報違反的規則

### Requirement: 卡圖資產與備援
卡圖下載腳本 SHALL 依 cards.json 中的 Google Drive 連結批次下載至 `frontend/assets/cards/{卡號}.jpg`,支援續抓並輸出失敗清單;卡圖缺失 MUST NOT 影響遊戲功能(前端以文字卡面呈現)。

#### Scenario: 下載失敗不阻塞
- **WHEN** 某卡的 Drive 連結無法存取
- **THEN** 腳本記錄至失敗清單並繼續,遊戲中該卡以文字卡面顯示

### Requirement: 日文權威資料抓取(atwiki)
`tools/scrape_ja_effects.py` SHALL 從 atwiki 的產品頁(如 LEVEL:1/2 booster 頁)的「収録カード」區塊,依 魔物/術/パートナー/イベント 分類取得每張卡的卡號、名稱與個別卡頁連結;逐一抓個別卡頁,解析 `<blockquote>` 內的官方資料區塊。`<blockquote>` 內以 `<hr/>` 分隔的 `<div>` 段數 MUST NOT 假設固定為 2 段——部分卡片(如卡面印有變身疊放條件、術相容性規則等「框線規則」的魔物卡)會多出中間段落。解析 MUST 一律取第一段當資料頭來源、最後一段當風味文/收錄產品來源,中間任意段數的內容 MUST 併入效果文,唯獨字面完全等於「以上、枠囲み」(純排版提示,表示前一段內容印在卡面框線內,非遊戲內容)的段落 MUST 被過濾、不併入效果文:

- 第一段(捨棄第一行卡號+名稱後):資料頭 1~2 行,逐 token(全形空白分隔)封閉分類,MUST 落在下列其中一類,否則視為未知標籤 MUST raise(不得歸類為屬性等開放欄位,不得靜默略過):類型(魔物/術/パートナー/イベント,已知略過)/級別(中級→intermediate、上級→superior)/費用(「MP」前綴+數字)/傷害(「ダメージ」前綴+數字)/power(見下)/元素屬性(水/火/雷/氷/木/風/重力)/效果 icon(バトル/非バトル/ジャマー)/回合欄位(「バトル攻撃」/「バトル防御」/「自分のターン」/「相手のターン」,四者換算為 A/D/AD)。
- power 為單一欄位,以字串保留格式標記以區分語意:純數字(如「4000」,魔物基礎魔力,無加號)/加號+數字(如「＋4000」,術的魔力加值,存為「+4000」)/「特殊」(Special)/數字+倍率後綴(如「2000×」,擲幣倍率型;後綴 MUST 同時接受乘號「×」與英文字母 x/X,wiki 頁面實際使用乘號)。
- 必填欄位依卡片類型而定:イベント/術 MUST 有回合欄位(ad);魔物/術 MUST 有 power。解析 MUST 先只讀資料頭第 1 行;第 1 行已滿足該卡類型的必填欄位時,MUST NOT 繼續讀第 2 行(第 2 行整行視為效果文);第 1 行未滿足時 MUST 接著讀第 2 行合併判斷;讀完 2 行仍未滿足必填欄位時,若該卡號登記於已知資料缺漏清單(對照英文資料核對過的官方頁面漏刊,非解析錯誤)MUST 套用登記的欄位覆寫值,否則 MUST raise。
- 資料頭之後為效果文,依卡片類型解析對應魔物身分尾行。尾行判斷 MUST 以「最後一個句號(。)之後的文字段落」為比對範圍,不要求該段落自成一行——尾行可能與前一句效果文黏在同一行(無 `<br/>` 分隔),此時句號前的敘述文字仍 MUST 保留在 effect_ja。依卡片類型:
  - 術卡:段落符合「<魔物名>第N の術」格式(魔物名可包在 `<a>` 連結中,亦可為純文字,兩者皆 MUST 支援),取魔物名存入 related_mamodo_ja 並排除於效果文之外;段落若為「コマンド」(指示術,不屬於特定魔物,對應英文 `related_mamodo: "Command: All"`),related_mamodo_ja MUST 存為「コマンド」並同樣排除於效果文之外。
  - 夥伴卡:段落符合「魔物＝<名字>」格式(純文字,無連結),取名字存入 related_mamodo_ja 並排除於效果文之外。
  - 魔物卡:MUST NOT 自動解析 related_mamodo_ja(不論基本形態或變身形態,一律留空;基本形態亦不自我參照為自己的 name_ja)——此身分之後如需使用,由人工從效果內文判斷。魔物卡另有對應搭檔的身分尾行(見下)。
  - 事件卡:MUST NOT 有 related_mamodo_ja 或 related_partner_ja(對照英文資料確認事件卡無此概念)。
  - 術卡與夥伴卡 MUST 有 related_mamodo_ja(必填);解析不出時,若卡號登記於已知資料缺漏清單 MUST 套用登記的覆寫值,否則 MUST raise。此檢查於尾行解析完成後進行,與資料頭 token 的必填檢查(ad/power)為各自獨立的檢查時機。
- 魔物卡另需解析對應搭檔的身分尾行:段落符合「パートナー＝<名字>」格式(純文字,無連結),取名字存入 related_partner_ja 並排除於效果文之外——與夥伴卡的「魔物＝X」尾行鏡像對稱(夥伴宣告對應魔物,魔物宣告對應夥伴)。魔物卡 MUST 有 related_partner_ja(必填);解析不出時,若卡號登記於已知資料缺漏清單 MUST 套用登記的覆寫值,否則 MUST raise,檢查時機與 related_mamodo_ja 相同(尾行解析完成後)。
- 最後一段:第一行為 flavor_ja(風味文),其餘每行為一筆收錄產品,合併存入 sets_ja。

輸出至 `data/cards_ja.csv`;已存在於輸出檔的卡號 MUST 跳過(支援分批執行、中斷續抓),每處理完一張卡 MUST 立即寫回檔案。

#### Scenario: 夥伴卡解析對應魔物
- **WHEN** 解析一張夥伴卡,資料區塊最後一行為「魔物＝ガッシュ・ベル」
- **THEN** related_mamodo_ja 為「ガッシュ・ベル」,該行不出現在 effect_ja 中

#### Scenario: 魔物卡一律不解析對應魔物
- **WHEN** 解析任一張魔物卡(不論基本或變身形態)
- **THEN** related_mamodo_ja 恆為空字串,不嘗試從卡名或效果文推論

#### Scenario: 術卡的魔物名無連結時仍可解析
- **WHEN** 解析一張術卡,尾段為純文字「<魔物名>第N の術」,魔物名沒有包在 `<a>` 連結中
- **THEN** related_mamodo_ja 正確解析為該魔物名

#### Scenario: 指示術不屬於特定魔物
- **WHEN** 解析一張術卡,尾段為「コマンド」
- **THEN** related_mamodo_ja 存為「コマンド」,該段落不出現在 effect_ja 中

#### Scenario: 尾段與前一句效果文同一行時正確切分
- **WHEN** 解析一張術卡,最後一行為「<敘述句>。<魔物名>第N の術」(無 `<br/>` 分隔)
- **THEN** related_mamodo_ja 正確解析為魔物名,句號前的敘述句完整保留於 effect_ja

#### Scenario: 術卡/夥伴卡缺少對應魔物身分且未登記已知缺漏時報錯
- **WHEN** 一張術卡或夥伴卡讀完效果文仍解析不出 related_mamodo_ja,且卡號未登記於已知資料缺漏清單
- **THEN** raise ValueError,不產出該卡的殘缺資料列

#### Scenario: 已知資料缺漏套用登記的對應魔物覆寫值
- **WHEN** 一張登記於已知資料缺漏清單的夥伴卡(如 P-018,頁面尾行寫成「パートナー＝X」而非「魔物＝X」)解析不出 related_mamodo_ja
- **THEN** 套用清單中登記的覆寫值,不 raise

#### Scenario: 魔物卡解析對應搭檔
- **WHEN** 解析一張魔物卡,資料區塊最後一行為「パートナー＝高嶺清麿」
- **THEN** related_partner_ja 為「高嶺清麿」,該行不出現在 effect_ja 中

#### Scenario: 魔物卡缺少對應搭檔且未登記已知缺漏時報錯
- **WHEN** 一張魔物卡讀完效果文仍解析不出 related_partner_ja,且卡號未登記於已知資料缺漏清單
- **THEN** raise ValueError,不產出該卡的殘缺資料列

#### Scenario: 框線規則卡的中間段落正確併入效果文
- **WHEN** 解析一張魔物卡,資料區塊為 4 段 `<div>`(數值列段/「以上、枠囲み」提示段/《能力》效果文+パートナー＝X 段/風味文段)
- **THEN** 「以上、枠囲み」不出現在 effect_ja 中;數值列段的框線規則文字與《能力》段的效果文都完整保留於 effect_ja;related_partner_ja 正確解析自最後一個有效段落

