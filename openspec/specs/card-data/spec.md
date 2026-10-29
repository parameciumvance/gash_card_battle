# card-data — 卡片資料庫與資產管線

## Purpose

資料以 `tools/scrape_ja_effects.py` 從 atwiki 日文權威來源抓取為 `data/cards_ja.csv`,再由 `tools/build_cards_json.py` 轉換為 repo 內版本化的 `data/cards.json`;翻譯與卡圖為獨立層。

## Requirements

### Requirement: 卡片資料轉換
`data/cards.json` SHALL 由 `data/cards_ja.csv`(日文權威來源的抓取結果)轉換產生,而非由 xlsx 抽取。轉換 MUST 涵蓋該檔全部列(含未存在於舊 xlsx 來源的卡號),欄位對應規則(`cards.json` 不含卡圖連結,卡圖來源見「卡圖資產與備援」;`sets` 見「收錄產品資料」):

- `related_mamodo`(魔物家族識別鍵,戰術卡/搭檔卡/事件卡與其對應魔物卡必須相等以供引擎比對陣營歸屬)戰術卡/搭檔卡/事件卡 MUST 直接對應 `related_mamodo_ja`(空字串視為 null);魔物卡 MUST 以「`name_ja` 去除括號後綴(如「（変身後）」)」推導,使變身/形態卡(如 M-007「ゴフレ（変身後）」)的 `related_mamodo` 與其基礎家族名(「ゴフレ」)一致,並與同家族戰術卡/搭檔卡的 `related_mamodo_ja` 相等。
- `name_ja`/`effect_ja`(欄位命名反映實際內容為日文,對應 `CardDef.name_ja`/`effect_ja`)MUST 直接對應 `cards_ja.csv` 的 `name_ja`/`effect_ja`。
- `power`(單一字串欄位)MUST 解析回結構化格式:純數字(無加號)→ `{base: N}`;加號+數字 → `{bonus: N}`;「特殊」→ `{special: true}`;數字+倍率後綴(×)→ `{special: true, per_heads: N}`;空字串(搭檔/事件卡通常無 power)→ `{}`。
- `ad`/`class`/`cost`/`damage` MUST 直接對應同名或同語意欄位;`damage` 為「?」(傷害依效果決定)時 `damage` MUST 為 null 並另設 `damage_variable: true`。
- `attr_name` MUST 僅在卡片類型為戰術時填入該卡的 `attr_ja`(元素);魔物卡與搭檔卡的 `attr_name` MUST 為 null——此欄位在引擎中僅用於戰術卡的屬性相容性判定,不承擔任何顯示職責(顯示由 `data/cards.zh-TW.json` 的 `attr` 欄位負責)。
- `effect_icon` MUST 對應 `cards_ja.csv` 的 `effect_icon_ja`,轉為英文枚舉值:「バトル」→ `"battle"`、「非バトル」→ `"nonbattle"`、「ジャマー」→ `"jammer"`、空字串 → `null`。

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

#### Scenario: cards.json 不含卡圖連結
- **WHEN** 轉換執行完成
- **THEN** 每張卡都沒有 `image_url` 欄位(卡圖來源見「卡圖資產與備援」)

### Requirement: 中文翻譯檔獨立
中文文本 SHALL 存於獨立檔 `data/cards.zh-TW.json`,以卡號為 key,含:卡名中譯、卡名日文原名、效果名中譯、效果全文中譯、風味文中譯(可缺)。翻譯依據 SHALL 為 `data/cards_ja.csv`(權威來源試算表的抓取結果,見 `tools/scrape_ja_effects.py`):卡名日文原名 MUST 與該檔的 `name_ja` 一致;效果全文中譯 SHALL 依該檔的 `effect_ja` 翻譯(該欄位已排除身分尾行與收錄產品資訊)。修改翻譯 MUST NOT 影響 cards.json 的數值與邏輯。結構 SHALL 允許並列新增其他語言檔。

#### Scenario: 校對翻譯不動邏輯
- **WHEN** 修改 cards.zh-TW.json 中某戰術名的音譯
- **THEN** 遊戲數值行為完全不變,僅 UI 顯示文字更新

#### Scenario: 卡名日文原名以權威來源為準
- **WHEN** 核對某卡的 `name_ja` 與 `data/cards_ja.csv` 對應列的 `name_ja` 不一致
- **THEN** `cards.zh-TW.json` 的 `name_ja` MUST 更正為與 `data/cards_ja.csv` 一致

