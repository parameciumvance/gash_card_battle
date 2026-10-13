## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: 卡片資料轉換
`data/cards.json` SHALL 由 `data/cards_ja.csv`(日文權威來源的抓取結果)轉換產生,而非由 xlsx 抽取。轉換 MUST 涵蓋該檔全部列(含未存在於舊 xlsx 來源的卡號),欄位對應規則:

- `related_mamodo`(魔物家族識別鍵,戰術卡/搭檔卡/事件卡與其對應魔物卡必須相等以供引擎比對陣營歸屬)戰術卡/搭檔卡/事件卡 MUST 直接對應 `related_mamodo_ja`(空字串視為 null);魔物卡 MUST 以「`name_ja` 去除括號後綴(如「（変身後）」)」推導,使變身/形態卡(如 M-007「ゴフレ（変身後）」)的 `related_mamodo` 與其基礎家族名(「ゴフレ」)一致,並與同家族戰術卡/搭檔卡的 `related_mamodo_ja` 相等。
- `name_ja`/`effect_ja`(欄位命名反映實際內容為日文,對應 `CardDef.name_ja`/`effect_ja`)MUST 直接對應 `cards_ja.csv` 的 `name_ja`/`effect_ja`。
- `power`(單一字串欄位)MUST 解析回結構化格式:純數字(無加號)→ `{base: N}`;加號+數字 → `{bonus: N}`;「特殊」→ `{special: true}`;數字+倍率後綴(×)→ `{special: true, per_heads: N}`;空字串(搭檔/事件卡通常無 power)→ `{}`。
- `ad`/`class`/`cost`/`damage` MUST 直接對應同名或同語意欄位;`damage` 為「?」(傷害依效果決定)時 `damage` MUST 為 null 並另設 `damage_variable: true`。
- `attr_name` MUST 僅在卡片類型為戰術時填入該卡的 `attr_ja`(元素);魔物卡與搭檔卡的 `attr_name` MUST 為 null——此欄位在引擎中僅用於戰術卡的屬性相容性判定,不承擔任何顯示職責(顯示由 `data/cards.zh-TW.json` 的 `attr` 欄位負責)。
- `effect_icon` MUST 對應 `cards_ja.csv` 的 `effect_icon_ja`,轉為英文枚舉值:「バトル」→ `"battle"`、「非バトル」→ `"nonbattle"`、「ジャマー」→ `"jammer"`、空字串 → `null`。
- `image_url` MUST 直接從 `openspec/specs/card-data/Zatch Bell CCG List for TTS.xlsx` 讀取(A 欄儲存格的 HYPERLINK 公式或儲存格超連結),以卡號(去除 e/j 版本尾碼)比對 `cards_ja.csv` 的卡號做對應;xlsx 中沒有對應卡號的,`image_url` MUST 為 null,不得因此中止轉換或報錯(注意:S-042 過去因 Sets 標籤格式不同於舊抽取腳本的過濾條件而被誤判為「xlsx 沒有這張卡」,實際上 xlsx 內有對應列,改直接讀取後已能正確取得其 `image_url`)。
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

#### Scenario: 傷害依效果決定的戰術卡
- **WHEN** 轉換 `damage` 為「?」的 S-061
- **THEN** 該卡 `damage` 為 null,`damage_variable` 為 true

#### Scenario: 新卡的收錄產品取自 xlsx
- **WHEN** 轉換一張轉換前 `cards.json` 沒有的卡(如 M-048)
- **THEN** 該卡 `sets` 為 xlsx 對應列 Sets 欄的各產品

### Requirement: 日文權威資料抓取(atwiki)
`tools/scrape_ja_effects.py` SHALL 從 atwiki 的產品頁(如 LEVEL:1/2 booster 頁)的「収録カード」區塊,依 魔物/戰術/パートナー/イベント 分類取得每張卡的卡號、名稱與個別卡頁連結;逐一抓個別卡頁,解析 `<blockquote>` 內的官方資料區塊。`<blockquote>` 內以 `<hr/>` 分隔的 `<div>` 段數 MUST NOT 假設固定為 2 段——部分卡片(如卡面印有變身疊放條件、戰術相容性規則等「框線規則」的魔物卡)會多出中間段落。解析 MUST 一律取第一段當資料頭來源、最後一段當風味文/收錄產品來源,中間任意段數的內容 MUST 併入效果文,唯獨字面完全等於「以上、枠囲み」(純排版提示,表示前一段內容印在卡面框線內,非遊戲內容)的段落 MUST 被過濾、不併入效果文:

