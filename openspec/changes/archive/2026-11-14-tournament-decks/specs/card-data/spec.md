## MODIFIED Requirements


### Requirement: 預組魔書資料
`data/decks/` 的每個預組 SHALL 以 32 個頁位依序對應卡號,並記錄來源:`level1.json` 由 `ref/raw/deck/level1.txt` 轉換;`level2.json`、`gash-nakama.json`、`zeon.json` 依 atwiki 構築済み魔本頁(「黒き魔界よりの使者」pages/2054、「ガッシュ・ベルと仲間達」pages/2056、「ゼオンと最凶魔物達」pages/2057)的頁序;`ref-zeon-baltro-s2.json`、`ref-brago-s2.json` 為使用者提供的第 2 賽季參考牌組(牌組代碼 gash1,2026-11-01),依提供的頁序;`ref-makai-{1,2}-{junior,middle,senior}.json` 為魔界王決定戦第 1、2 回各組(ジュニア、ミドル、シニア)優勝的魔本,依 atwiki 各優勝魔本頁(魔界王決定戦 pages/1878 所列)「魔本リスト」的頁序。載入時 MUST 驗證構築合法性(32 頁全滿、第 1 頁魔物、最後一頁戰術、中級 12 頁後、上級 22 頁後、同號 ≤4、魔物 ≤8、不含尚未開放的卡)且每個卡號存在於 cards.json。每個預組 SHALL 有 `name_key`,其名稱在四種語言的介面字典中都有翻譯。

#### Scenario: 預組魔書通過驗證
- **WHEN** 引擎載入 level1.json
- **THEN** 驗證通過:P01=M-001、P32=S-005(上級,位於 22 頁後)、S-001×3 未超限

#### Scenario: 非法魔書被拒
- **WHEN** 載入一份第 1 頁不是魔物卡的魔書資料
- **THEN** 載入失敗並回報違反的規則

#### Scenario: 第三系列預組依魔本頁頁序
- **WHEN** 載入 gash-nakama.json 與 zeon.json
- **THEN** 兩者通過驗證,gash-nakama 的 P01 為 M-048、P32 為 S-091,zeon 的 P01 為 M-051、P32 為 S-101,32 頁與 atwiki 魔本頁一致

#### Scenario: 參考牌組
- **WHEN** 載入 ref-zeon-baltro-s2.json 與 ref-brago-s2.json
- **THEN** 兩者通過驗證,ref-zeon-baltro-s2 的 P01 為 M-029、P32 為 S-049,ref-brago-s2 的 P01 為 M-011、P32 為 S-036,賽季皆為第 2 賽季

#### Scenario: 魔界王決定戦的優勝魔本
- **WHEN** 載入 ref-makai-1-junior、ref-makai-1-middle、ref-makai-1-senior、ref-makai-2-junior、ref-makai-2-middle、ref-makai-2-senior
- **THEN** 六副都通過驗證,32 頁與 atwiki 魔本リスト一致(例:ref-makai-1-junior 的 P01 為 M-030、P32 為 S-021;ref-makai-2-junior 的 P01 為 M-053、P32 為 S-036);第 1 回(2003-11)三副為第 2 賽季,第 2 回(2004-03)三副為第 4 賽季
