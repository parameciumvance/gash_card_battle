## ADDED Requirements

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

## MODIFIED Requirements

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
