## ADDED Requirements

### Requirement: 收錄產品資料
`cards.json` 的 `sets`(前端依產品篩選所讀取的收錄產品清單)SHALL 由 `cards_ja.csv` 的 `sets_ja` 產生,轉換 MUST NOT 讀取 xlsx。每筆收錄產品取全形空白前的產品名(去掉稀有度與販售形式),依產品對照表轉為產品代號,去除重複並依對照表順序排列。對照表為:LEVEL:1 → `level-1`、LEVEL:2 → `level-2`、別売魔本 → `mahon-file`、LEVEL:3 → `level-3`、ガッシュ・ベルと仲間たち → `cardset-gash-nakama`、ゼオンと最凶魔物達 → `cardset-zeon`、LEVEL:S → `level-s`、TBB1 → `tbb1`、TBB2 → `tbb2`、RE → `re`、FILE:1 → `file-1`。對照表沒有的產品名 MUST 報錯中止轉換,不寫出 `cards.json`。

#### Scenario: 收錄產品取自日文來源
- **WHEN** 轉換 `sets_ja` 為「LEVEL:2　Rパック・自販機|LEVEL:2　Nスターター|TBB2　N|RE　R」的卡
- **THEN** 該卡 `sets` 為 `["level-2", "tbb2", "re"]`

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

#### Scenario: E-024 的第二行風味文不是產品
- **WHEN** 抓取並解析 E-024
- **THEN** `sets_ja` 不含「これは私の趣味ではない...断じてだ!!」,`flavor_ja` 含兩行風味文

#### Scenario: P-018 的 TBB 為 TBB2
- **WHEN** 抓取並解析 P-018
- **THEN** `sets_ja` 含「TBB2　N」,不含「TBB　N」

#### Scenario: 來源已修正時提醒
- **WHEN** 頁面上的 P-018 收錄產品已不含「TBB　N」
- **THEN** 工具報錯,不產出該卡

## MODIFIED Requirements

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
