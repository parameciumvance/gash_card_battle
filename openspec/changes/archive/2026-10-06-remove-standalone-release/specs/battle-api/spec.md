## MODIFIED Requirements

### Requirement: 執行環境中繼資訊
API SHALL 提供 `GET /api/meta` 回傳執行環境資訊:`assets`(卡圖安裝狀態:`installed`、既有張數 `count`、應有張數 `expected`、卡圖目錄 `install_dir`,未安裝時提示放置位置)與 `version`(版本號:Docker 部署為觸發建置的 git tag 名稱,開發環境為當下的 `git describe`,都取不到時為 `dev`)。`count` SHALL 只計卡圖目錄中的 `{卡號}.webp`(格式見 `card-data`「卡圖資產與備援」),其他格式的檔案 MUST NOT 計入。回應 MUST NOT 含 `tunnel_url`。

#### Scenario: 卡圖未安裝時回報狀態
- **WHEN** 卡圖目錄不存在時請求 `GET /api/meta`
- **THEN** `assets.installed` 為 false 且 `install_dir` 為卡圖目錄

#### Scenario: 舊格式卡圖不計入
- **WHEN** 卡圖目錄只有 `.jpg` 卡圖時請求 `GET /api/meta`
- **THEN** `assets.count` 為 0

#### Scenario: 回報版本號
- **WHEN** 以 `GASH_VERSION=v0.9.1` 啟動的服務收到 `GET /api/meta`
- **THEN** 回應的 `version` 為 `v0.9.1`

#### Scenario: 不回報通道網址
- **WHEN** 前端請求 `GET /api/meta`
- **THEN** 回應只含 `assets` 與 `version`,不含 `tunnel_url`

### Requirement: 卡圖靜態資源外部化
卡圖目錄 SHALL 為環境變數 `GASH_ASSETS_DIR` 指定的目錄,設定時即使該目錄不存在也 MUST NOT 改用其他位置;未設定時 SHALL 為 repo 的 `frontend/assets/`。卡圖靜態路由(`/static/assets/`)SHALL 掛載自該目錄。目錄下沒有 `cards/` 時 SHALL 視為未安裝:伺服器照常啟動,遊戲可完整進行。

#### Scenario: 環境變數指定卡圖目錄
- **WHEN** `GASH_ASSETS_DIR` 指向某目錄且前端請求 `/static/assets/cards/S-001.webp`
- **THEN** 回應該目錄中的 `cards/S-001.webp`

#### Scenario: 環境變數優先
- **WHEN** `GASH_ASSETS_DIR` 指向不存在的目錄
- **THEN** 卡圖目錄仍為該目錄並回報未安裝,不改用 repo `frontend/assets/`

#### Scenario: 開發模式預設
- **WHEN** 於 repo 以 `uvicorn gash.api.app:app` 啟動且未設定 `GASH_ASSETS_DIR`
- **THEN** 卡圖取自 repo `frontend/assets/`

#### Scenario: 完全未安裝卡圖
- **WHEN** 卡圖目錄下沒有 `cards/`
- **THEN** `GET /api/meta` 回報未安裝,伺服器正常啟動且遊戲可完整進行