- 第一段(捨棄第一行卡號+名稱後):資料頭 1~2 行,逐 token(全形空白分隔)封閉分類,MUST 落在下列其中一類,否則視為未知標籤 MUST raise(不得歸類為屬性等開放欄位,不得靜默略過):類型(魔物/戰術/パートナー/イベント,已知略過)/級別(中級→intermediate、上級→superior)/費用(「MP」前綴+數字)/傷害(「ダメージ」前綴+數字;「ダメージ?」表示傷害依效果決定,存為「?」)/power(見下)/元素屬性(水/火/雷/氷/木/風/重力/土)/效果 icon(バトル/非バトル/ジャマー)/回合欄位(「バトル攻撃」/「バトル防御」/「自分のターン」/「相手のターン」,四者換算為 A/D/AD)。
- power 為單一欄位,以字串保留格式標記以區分語意:純數字(如「4000」,魔物基礎魔力,無加號)/加號+數字(如「＋4000」,戰術的魔力加值,存為「+4000」)/「特殊」(Special)/數字+倍率後綴(如「2000×」,擲幣倍率型;後綴 MUST 同時接受乘號「×」與英文字母 x/X,wiki 頁面實際使用乘號)。
- 必填欄位依卡片類型而定:イベント/戰術 MUST 有回合欄位(ad);魔物/戰術 MUST 有 power。解析 MUST 先只讀資料頭第 1 行;第 1 行已滿足該卡類型的必填欄位時,MUST NOT 繼續讀第 2 行(第 2 行整行視為效果文);第 1 行未滿足時 MUST 接著讀第 2 行合併判斷;讀完 2 行仍未滿足時 MAY 再讀第 3 行,但只有第 3 行的每個 token 都能分類時才視為資料頭,否則 MUST 退回、該行視為效果文(如 S-093 的資料頭分三行)。讀完仍未滿足必填欄位時,若該卡號登記於已知資料缺漏清單(對照英文資料核對過的官方頁面漏刊,非解析錯誤,如 S-098 的 power「特殊」)MUST 套用登記的欄位覆寫值,否則 MUST raise。必填欄位滿足後,緊接著只由效果 icon 或回合欄位 token 組成的行(如單獨一行的「非バトル」)MUST 一併視為資料頭。第一段之後、最後一段之前的中間段落,其行 MUST 接在第一段之後一起交給資料頭解析,使中間段開頭的標記行(如 M-039 第二段開頭的「バトル防御」)被正確分類而不併入效果文。
- 資料頭之後為效果文,依卡片類型解析對應魔物身分尾行。尾行判斷 MUST 以「最後一個句號(。)之後的文字段落」為比對範圍,不要求該段落自成一行——尾行可能與前一句效果文黏在同一行(無 `<br/>` 分隔),此時句號前的敘述文字仍 MUST 保留在 effect_ja。依卡片類型:
  - 戰術卡:段落符合「<魔物名>第N の術」格式(N 為數字或「X」,如 S-100「ゼオン第Xの術」)(魔物名可包在 `<a>` 連結中,亦可為純文字,兩者皆 MUST 支援),取魔物名存入 related_mamodo_ja 並排除於效果文之外;段落若為「コマンド」(指令戰術,不屬於特定魔物,對應英文 `related_mamodo: "Command: All"`),related_mamodo_ja MUST 存為「コマンド」並同樣排除於效果文之外。
  - 搭檔卡:段落符合「魔物＝<名字>」格式(純文字,無連結),取名字存入 related_mamodo_ja 並排除於效果文之外。
  - 魔物卡:MUST NOT 自動解析 related_mamodo_ja(不論基本形態或變身形態,一律留空;基本形態亦不自我參照為自己的 name_ja)——此身分之後如需使用,由人工從效果內文判斷。魔物卡另有對應搭檔的身分尾行(見下)。
  - 事件卡:MUST NOT 有 related_mamodo_ja 或 related_partner_ja(對照英文資料確認事件卡無此概念)。
  - 戰術卡與搭檔卡 MUST 有 related_mamodo_ja(必填);解析不出時,若卡號登記於已知資料缺漏清單 MUST 套用登記的覆寫值,否則 MUST raise。此檢查於尾行解析完成後進行,與資料頭 token 的必填檢查(ad/power)為各自獨立的檢查時機。