### Requirement: 預組魔書資料
`data/decks/` 的每個預組 SHALL 以 32 個頁位依序對應卡號,並記錄來源:`level1.json` 由 `ref/raw/deck/level1.txt` 轉換;`level2.json`、`gash-nakama.json`、`zeon.json` 依 atwiki 構築済み魔本頁(「黒き魔界よりの使者」pages/2054、「ガッシュ・ベルと仲間達」pages/2056、「ゼオンと最凶魔物達」pages/2057)的頁序。載入時 MUST 驗證構築合法性(32 頁全滿、第 1 頁魔物、最後一頁戰術、中級 12 頁後、上級 22 頁後、同號 ≤4、魔物 ≤8、不含尚未開放的卡)且每個卡號存在於 cards.json。每個預組 SHALL 有 `name_key`,其名稱在四種語言的介面字典中都有翻譯。

#### Scenario: 預組魔書通過驗證
- **WHEN** 引擎載入 level1.json
- **THEN** 驗證通過:P01=M-001、P32=S-005(上級,位於 22 頁後)、S-001×3 未超限

#### Scenario: 非法魔書被拒
- **WHEN** 載入一份第 1 頁不是魔物卡的魔書資料
- **THEN** 載入失敗並回報違反的規則

#### Scenario: 第三系列預組依魔本頁頁序
- **WHEN** 載入 gash-nakama.json 與 zeon.json
- **THEN** 兩者通過驗證,gash-nakama 的 P01 為 M-048、P32 為 S-091,zeon 的 P01 為 M-051、P32 為 S-101,32 頁與 atwiki 魔本頁一致

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

### Requirement: atwiki 抓取的頁面與範圍
`tools/scrape_ja_effects.py` SHALL 從 atwiki 的產品頁(如 LEVEL:1/2 booster 頁)的「収録カード」區塊,依 魔物/戰術/パートナー/イベント 分類取得每張卡的卡號、名稱與個別卡頁連結;逐一抓個別卡頁,解析 `<blockquote>` 內的官方資料區塊。產品頁之外也 SHALL 接受同格式的商品頁(如カードセット、魔本ファイル)。可指定卡號範圍(例如 `M-032:M-053`),只抓範圍內的卡;商品頁收錄範圍外的卡(例如魔本ファイル的後續彈卡片)MUST 略過。輸出至 `data/cards_ja.csv`;已存在於輸出檔的卡號 MUST 跳過(支援分批執行、中斷續抓),每處理完一張卡 MUST 立即寫回檔案。

#### Scenario: 依卡號範圍篩選
- **WHEN** 以範圍 `M-032:M-034` 抓魔本ファイル的商品頁
- **THEN** 只抓 M-032 至 M-034,頁面上的其他卡(如 M-059)不抓

### Requirement: atwiki 資料區塊的分段
`<blockquote>` 內以 `<hr/>` 分隔的 `<div>` 段數 MUST NOT 假設固定為 2 段——部分卡片(如卡面印有變身疊放條件、戰術相容性規則等「框線規則」的魔物卡)會多出中間段落。解析 MUST 一律取第一段當資料頭來源、最後一段當風味文/收錄產品來源,中間任意段數的內容 MUST 併入效果文,唯獨字面完全等於「以上、枠囲み」(純排版提示,表示前一段內容印在卡面框線內,非遊戲內容)的段落 MUST 被過濾、不併入效果文。最後一段依每行內容分類:
- 第一行是對應魔物 / 搭檔的尾行(戰術「X第N の術」、搭檔「魔物＝X」、魔物「パートナー＝X」;拡張シート的卡印在這裡)時,MUST 移回效果文末,依尾行規則解析。
- 第一個收錄產品行(全形空白前為已知產品名,如「拡張1」「LEVEL:2」)之前的行是 flavor_ja(風味文);可能沒有,也可能有多行(以換行分隔)。
- 其餘每行為一筆收錄產品,合併存入 sets_ja。

#### Scenario: 框線規則卡的中間段落正確併入效果文
- **WHEN** 解析一張魔物卡,資料區塊為 4 段 `<div>`(數值列段/「以上、枠囲み」提示段/《能力》效果文+パートナー＝X 段/風味文段)
- **THEN** 「以上、枠囲み」不出現在 effect_ja 中;數值列段的框線規則文字與《能力》段的效果文都完整保留於 effect_ja;related_partner_ja 正確解析自最後一個有效段落

#### Scenario: 尾行印在最後一段
- **WHEN** 解析 Ex-013,最後一段為「ガッシュ・ベル第1の術」「拡張1」
- **THEN** related_mamodo_ja 為「ガッシュ・ベル」,effect_ja 不含尾行,flavor_ja 為空,sets_ja 為「拡張1」

#### Scenario: 沒有風味文
- **WHEN** 解析 Ex-004,最後一段只有「拡張1　R」
- **THEN** flavor_ja 為空,sets_ja 為「拡張1　R」

