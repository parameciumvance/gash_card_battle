# battle-api — 發行環境支援(delta)

## ADDED Requirements

### Requirement: 執行環境中繼資訊
API SHALL 提供 `GET /api/meta` 回傳執行環境資訊:`tunnel_url`(公開通道網址,無通道時為 null)與 `assets`(卡圖安裝狀態:`installed`、既有張數 `count`、應有張數 `expected`、建議安裝路徑 `install_dir`)。

#### Scenario: 有通道時回報網址
- **WHEN** launcher 已建立公開通道後前端請求 `GET /api/meta`
- **THEN** 回應含 `tunnel_url` 為該 https 網址

#### Scenario: 卡圖未安裝時回報狀態
- **WHEN** 卡圖目錄不存在時請求 `GET /api/meta`
- **THEN** `assets.installed` 為 false 且 `install_dir` 為建議安裝路徑

### Requirement: 卡圖靜態資源外部化
卡圖靜態路由(`/static/assets/`)SHALL 掛載自資源解析模組決定的卡圖目錄,而非寫死於前端目錄之下;開發模式下(卡圖目錄即 repo `frontend/assets/`)對外行為 SHALL 與現況等價。

#### Scenario: 外部卡圖目錄生效
- **WHEN** 卡圖解析至使用者資料夾且前端請求 `/static/assets/cards/S-001.jpg`
- **THEN** 回應該使用者資料夾中的對應圖檔

#### Scenario: 開發模式等價
- **WHEN** 開發模式下請求任一既有卡圖 URL
- **THEN** 回應與本變更前完全一致
