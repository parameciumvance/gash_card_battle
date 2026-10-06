# docker-deployment Specification

## Purpose

在 VPS 上以容器長期常駐提供線上對戰服務。

Scope:production 容器映像檔、經 Cloudflare Tunnel 對外服務、CI 的測試 / 建置分流、VPS 端的自動更新與健康檢查。不含單機發行(見 `standalone-release`)與房間 / 對戰行為本身(見 `online-room`、`battle-api`)。

## Requirements

### Requirement: Production 容器映像檔
專案 SHALL 提供獨立於開發容器(`.devcontainer/Dockerfile`)的 production `Dockerfile`,只安裝 `pyproject.toml` 核心依賴(不含 `dev` extras),進入點為單一 uvicorn 行程(不帶 `--reload`,不使用多 worker)。房間狀態存於行程記憶體,服務 MUST NOT 以多 replica/多 worker 方式水平擴展。映像檔 SHALL 以 build arg `GASH_VERSION` 帶入版本號並設為同名環境變數;CI 建置時 SHALL 傳入觸發部署的 tag 名稱。

#### Scenario: 映像檔不含開發工具與測試檔案
- **WHEN** 建置 production 映像檔
- **THEN** 映像檔內不包含 `tests/`、`tools/`、`.devcontainer/`、`pytest`/`pyinstaller`/`openpyxl` 等僅供開發或單機發行使用的檔案與套件

#### Scenario: 容器啟動即提供服務
- **WHEN** 以此映像檔啟動容器並對映對外埠
- **THEN** 瀏覽器可連上首頁,且可建立本機測試模式或線上房間並完成一局對戰

#### Scenario: 映像檔帶版本號
- **WHEN** 推送 tag `v0.9.1` 觸發建置,並以產出的映像檔啟動容器
- **THEN** `GET /api/meta` 的 `version` 為 `v0.9.1`

### Requirement: CI 測試與建置分流
CI SHALL 區分「一般提交」與「正式發布」兩種流程:push 或 pull request 到主分支時只執行測試套件,不得觸碰部署環境;僅當推送符合版本號格式(`v*`)的 tag 時,才建置映像檔並推送至容器登錄庫。CI MUST NOT 持有任何能連進 VPS 的常駐憑證(SSH 金鑰、VPN 授權等)——容器更新由 VPS 端自行輪詢容器登錄庫觸發,不是 CI 主動推送。

#### Scenario: 一般 push 不影響線上服務
- **WHEN** 開發者 push 一般commit 到主分支
- **THEN** CI 執行測試套件,不建置映像檔、不連線 VPS、線上服務不受影響

#### Scenario: 打版號 tag 觸發建置
- **WHEN** 開發者推送符合 `v*` 格式的 tag(如 `v0.2.0`)
- **THEN** CI 建置映像檔並推送至容器登錄庫、標上該版號與 `latest`,流程到此結束,不連線 VPS

### Requirement: VPS 端自動更新與健康檢查
VPS 端 SHALL 執行一個定期輪詢容器登錄庫的更新代理,偵測到應用服務或通道連接器的映像檔有新版本時,自動拉取並重啟該容器,不需要外部(CI)主動觸發。更新代理 MUST 只管理這兩個容器。重啟通道連接器 MUST NOT 連帶重啟應用服務。容器編排 SHALL 在應用容器啟動或更新後,透過既有的 `GET /api/meta` 端點確認服務就緒,不需另外新增健康檢查專用端點。

#### Scenario: 新版映像檔自動生效
- **WHEN** 容器登錄庫出現比目前執行中版本更新的映像檔
- **THEN** VPS 端的更新代理在下一次輪詢週期內自動拉取新映像檔並重啟應用容器,不需人工介入或 CI 連線

#### Scenario: 更新後容器就緒才視為部署成功
- **WHEN** VPS 執行容器更新流程
- **THEN** 編排設定持續檢查 `/api/meta` 直到回應成功,才視為該次部署完成

#### Scenario: 通道連接器更新不影響對局
- **WHEN** 更新代理拉取新版通道連接器並重啟它
- **THEN** 應用容器沒有重啟,房間與對局狀態都保留;玩家的 WebSocket 短暫斷線後自動重連,回到原本的對局畫面

### Requirement: 經 Cloudflare Tunnel 對外服務
部署 SHALL 透過 Cloudflare Tunnel 對外提供服務:VPS 上的通道連接器(`cloudflared`)主動向 Cloudflare 建立 outbound 連線,在 Cloudflare 設定的公開網域收到的請求經此通道轉送到應用服務。compose 內任何服務 MUST NOT 發布埠到主機,VPS 不需要為網頁服務開放任何 inbound 埠。HTTPS 由 Cloudflare 處理,VPS 端不需要任何憑證管理。通道 MUST 正確轉發 WebSocket 升級請求,不得中斷 `/api/rooms/{code}/ws` 連線。

通道 token MUST 只存放在 VPS 部署目錄的 `.env`,不得進入 repo。未設定 token 時,編排 MUST 拒絕啟動並指出缺少的變數。

#### Scenario: 經公開網域以 HTTPS 連線
- **WHEN** 瀏覽器開啟公開網域的 `https://` 網址
- **THEN** 首頁正常載入,可建立線上房間並經 `wss://` 完成一局對戰

#### Scenario: VPS 不對外開放網頁埠
- **WHEN** 從外部連線到 VPS 公開 IP 的 80 或 443 埠
- **THEN** 連線失敗,主機上沒有任何服務在聽這些埠

#### Scenario: 缺少通道 token
- **WHEN** VPS 部署目錄沒有設定 `TUNNEL_TOKEN` 就執行 `docker compose up -d`
- **THEN** 指令直接失敗並指出缺少 `TUNNEL_TOKEN`,不會啟動任何容器
