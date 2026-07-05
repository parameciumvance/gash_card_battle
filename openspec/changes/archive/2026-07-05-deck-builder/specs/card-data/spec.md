# card-data — 差分:抽取收錄產品

構築器需依產品篩選卡池;抽取須保留 xlsx 的 Sets 欄。

## MODIFIED Requirements

### Requirement: 卡片資料抽取
抽取腳本 SHALL 讀取 xlsx「The Table」工作表,過濾 Sets 含 "Level 1" 的卡,自 HYPERLINK 顯示文字取得卡號;同卡號存在 e/j 兩版時 MUST 只保留 j 版並以基礎卡號(去除尾碼)入庫。產出 `data/cards.json`,每張卡含:卡號、類型(魔物/夥伴/術/事件)、卡名(英)、對應魔物、費用、A/D、級別(無/中級/上級)、屬性/效果名、效果原文、魔力、傷害、**收錄產品清單(Sets 欄逗號拆分)**、卡圖連結。

#### Scenario: e/j 去重採日版
- **WHEN** 抽取遇到 S-019e 與 S-019j 兩列
- **THEN** cards.json 僅含一筆 S-019,其效果文為 j 版內容

#### Scenario: 抽出 67 種卡
- **WHEN** 抽取腳本執行完成
- **THEN** cards.json 恰含 67 種唯一卡號(M×15+S×28+P×9+E×15;官方「全60種」為稀有度合併算法,唯一卡號為 67)

#### Scenario: 收錄產品入庫
- **WHEN** 某卡的 Sets 欄為 "Series 1, Level 1, The Best Booster 1"
- **THEN** cards.json 該卡的 sets 為三個產品標籤的清單
