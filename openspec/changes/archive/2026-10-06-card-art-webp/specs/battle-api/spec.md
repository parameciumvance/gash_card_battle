## MODIFIED Requirements

### Requirement: 執行環境中繼資訊
API SHALL 提供 `GET /api/meta` 回傳執行環境資訊:`tunnel_url`(公開通道網址,無通道時為 null)與 `assets`(卡圖安裝狀態:`installed`、既有張數 `count`、應有張數 `expected`、建議安裝路徑 `install_dir`)與 `version`(版本號:部署時的 git tag 名稱,單機版為打包時的 `git describe`,開發環境為當下的 `git describe`,都取不到時為 `dev`)。`count` SHALL 只計卡圖目錄中的 `{卡號}.webp`(格式見 `card-data`「卡圖資產與備援」),其他格式的檔案 MUST NOT 計入。

#### Scenario: 有通道時回報網址
- **WHEN** launcher 已建立公開通道後前端請求 `GET /api/meta`
- **THEN** 回應含 `tunnel_url` 為該 https 網址

#### Scenario: 卡圖未安裝時回報狀態
- **WHEN** 卡圖目錄不存在時請求 `GET /api/meta`
- **THEN** `assets.installed` 為 false 且 `install_dir` 為建議安裝路徑

#### Scenario: 舊格式卡圖不計入
- **WHEN** 卡圖目錄只有 `.jpg` 卡圖時請求 `GET /api/meta`
- **THEN** `assets.count` 為 0

#### Scenario: 回報版本號
- **WHEN** 以 `GASH_VERSION=v0.9.1` 啟動的服務收到 `GET /api/meta`
- **THEN** 回應的 `version` 為 `v0.9.1`

### Requirement: 卡圖靜態資源外部化
卡圖靜態路由(`/static/assets/`)SHALL 掛載自資源解析模組決定的卡圖目錄,而非寫死於前端目錄之下;開發模式下(卡圖目錄即 repo `frontend/assets/`)對外行為 SHALL 與現況等價。

#### Scenario: 外部卡圖目錄生效
- **WHEN** 卡圖解析至使用者資料夾且前端請求 `/static/assets/cards/S-001.webp`
- **THEN** 回應該使用者資料夾中的對應圖檔

#### Scenario: 開發模式等價
- **WHEN** 開發模式下請求任一既有卡圖 URL
- **THEN** 回應與本變更前完全一致

### Requirement: 前端資源每次確認更新
伺服器回應前端資源(`/`,以及 `/static/`、`/data/` 之下、卡圖 `/static/assets/` 以外的檔案)時 SHALL 帶 `Cache-Control: no-cache`,讓瀏覽器每次使用前向伺服器確認;檔案未變時 SHALL 以 304 回應帶相同 `ETag` 的條件請求。卡圖(`/static/assets/`)MUST NOT 套用此標頭。部署新版後,瀏覽器 MUST NOT 混用新舊版本的前端檔案。

#### Scenario: 前端檔案每次確認
- **WHEN** 瀏覽器請求 `/static/app.js`
- **THEN** 回應帶 `Cache-Control: no-cache` 與 `ETag`

#### Scenario: 未變更時回 304
- **WHEN** 瀏覽器以上次取得的 `ETag` 再次請求 `/static/app.js`,且檔案未變
- **THEN** 伺服器回 304,不傳送內容

#### Scenario: 卡圖不套用
- **WHEN** 瀏覽器請求 `/static/assets/cards/S-001.webp`
- **THEN** 回應不帶 `Cache-Control: no-cache`
