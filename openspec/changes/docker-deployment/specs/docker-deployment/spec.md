## ADDED Requirements

### Requirement: Production 容器映像檔
專案 SHALL 提供獨立於開發容器(`.devcontainer/Dockerfile`)的 production `Dockerfile`,只安裝 `pyproject.toml` 核心依賴(不含 `dev` extras),進入點為單一 uvicorn 行程(不帶 `--reload`,不使用多 worker)。房間狀態存於行程記憶體,服務 MUST NOT 以多 replica/多 worker 方式水平擴展。

#### Scenario: 映像檔不含開發工具與測試檔案
- **WHEN** 建置 production 映像檔
- **THEN** 映像檔內不包含 `tests/`、`tools/`、`.devcontainer/`、`pytest`/`pyinstaller`/`openpyxl` 等僅供開發或單機發行使用的檔案與套件

#### Scenario: 容器啟動即提供服務
- **WHEN** 以此映像檔啟動容器並對映對外埠
- **THEN** 瀏覽器可連上首頁,且可建立本機測試模式或線上房間並完成一局對戰

### Requirement: 反向代理與對外服務
部署 SHALL 透過 Caddy 反向代理對外提供服務,應用服務本身不直接對外開放埠。Caddy 設定 SHALL 支援先以純 IP(HTTP)運作,之後補上網域時僅需替換站台位址即可自動取得 HTTPS,不需額外設定憑證工具。反代 MUST 正確轉發 WebSocket 升級請求,不得中斷 `/api/rooms/{code}/ws` 連線。

#### Scenario: 純 IP 運作
- **WHEN** 尚未設定網域,Caddyfile 的站台區塊為 VPS 公開 IP
- **THEN** 服務以明碼 HTTP 正常運作,WebSocket 連線正常建立與維持

#### Scenario: 補上網域後自動取得 HTTPS
- **WHEN** 將 Caddyfile 站台位址由 IP 改為網域並重啟 Caddy
- **THEN** Caddy 自動透過 ACME 簽發憑證,服務改以 HTTPS(`wss://`)運作,不需要額外的憑證管理步驟

### Requirement: CI 測試與部署分流
CI SHALL 區分「一般提交」與「正式發布」兩種流程:push 或 pull request 到主分支時只執行測試套件,不得觸碰部署環境;僅當推送符合版本號格式(`v*`)的 tag 時,才建置映像檔、推送至容器登錄庫,並觸發 VPS 端更新。

#### Scenario: 一般 push 不影響線上服務
- **WHEN** 開發者 push 一般commit 到主分支
- **THEN** CI 執行測試套件,不建置映像檔、不連線 VPS、線上服務不受影響

#### Scenario: 打版號 tag 觸發部署
- **WHEN** 開發者推送符合 `v*` 格式的 tag(如 `v0.2.0`)
- **THEN** CI 建置映像檔並推送至容器登錄庫、標上該版號與 `latest`,並連線 VPS 完成容器更新與重啟

### Requirement: 部署後健康檢查
VPS 端的容器編排 SHALL 在應用容器啟動或更新後,透過既有的 `GET /api/meta` 端點確認服務就緒,不需另外新增健康檢查專用端點。

#### Scenario: 更新後容器就緒才視為部署成功
- **WHEN** VPS 執行容器更新流程
- **THEN** 編排設定持續檢查 `/api/meta` 直到回應成功,才視為該次部署完成