#### Scenario: 多行風味文
- **WHEN** 解析 Ex-007,最後一段為「(スナック)…」「(TBB)…」「拡張1」「TBB1」「RE」
- **THEN** flavor_ja 為前兩行(以換行分隔),sets_ja 為「拡張1|TBB1|RE」

### Requirement: atwiki 資料頭的 token 分類
第一段(捨棄第一行卡號+名稱後)的資料頭 SHALL 逐 token(全形空白分隔)封閉分類,每個 token MUST 落在下列其中一類,否則視為未知標籤 MUST raise(不得歸類為屬性等開放欄位,不得靜默略過):類型(魔物/戰術/パートナー/イベント,已知略過)/級別(中級→intermediate、上級→superior)/費用(「MP」前綴+數字)/傷害(「ダメージ」前綴+數字;「ダメージ?」表示傷害依效果決定,存為「?」)/power(見「atwiki 資料頭的 power 格式」)/元素屬性(水/火/雷/氷/木/風/重力/土)/效果 icon(バトル/非バトル/ジャマー)/回合欄位(「バトル攻撃」/「バトル防御」/「自分のターン」/「相手のターン」,四者換算為 A/D/AD)。

#### Scenario: 土元素
- **WHEN** 解析資料頭為「術　MP2　＋4000　ダメージ1　土」的戰術卡(如 S-065)
- **THEN** 元素為「土」,不視為未知標籤

#### Scenario: 傷害依效果決定
- **WHEN** 解析資料頭含「ダメージ?」的戰術卡(如 S-061)
- **THEN** 傷害存為「?」,不視為未知標籤

### Requirement: atwiki 資料頭的 power 格式
power 為單一欄位,SHALL 以字串保留格式標記以區分語意:純數字(如「4000」,魔物基礎魔力,無加號)/加號+數字(如「＋4000」,戰術的魔力加值,存為「+4000」)/「特殊」(Special)/數字+倍率後綴(如「2000×」,擲幣倍率型;後綴 MUST 同時接受乘號「×」與英文字母 x/X,wiki 頁面實際使用乘號)。

#### Scenario: 擲幣倍率型 power 保留後綴
- **WHEN** 解析資料頭為「術　MP2　2000×　ダメージ1　木　バトル攻撃」的戰術卡(如 S-040)
- **THEN** power 存為「2000×」;資料頭的「＋4000」則存為「+4000」

### Requirement: atwiki 資料頭的行數與必填欄位
必填欄位 SHALL 依卡片類型而定:イベント/戰術 MUST 有回合欄位(ad);魔物/戰術 MUST 有 power。解析 MUST 先只讀資料頭第 1 行;第 1 行已滿足該卡類型的必填欄位時,MUST NOT 繼續讀第 2 行(第 2 行整行視為效果文);第 1 行未滿足時 MUST 接著讀第 2 行合併判斷;讀完 2 行仍未滿足時 MAY 再讀第 3 行,但只有第 3 行的每個 token 都能分類時才視為資料頭,否則 MUST 退回、該行視為效果文(如 S-093 的資料頭分三行)。讀完仍未滿足必填欄位時,若該卡號登記於已知資料缺漏清單(對照英文資料核對過的官方頁面漏刊,非解析錯誤,如 S-098 的 power「特殊」)MUST 套用登記的欄位覆寫值,否則 MUST raise。

#### Scenario: 資料頭分三行
- **WHEN** 解析資料頭第 1、2 行仍缺必填欄位、第 3 行全為可分類 token 的戰術卡(如 S-093)
- **THEN** 第 3 行併入資料頭,不出現在 effect_ja 中

### Requirement: atwiki 資料頭的標記行
必填欄位滿足後,緊接著只由效果 icon 或回合欄位 token 組成的行(如單獨一行的「非バトル」)MUST 一併視為資料頭。第一段之後、最後一段之前的中間段落,其行 MUST 接在第一段之後一起交給資料頭解析,使中間段開頭的標記行(如 M-039 第二段開頭的「バトル防御」)被正確分類而不併入效果文。

#### Scenario: 單獨一行的效果 icon 或回合標記
- **WHEN** 解析必填欄位已滿足後,下一行只有「非バトル」的戰術卡(如 S-086),或第二段開頭為「バトル防御」的魔物卡(如 M-039)
- **THEN** 該標記分類為效果 icon / 回合欄位,不出現在 effect_ja 中

### Requirement: atwiki 身分尾行的比對範圍
資料頭之後為效果文,SHALL 依卡片類型解析對應魔物 / 對應搭檔的身分尾行。尾行判斷 MUST 以「最後一個句號(。)之後的文字段落」為比對範圍,不要求該段落自成一行——尾行可能與前一句效果文黏在同一行(無 `<br/>` 分隔),此時句號前的敘述文字仍 MUST 保留在 effect_ja。

