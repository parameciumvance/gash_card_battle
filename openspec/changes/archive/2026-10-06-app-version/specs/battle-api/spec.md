## MODIFIED Requirements

### Requirement: 執行環境中繼資訊
API SHALL 提供 `GET /api/meta` 回傳執行環境資訊:`tunnel_url`(公開通道網址,無通道時為 null)與 `assets`(卡圖安裝狀態:`installed`、既有張數 `count`、應有張數 `expected`、建議安裝路徑 `install_dir`)與 `version`(版本號:部署時的 git tag 名稱,單機版為打包時的 `git describe`,開發環境為當下的 `git describe`,都取不到時為 `dev`)。

#### Scenario: 有通道時回報網址
- **WHEN** launcher 已建立公開通道後前端請求 `GET /api/meta`
- **THEN** 回應含 `tunnel_url` 為該 https 網址

#### Scenario: 卡圖未安裝時回報狀態
- **WHEN** 卡圖目錄不存在時請求 `GET /api/meta`
- **THEN** `assets.installed` 為 false 且 `install_dir` 為建議安裝路徑

#### Scenario: 回報版本號
- **WHEN** 以 `GASH_VERSION=v0.9.1` 啟動的服務收到 `GET /api/meta`
- **THEN** 回應的 `version` 為 `v0.9.1`
