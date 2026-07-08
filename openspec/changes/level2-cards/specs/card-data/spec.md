# card-data — 差分:資料範圍擴至 Level 2

卡池自第一彈 67 張擴至 134 張(Level 1 + Level 2)。

## MODIFIED Requirements

### Requirement: 卡片資料抽取
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