#### Scenario: 尾段與前一句效果文同一行時正確切分
- **WHEN** 解析一張戰術卡,最後一行為「<敘述句>。<魔物名>第N の術」(無 `<br/>` 分隔)
- **THEN** related_mamodo_ja 正確解析為魔物名,句號前的敘述句完整保留於 effect_ja

### Requirement: atwiki 戰術卡與搭檔卡的對應魔物
- 戰術卡:尾行段落符合「<魔物名>第N の術」格式(N 為數字或「X」,如 S-100「ゼオン第Xの術」)(魔物名可包在 `<a>` 連結中,亦可為純文字,兩者皆 MUST 支援)時,SHALL 取魔物名存入 related_mamodo_ja 並排除於效果文之外;段落若為「コマンド」(指令戰術,不屬於特定魔物,對應英文 `related_mamodo: "Command: All"`),related_mamodo_ja MUST 存為「コマンド」並同樣排除於效果文之外。
- 搭檔卡:尾行段落符合「魔物＝<名字>」格式(純文字,無連結)時,SHALL 取名字存入 related_mamodo_ja 並排除於效果文之外。
- 戰術卡與搭檔卡 MUST 有 related_mamodo_ja(必填);解析不出時,若卡號登記於已知資料缺漏清單 MUST 套用登記的覆寫值,否則 MUST raise。此檢查於尾行解析完成後進行,與資料頭 token 的必填檢查(ad/power)為各自獨立的檢查時機。

#### Scenario: 搭檔卡解析對應魔物
- **WHEN** 解析一張搭檔卡,資料區塊最後一行為「魔物＝ガッシュ・ベル」
- **THEN** related_mamodo_ja 為「ガッシュ・ベル」,該行不出現在 effect_ja 中

#### Scenario: 戰術卡的魔物名無連結時仍可解析
- **WHEN** 解析一張戰術卡,尾段為純文字「<魔物名>第N の術」,魔物名沒有包在 `<a>` 連結中
- **THEN** related_mamodo_ja 正確解析為該魔物名

#### Scenario: 指令戰術不屬於特定魔物
- **WHEN** 解析一張戰術卡,尾段為「コマンド」
- **THEN** related_mamodo_ja 存為「コマンド」,該段落不出現在 effect_ja 中

#### Scenario: 戰術卡/搭檔卡缺少對應魔物身分且未登記已知缺漏時報錯
- **WHEN** 一張戰術卡或搭檔卡讀完效果文仍解析不出 related_mamodo_ja,且卡號未登記於已知資料缺漏清單
- **THEN** raise ValueError,不產出該卡的殘缺資料列

#### Scenario: 已知資料缺漏套用登記的對應魔物覆寫值
- **WHEN** 一張登記於已知資料缺漏清單的搭檔卡(如 P-018,頁面尾行寫成「パートナー＝X」而非「魔物＝X」)解析不出 related_mamodo_ja
- **THEN** 套用清單中登記的覆寫值,不 raise

### Requirement: atwiki 魔物卡與事件卡的身分
- 魔物卡:MUST NOT 自動解析 related_mamodo_ja(不論基本形態或變身形態,一律留空;基本形態亦不自我參照為自己的 name_ja)——此身分之後如需使用,由人工從效果內文判斷。魔物卡 SHALL 解析對應搭檔的身分尾行:段落符合「パートナー＝<名字>」格式(純文字,無連結),取名字存入 related_partner_ja 並排除於效果文之外——與搭檔卡的「魔物＝X」尾行鏡像對稱(搭檔宣告對應魔物,魔物宣告對應搭檔)。魔物卡 MUST 有 related_partner_ja(必填);解析不出時,若卡號登記於已知資料缺漏清單 MUST 套用登記的覆寫值,否則 MUST raise,檢查時機與 related_mamodo_ja 相同(尾行解析完成後)。
- 事件卡:MUST NOT 有 related_mamodo_ja 或 related_partner_ja(對照英文資料確認事件卡無此概念)。

#### Scenario: 魔物卡一律不解析對應魔物
- **WHEN** 解析任一張魔物卡(不論基本或變身形態)
- **THEN** related_mamodo_ja 恆為空字串,不嘗試從卡名或效果文推論

#### Scenario: 魔物卡解析對應搭檔
- **WHEN** 解析一張魔物卡,資料區塊最後一行為「パートナー＝高嶺清麿」
- **THEN** related_partner_ja 為「高嶺清麿」,該行不出現在 effect_ja 中

