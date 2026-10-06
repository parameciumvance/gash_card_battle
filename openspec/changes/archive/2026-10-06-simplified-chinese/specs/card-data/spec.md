## ADDED Requirements

### Requirement: 簡體中文卡片文字
簡體中文的卡片文字 SHALL 存於 `data/cards.zh-CN.json`,與 `data/cards.zh-TW.json` 相同結構。簡體中文的介面字典 `frontend/i18n/zh-CN.json` 與規則頁 `frontend/i18n/rules.zh-CN.json` 亦同。三個檔 SHALL 由工具自對應的繁體中文檔轉換產生,MUST NOT 手動編輯;繁體中文檔修改後 SHALL 重新產生,兩者 MUST 保持同步。

轉換 SHALL 把繁體字形轉為簡體字形,並把台灣用語轉為大陸用語;遊戲術語 SHALL 依工具的術語表保留或替換(例如「宣告」保留,不轉為「声明」)。角色名、卡名、術名 SHALL 只轉字形,沿用繁體中文的譯名。`name_ja` MUST NOT 轉換,仍 MUST 與 `data/cards_ja.csv` 一致。修改這些檔 MUST NOT 影響 `cards.json` 的數值與邏輯。

#### Scenario: 譯名只轉字形
- **WHEN** 產生 M-001 的簡體中文文字
- **THEN** `name` 為「贾修・贝尔」,`name_ja` 仍為「ガッシュ・ベル」

#### Scenario: 遊戲術語保留
- **WHEN** 繁體中文的效果文含「【宣告使用→】」
- **THEN** 簡體中文為「【宣告使用→】」,不是「声明使用」

#### Scenario: 繁中修改後未重新產生
- **WHEN** 修改 `cards.zh-TW.json` 某卡的卡名但沒有重新執行工具
- **THEN** 檢查同步的測試失敗
