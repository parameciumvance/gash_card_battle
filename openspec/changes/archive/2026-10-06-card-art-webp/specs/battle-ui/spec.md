## ADDED Requirements

### Requirement: 卡圖網址
所有顯示卡圖的地方(卡片元件、聚焦展示、規則頁的範例卡與圖示)SHALL 以 `/static/assets/cards/{卡號}.webp` 請求卡圖(格式見 `card-data`「卡圖資產與備援」),MUST NOT 改請求其他副檔名。請求失敗時依「卡圖安裝狀態提示」與「規則頁」的缺圖呈現處理。

#### Scenario: 卡片元件請求 WebP
- **WHEN** 盤面渲染卡號 S-001 的卡
- **THEN** 卡圖的網址為 `/static/assets/cards/S-001.webp`

#### Scenario: 只裝舊格式卡圖
- **WHEN** 卡圖目錄只有 `{卡號}.jpg`,盤面渲染該卡
- **THEN** 卡圖區以卡背佔位,不改請求 `.jpg`