#### Scenario: 魔物卡缺少對應搭檔且未登記已知缺漏時報錯
- **WHEN** 一張魔物卡讀完效果文仍解析不出 related_partner_ja,且卡號未登記於已知資料缺漏清單
- **THEN** raise ValueError,不產出該卡的殘缺資料列

### Requirement: 日文與英文卡片文字
日文與英文的卡片文字 SHALL 各存於獨立檔 `data/cards.ja.json`、`data/cards.en.json`,與 `data/cards.zh-TW.json` 相同結構(以卡號為 key,含 `name`、`name_ja`、`attr`、`effect`),涵蓋 `cards.json` 的全部卡號。修改這兩個檔 MUST NOT 影響 `cards.json` 的數值與邏輯。

- `cards.ja.json` SHALL 由工具自 `data/cards_ja.csv` 產生,不手動編輯:`name` 與 `name_ja` 為 `name_ja`;`effect` 為 `effect_ja`;`attr` 對戰術卡為 `attr_ja`(元素),對魔物卡與搭檔卡為 `effect_ja` 中第一個《》括起的效果名,沒有時為 null。
- `cards.en.json` 的 `name` 與 `attr` SHALL 取自 `card-data` 的 TTS 卡表(`Zatch Bell CCG List for TTS.xlsx`)的英文卡名與 Attribute / Effect Name;卡表的屬性欄為「-」而該戰術卡在日文資料有元素時,`attr` SHALL 為卡表中同一元素其他戰術的英文,卡表沒有該元素的英文時為 null;`cards.ja.json` 的 `attr` 為 null(例如沒有效果名的白板魔物)時,英文 `attr` MUST 為 null,不留卡表的英文效果名。`effect` SHALL 依 `effect_ja` 翻譯,MUST NOT 以卡表或卡圖上的英文效果文為依據(兩者與日文效果文有出入)。`name_ja` MUST 與 `data/cards_ja.csv` 一致。

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

#### Scenario: 日文沒有效果名的卡
- **WHEN** 產生 Ex-001(白板魔物,卡表的效果名為「Strong Resolve」)的英文文字
- **THEN** `attr` 為 null

### Requirement: 簡體中文卡片文字
簡體中文的卡片文字 SHALL 存於 `data/cards.zh-CN.json`,與 `data/cards.zh-TW.json` 相同結構。簡體中文的介面字典 `frontend/i18n/zh-CN.json` 與規則頁 `frontend/i18n/rules.zh-CN.json` 亦同。三個檔 SHALL 由工具自對應的繁體中文檔轉換產生,MUST NOT 手動編輯;繁體中文檔修改後 SHALL 重新產生,兩者 MUST 保持同步。

轉換 SHALL 把繁體字形轉為簡體字形,並把台灣用語轉為大陸用語;遊戲術語 SHALL 依工具的術語表保留或替換(例如「宣告」保留,不轉為「声明」)。角色名、卡名、戰術名 SHALL 只轉字形,沿用繁體中文的譯名。`name_ja` MUST NOT 轉換,仍 MUST 與 `data/cards_ja.csv` 一致。修改這些檔 MUST NOT 影響 `cards.json` 的數值與邏輯。

#### Scenario: 譯名只轉字形
- **WHEN** 產生 M-001 的簡體中文文字
- **THEN** `name` 為「贾修・贝尔」,`name_ja` 仍為「ガッシュ・ベル」

#### Scenario: 遊戲術語保留
- **WHEN** 繁體中文的效果文含「【宣告使用→】」
- **THEN** 簡體中文為「【宣告使用→】」,不是「声明使用」

#### Scenario: 繁中修改後未重新產生
- **WHEN** 修改 `cards.zh-TW.json` 某卡的卡名但沒有重新執行工具
- **THEN** 檢查同步的測試失敗

### Requirement: 第三彈卡片資料
卡片資料 SHALL 涵蓋第三彈:LEVEL:3「金色の超呪文」、カードセット「ガッシュ・ベルと仲間達」「ゼオンと最凶魔物達」與「魔本ファイル」收錄的 M-032–M-053、P-020–P-035、S-059–S-106、E-028–E-043,共 102 張。每張卡 SHALL 有日文權威資料(`cards_ja.csv`)、`cards.json` 的資料,以及四種語言的卡片文字(繁中卡名與效果文、英文效果文為初版翻譯,尚待校對)。

#### Scenario: 第三彈卡號齊全
- **WHEN** 載入卡片資料
- **THEN** 含 M-032–M-053、P-020–P-035、S-059–S-106、E-028–E-043 的每一張,四種語言的卡片文字都有對應項目

### Requirement: 尚未開放的卡片
`data/pending_cards.json` SHALL 列出資料已收錄、但效果尚未實作的卡號。尚未開放的卡 MUST NOT 通過構築規則驗證(原因碼 `deck.card_pending`),因此不能用於建房、加入、NPC 牌組或預組。卡片效果實作完成時,SHALL 自清單移除該卡號以開放使用。