- 魔物卡另需解析對應搭檔的身分尾行:段落符合「パートナー＝<名字>」格式(純文字,無連結),取名字存入 related_partner_ja 並排除於效果文之外——與搭檔卡的「魔物＝X」尾行鏡像對稱(搭檔宣告對應魔物,魔物宣告對應搭檔)。魔物卡 MUST 有 related_partner_ja(必填);解析不出時,若卡號登記於已知資料缺漏清單 MUST 套用登記的覆寫值,否則 MUST raise,檢查時機與 related_mamodo_ja 相同(尾行解析完成後)。
- 最後一段:第一行為 flavor_ja(風味文),其餘每行為一筆收錄產品,合併存入 sets_ja。

產品頁之外也 SHALL 接受同格式的商品頁(如カードセット、魔本ファイル)。可指定卡號範圍(例如 `M-032:M-053`),只抓範圍內的卡;商品頁收錄範圍外的卡(例如魔本ファイル的後續彈卡片)MUST 略過。輸出至 `data/cards_ja.csv`;已存在於輸出檔的卡號 MUST 跳過(支援分批執行、中斷續抓),每處理完一張卡 MUST 立即寫回檔案。

#### Scenario: 搭檔卡解析對應魔物
- **WHEN** 解析一張搭檔卡,資料區塊最後一行為「魔物＝ガッシュ・ベル」
- **THEN** related_mamodo_ja 為「ガッシュ・ベル」,該行不出現在 effect_ja 中

#### Scenario: 魔物卡一律不解析對應魔物
- **WHEN** 解析任一張魔物卡(不論基本或變身形態)
- **THEN** related_mamodo_ja 恆為空字串,不嘗試從卡名或效果文推論

#### Scenario: 戰術卡的魔物名無連結時仍可解析
- **WHEN** 解析一張戰術卡,尾段為純文字「<魔物名>第N の術」,魔物名沒有包在 `<a>` 連結中
- **THEN** related_mamodo_ja 正確解析為該魔物名

#### Scenario: 指令戰術不屬於特定魔物
- **WHEN** 解析一張戰術卡,尾段為「コマンド」
- **THEN** related_mamodo_ja 存為「コマンド」,該段落不出現在 effect_ja 中

#### Scenario: 尾段與前一句效果文同一行時正確切分
- **WHEN** 解析一張戰術卡,最後一行為「<敘述句>。<魔物名>第N の術」(無 `<br/>` 分隔)
- **THEN** related_mamodo_ja 正確解析為魔物名,句號前的敘述句完整保留於 effect_ja

#### Scenario: 戰術卡/搭檔卡缺少對應魔物身分且未登記已知缺漏時報錯
- **WHEN** 一張戰術卡或搭檔卡讀完效果文仍解析不出 related_mamodo_ja,且卡號未登記於已知資料缺漏清單
- **THEN** raise ValueError,不產出該卡的殘缺資料列

#### Scenario: 已知資料缺漏套用登記的對應魔物覆寫值
- **WHEN** 一張登記於已知資料缺漏清單的搭檔卡(如 P-018,頁面尾行寫成「パートナー＝X」而非「魔物＝X」)解析不出 related_mamodo_ja
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

#### Scenario: 土元素
- **WHEN** 解析資料頭為「術　MP2　＋4000　ダメージ1　土」的戰術卡(如 S-065)
- **THEN** 元素為「土」,不視為未知標籤

#### Scenario: 傷害依效果決定
- **WHEN** 解析資料頭含「ダメージ?」的戰術卡(如 S-061)
- **THEN** 傷害存為「?」,不視為未知標籤

#### Scenario: 依卡號範圍篩選
- **WHEN** 以範圍 `M-032:M-034` 抓魔本ファイル的商品頁
- **THEN** 只抓 M-032 至 M-034,頁面上的其他卡(如 M-059)不抓

#### Scenario: 資料頭分三行
- **WHEN** 解析資料頭第 1、2 行仍缺必填欄位、第 3 行全為可分類 token 的戰術卡(如 S-093)
- **THEN** 第 3 行併入資料頭,不出現在 effect_ja 中

#### Scenario: 單獨一行的效果 icon 或回合標記
- **WHEN** 解析必填欄位已滿足後,下一行只有「非バトル」的戰術卡(如 S-086),或第二段開頭為「バトル防御」的魔物卡(如 M-039)
- **THEN** 該標記分類為效果 icon / 回合欄位,不出現在 effect_ja 中
