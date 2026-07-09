# card-data — 卡片資料庫與資產管線

## Purpose

由 `ref/raw/Zatch Bell CCG List for TTS.xlsx` 一次性抽取,產出 repo 內版本化的結構化資料;翻譯與卡圖為獨立層。
## Requirements
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

### Requirement: 中文翻譯檔獨立
中文文本 SHALL 存於獨立檔 `data/cards.zh-TW.json`,以卡號為 key,含:卡名中譯、卡名日文原名、效果名中譯、效果全文中譯、風味文中譯(可缺)。修改翻譯 MUST NOT 影響 cards.json 的數值與邏輯。結構 SHALL 允許並列新增其他語言檔。

#### Scenario: 校對翻譯不動邏輯
- **WHEN** 修改 cards.zh-TW.json 中某術名的音譯
- **THEN** 遊戲數值行為完全不變,僅 UI 顯示文字更新

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