#### Scenario: 含尚未開放卡的牌組被拒絕
- **WHEN** 建房時的自訂牌組含有清單中的卡
- **THEN** 回應 422 與原因碼 `deck.card_pending`,不建立房間

#### Scenario: 實作後開放
- **WHEN** 某卡號自清單移除
- **THEN** 含該卡的牌組可通過構築規則驗證

### Requirement: 戰術屬性譯名一致
同一個日文元素(戰術卡的 `attr_name`)在 `cards.zh-TW.json` 與 `cards.en.json` 中 SHALL 各只對應一種譯名;有元素的戰術卡,這兩個檔的 `attr` MUST NOT 為空;日文資料沒有元素的戰術卡(含指令戰術),`attr` MUST 為空,不另訂屬性。簡體中文由繁體中文轉換,隨之一致。

#### Scenario: 雷屬性的繁中譯名
- **WHEN** 檢查所有日文元素為「雷」的戰術卡(含 S-001、S-029)的繁中 `attr`
- **THEN** 全部為「雷」

#### Scenario: 沒有元素的戰術沒有屬性
- **WHEN** 檢查 S-058(傑昂的「ザケル」,日文資料沒有元素)與指令戰術 S-026 的繁中 `attr`
- **THEN** 兩者皆為空

### Requirement: 已知的效果文錯誤
抓取工具 SHALL 登記 atwiki 上已確認的效果文錯誤(錯誤原文與修正後的文字),解析後以修正後的文字取代;頁面上找不到登記的錯誤原文時(來源已修正或改寫)MUST 報錯,由人工確認後更新登記。目前登記:S-069 的「防御に使ったとき」與「攻撃に使ったとき」兩段標題寫反(依卡圖與 TTS 卡表的英文確認);Ex-002 的「(0より小さくはならない)。」後多一個「,」(頁面打字錯誤)。

#### Scenario: S-069 的效果文修正
- **WHEN** 抓取並解析 S-069
- **THEN** `effect_ja` 為「●この術を攻撃に使ったとき相手は、この攻撃を防御できない。コインを投げてオモテなら、相手の魔本にダメージ。●この術を防御に使ったとき魔力勝負の勝敗にかかわらず、コインを投げてオモテなら、相手の攻撃を無効にする。」

#### Scenario: 來源已修正時提醒
- **WHEN** 頁面上的 S-069 效果文已不含登記的錯誤原文
- **THEN** 工具報錯,不產出該卡

#### Scenario: Ex-002 的多餘逗號
- **WHEN** 抓取並解析 Ex-002
- **THEN** `effect_ja` 以「(0より小さくはならない)。」結尾,不含「,」

### Requirement: 收錄產品資料
`cards.json` 的 `sets`(前端依產品篩選所讀取的收錄產品清單)SHALL 由 `cards_ja.csv` 的 `sets_ja` 產生,轉換 MUST NOT 讀取 xlsx。每筆收錄產品取全形空白前的產品名(去掉稀有度與販售形式),依產品對照表轉為產品代號,去除重複並依對照表順序排列。對照表為:LEVEL:1 → `level-1`、LEVEL:2 → `level-2`、別売魔本 → `mahon-file`、LEVEL:3 → `level-3`、ガッシュ・ベルと仲間たち → `cardset-gash-nakama`、ゼオンと最凶魔物達 → `cardset-zeon`、(第 3 賽季產品,見「第 3 賽季產品的代號」)、LEVEL:S → `level-s`、TBB1 → `tbb1`、TBB2 → `tbb2`、RE → `re`、FILE:1 → `file-1`。對照表沒有的產品名 MUST 報錯中止轉換,不寫出 `cards.json`。

#### Scenario: 收錄產品取自日文來源
- **WHEN** 轉換 `sets_ja` 為「LEVEL:2　Rパック・自販機|LEVEL:2　Nスターター|TBB2　N|RE　R」的卡
- **THEN** 該卡 `sets` 為 `["level-2", "tbb2", "re"]`

#### Scenario: 第 3 賽季的新產品
- **WHEN** 轉換 `sets_ja` 為「拡張2　R|TBB2　N」的卡(Ex-025)
- **THEN** 該卡 `sets` 為 `["ex-sheet-2", "tbb2"]`
- **WHEN** 轉換 `sets_ja` 為「SPBOX|TBB1|RE」的卡
- **THEN** 該卡 `sets` 為 `["special-box", "tbb1", "re"]`

#### Scenario: 每張卡都有收錄產品
- **WHEN** 轉換執行完成
- **THEN** 每張卡的 `sets` 至少有一個產品代號

