# docker-deployment — 設計

VPS 上的實際操作步驟(一次性設置、發布、卡圖、遷移與回退)以 README「VPS 部署」為準,本檔只整理架構與理由。

## 架構

`docker-compose.yml` 有三個容器,全部在 compose 的內部網路裡,**沒有任何容器發布埠到主機**。

| 容器 | 責任 | 對外連線 |
|---|---|---|
| `app` | GHCR 上的應用映像檔,單一 uvicorn 行程,房間狀態在記憶體;健康檢查打 `GET /api/meta` | 無 |
| `cloudflared` | Cloudflare Tunnel 連接器,把公開網域的請求轉給 `app:8000` | 只有 outbound(連到 Cloudflare) |
| `watchtower` | 定期輪詢映像檔來源,更新貼了 label 的容器(`app`、`cloudflared`) | 只有 outbound(查詢 registry) |

```text
瀏覽器 ──HTTPS / WSS──▶ Cloudflare 邊緣 ◀──outbound 通道── cloudflared ──HTTP──▶ app:8000
```

## 映像檔

- `Dockerfile` 與開發容器分開,只裝核心依賴,不含 `tests/`、`tools/`、`.devcontainer/`、`ref/`。
- MUST 用 editable 安裝(`pip install -e .`):`src/gash/paths.py` 以 `__file__` 往上推算 repo 根目錄來定位 `frontend/`、`data/`,非 editable 安裝會把檔案複製進 site-packages 而算錯路徑。
- 卡圖不在映像檔內,放在具名 volume `card-assets`(掛到 `GASH_ASSETS_DIR`),換映像檔、重建容器都不會動到。

## 單一行程

房間狀態只存在單一行程的記憶體,沒有外部儲存。服務 MUST 只跑一個 uvicorn 行程,不能多 worker 或多 replica,否則同一房間的請求可能落到沒有該房間資料的行程。因此每次重啟 `app`,進行中的對局都會消失。

## 發布與更新

- CI 只在推送 `v*` tag 時建置映像檔並推上 GHCR(標上版號與 `latest`),一般 push 只跑測試。
- VPS 端由 watchtower 每 300 秒輪詢,有新版就拉取並重啟該容器。CI 不持有任何能連進 VPS 的憑證(SSH 金鑰、VPN 授權)。
  - 理由:只要 CI 有能力觸發 VPS 執行指令,Secrets 外洩時這個能力就會一起外洩,加固憑證只能縮小傷害範圍。直接拿掉這個能力,外洩時最多只能推一個惡意映像檔到 registry。代價是部署要等下一次輪詢。
- `app` 只在打 tag 時才有新版,維護者藉此挑對局少的時間發布(重啟會讓對局消失)。
- `cloudflared` 使用 `latest`,有新版就自動更新,容器內關閉它自己的更新機制(`--no-autoupdate`)。
  - 理由:重啟 `cloudflared` 不會重啟 `app`,房間狀態保留,前端的 WebSocket 斷線後 1.5 秒自動重連並由 `welcome` 取回完整狀態,所以不需要挑時間;不更新反而會逐漸落後於 Cloudflare 支援的版本。新版有問題時,把 image 改釘到上一個正常的版本。

## 對外服務

- **Cloudflare Tunnel**:`cloudflared` 主動向 Cloudflare 建立 outbound 連線,VPS 不需要為網頁服務開放任何 inbound 埠。TLS 在 Cloudflare 邊緣終止,VPS 不做憑證管理。
- **不發布埠**:Docker 發布的埠會直接寫入 iptables、繞過 `ufw`。不發布埠就不需要依賴主機防火牆設定正確;供應商的雲端防火牆也不開放 80 / 443,作為第二層防護。
- **遠端管理的通道**:通道與轉送規則(`card-battle.zatchholic.com` → `http://app:8000`)設定在 Cloudflare Zero Trust 後台,VPS 只需要一組 token。只有一條轉送規則,放進版本控制的價值不大;規則內容記在 README。
- **token**:只放在 VPS 部署目錄的 `.env`(權限 600,`.gitignore` 已排除)。compose 以 `${TUNNEL_TOKEN:?...}` 取值,沒設定時 `docker compose` 在解析設定階段就失敗,不會啟動一個連不上的連接器。
- **WebSocket**:`uvicorn[standard]` 每 20 秒送一次 ping,閒置中的對局連線不會被切斷;萬一被切斷,前端會自動重連。
- **連線端 IP**:`app` 看到的來源都是 `cloudflared` 容器。目前沒有功能使用玩家 IP,所以沒有開啟 uvicorn 的 `--proxy-headers`;之後若需要(例如依 IP 限流),應改讀 Cloudflare 的 `CF-Connecting-IP`。
- **HTTP 導向 HTTPS**:由 Cloudflare 的 Always Use HTTPS(或只針對此網域的 Redirect Rule)負責,不在 repo 的設定裡。前端依頁面協定選擇 `ws` / `wss`,分享連結取自 `location.origin`,所以應用程式不需要知道自己的公開網址。
