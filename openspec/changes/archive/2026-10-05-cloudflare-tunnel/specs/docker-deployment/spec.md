## ADDED Requirements

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

## MODIFIED Requirements

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

## REMOVED Requirements

### Requirement: 反向代理與對外服務
**Reason**: 改由 Cloudflare Tunnel 對外提供服務,VPS 不再發布 80 / 443 埠,Caddy 反向代理、純 IP 運作與 ACME 自動簽發都不再需要。
**Migration**: 依「經 Cloudflare Tunnel 對外服務」部署:在 Cloudflare 建立通道與公開網域,VPS 的 `.env` 設定 `TUNNEL_TOKEN`,以新的 `docker-compose.yml` 執行 `docker compose up -d --remove-orphans` 移除 `caddy`。步驟見 README「VPS 部署」。