#### Scenario: 未登記的產品名中止轉換
- **WHEN** 某卡的 `sets_ja` 含產品對照表沒有的產品名
- **THEN** 轉換報錯並指出卡號與產品名,不寫出 `cards.json`

### Requirement: 已知的收錄產品與風味文錯誤
抓取工具 SHALL 登記 atwiki 卡頁上已確認的風味文 / 收錄產品錯誤並在解析時修正;頁面上找不到登記的錯誤原文時 MUST 報錯,由人工確認後更新登記。目前登記:

- E-024 的風味文有兩行(LEVEL:S 再錄版與原版),第二行「これは私の趣味ではない...断じてだ!!」MUST 併入 `flavor_ja`(兩行以換行分隔),不當作收錄產品。
- P-018 的收錄產品「TBB　N」MUST 改為「TBB2　N」(該頁標籤為「THE BEST BOOSTER 2」)。
- Ex-005 的風味文「私もやさしい王様を目指してあげるわ。」印在第一段「パートナー＝大海恵」之後,MUST 移回 `flavor_ja`,不併入效果文。

#### Scenario: E-024 的第二行風味文不是產品
- **WHEN** 抓取並解析 E-024
- **THEN** `sets_ja` 不含「これは私の趣味ではない...断じてだ!!」,`flavor_ja` 含兩行風味文

#### Scenario: P-018 的 TBB 為 TBB2
- **WHEN** 抓取並解析 P-018
- **THEN** `sets_ja` 含「TBB2　N」,不含「TBB　N」

#### Scenario: 來源已修正時提醒
- **WHEN** 頁面上的 P-018 收錄產品已不含「TBB　N」
- **THEN** 工具報錯,不產出該卡

#### Scenario: Ex-005 的風味文移回
- **WHEN** 抓取並解析 Ex-005
- **THEN** `flavor_ja` 為「私もやさしい王様を目指してあげるわ。」,`effect_ja` 為空,`related_partner_ja` 為「大海恵」

#### Scenario: Ex-005 來源已修正時提醒
- **WHEN** 頁面上 Ex-005 第一段的最後一行已不是登記的風味文
- **THEN** 工具報錯,不產出該卡

### Requirement: 賽季定義
`data/seasons.json` SHALL 定義各賽季每種卡號前綴的最大編號,以及特別歸屬某賽季的卡號。目前的定義:
- 第 1 賽季:M-015、S-028、P-009、E-015、PR-002
- 第 2 賽季:M-034、S-058、P-019、E-027、PR-007、Ex-024
- 第 3 賽季:M-069、S-112、P-043、E-049、PR-011、Ex-048
- 特別歸屬:Ex-000 屬第 4 賽季

一張卡的賽季 SHALL 為特別歸屬的賽季;沒有特別歸屬時,為該前綴最大編號不小於其編號的最早賽季。沒有任何賽季包含的卡沒有賽季。

#### Scenario: 卡片的賽季
- **WHEN** 查詢 M-015、M-016、S-106、M-053 的賽季
- **THEN** 依序為第 1、2、3、3 賽季

#### Scenario: 前綴在早期賽季沒有定義
- **WHEN** 查詢 Ex-010 的賽季
- **THEN** 為第 2 賽季(第 1 賽季沒有 Ex 前綴)

#### Scenario: 特別歸屬
- **WHEN** 查詢 Ex-000 的賽季
- **THEN** 為第 4 賽季,雖然它的編號在第 2 賽季的 Ex 範圍內

### Requirement: 魔書的賽季
一副魔書的賽季 SHALL 為其中各卡賽季的最大值,表示該魔書從這個賽季起可以使用。魔書在某賽季可用,當且僅當每張卡都有賽季且不大於該賽季。

#### Scenario: 混合賽季的魔書
- **WHEN** 魔書含第 1 賽季與第 2 賽季的卡,沒有更晚的卡
- **THEN** 魔書的賽季為 2;在第 2、3 賽季可用,在第 1 賽季不可用

#### Scenario: 預組的賽季
- **WHEN** 計算預組 level1、level2、gash-nakama、zeon 的賽季
- **THEN** 依序為 1、2、3、3

### Requirement: 構築規則的賽季限制
構築規則驗證 SHALL 可指定賽季;魔書含不屬於該賽季可用範圍的卡時 MUST 拒絕,原因碼 `deck.season`。未指定賽季時不做此檢查。

#### Scenario: 超出賽季的魔書被拒絕
- **WHEN** 以第 1 賽季驗證含 M-030 的合法魔書
- **THEN** 驗證失敗,原因碼 `deck.season`

#### Scenario: 符合賽季的魔書通過
- **WHEN** 以第 3 賽季驗證 level2 預組
- **THEN** 驗證通過

### Requirement: 第 3 賽季卡片資料
卡片資料 SHALL 涵蓋第 3 賽季範圍內、第三彈以後的卡,共 95 張:
- M-054–M-069
- S-107–S-112
- P-036–P-043
- E-044–E-049
- PR-001–PR-011
- Ex-001–Ex-048

每張卡 SHALL 有日文權威資料(`cards_ja.csv`)、`cards.json` 的資料,以及四種語言的卡片文字。繁中卡名、繁中效果文與英文效果文是初版翻譯,尚待校對。

擴張卡的卡號 SHALL 依 atwiki 寫作 `Ex-`(例如 `Ex-001`)。這 95 張 SHALL 全部列入尚未開放的卡,直到各自的效果實作完成。

#### Scenario: 第 3 賽季卡號齊全
- **WHEN** 載入卡片資料
- **THEN** 含 M-054–M-069、S-107–S-112、P-036–P-043、E-044–E-049、PR-001–PR-011、Ex-001–Ex-048 的每一張
- **THEN** 四種語言的卡片文字都有對應項目
- **THEN** `cards.json` 共 332 張

#### Scenario: 新卡尚未開放
- **WHEN** 建房時的自訂牌組含 Ex-001
- **THEN** 回應 422 與原因碼 `deck.card_pending`

#### Scenario: 擴張卡號的寫法
- **WHEN** 查詢卡號 `Ex-025`
- **THEN** 找到 Ex-025(ガッシュ・ベル,魔物)
- **THEN** 卡片資料中沒有 `EX-` 開頭的卡號

### Requirement: atwiki 擴張卡與特典卡的抓取
抓取工具 SHALL 接受拡張シート商品頁(Ex 卡)與特典卡頁(PR 卡)。

拡張シート商品頁:
- 「収録カード」的卡號 SHALL 接受 `Ex-` 開頭。
- 頁面中依シート分組重複列出的卡 MUST 略過,每張卡只抓一次。
- 類型取自 魔物 / パートナー / 術 / イベント 分類。

特典卡頁沒有類型分類,PR 卡的類型 SHALL 由個別卡頁資料頭的類型 token(魔物 / 術 / パートナー / イベント)決定。

#### Scenario: 拡張シートの卡只抓一次
- **WHEN** 解析拡張シート LEVEL:2 的商品頁
- **THEN** 取得 Ex-025 至 Ex-048 各一次,類型依分類決定

#### Scenario: PR 卡類型取自卡頁
- **WHEN** 解析特典卡頁並抓取 PR 卡
- **THEN** 每張 PR 卡的類型取自卡頁資料頭,不因商品頁沒有分類而中止

### Requirement: 外部來源的擴張卡號寫法
TTS 卡表與卡圖資料夾把擴張卡寫作大寫 `EX-`(如 `EX-001`)。工具讀取這兩個來源時 SHALL 把 `EX-` 對應到卡號 `Ex-`:
- 卡表的英文卡名寫入 `Ex-` 卡。
- 卡圖下載資料夾中的 `EX-001.webp`,存成 `frontend/assets/cards/Ex-001.webp`。

`Ex-` 以外的卡號 MUST NOT 受影響。

#### Scenario: 卡圖檔名對應
- **WHEN** 卡圖資料夾有 `EX-001.webp`,本機沒有 `Ex-001.webp`
- **THEN** 腳本下載該檔並存成 `frontend/assets/cards/Ex-001.webp`

#### Scenario: 卡表英文卡名對應
- **WHEN** 產生英文卡片文字
- **THEN** Ex-001 的 `name` 取自卡表 `EX-001` 列的英文卡名

### Requirement: 第 3 賽季產品的代號
「收錄產品資料」的對照表 SHALL 在 `cardset-zeon` 之後、LEVEL:S 之前依序包含:LTD1 → `limited-1`、SPBOX → `special-box`、魔本ファイル第2弾 → `mahon-file-2`、拡張1 → `ex-sheet-1`、拡張2 → `ex-sheet-2`、プロモ → `promo`。

atwiki 把魔本ファイル第1弾(M-032–M-034)與第2弾(M-059–M-061)的收錄產品都寫作「別売魔本」。轉換 SHALL 把 M-059–M-061 的「別売魔本」轉為 `mahon-file-2`,其他卡的「別売魔本」為 `mahon-file`。

#### Scenario: 魔本ファイル分兩個產品
- **WHEN** 轉換 `sets_ja` 皆為「別売魔本」的 M-032 與 M-060
- **THEN** M-032 的 `sets` 為 `["mahon-file"]`,M-060 的 `sets` 為 `["mahon-file-2"]`
