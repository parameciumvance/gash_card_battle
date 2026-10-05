## Context

現行部署(見 `openspec/changes/archive/2026-09-08-docker-deployment/`)在 VPS 上跑三個容器:`app`(單一 uvicorn 行程,房間狀態在記憶體)、`caddy`(唯一發布 80 / 443 埠的服務,反代到 `app:8000`)、`watchtower`(只更新貼了 label 的 `app`)。`Caddyfile` 目前是 `:80`,也就是以 VPS 的 IP 走明碼 HTTP;原本規劃補上網域後再讓 Caddy 自動簽 HTTPS。

VPS 端的已知狀況(來自上述 archive 的 design,不在 repo 內,實作前請使用者確認仍然成立):

- SSH 只能經由 Tailscale 的 tailnet 位址連線,公網沒有開放 SSH 埠。
- VPS 上的 `ufw` 沒有啟用;VPS 供應商(Linode)另有雲端防火牆。

`zatchholic.com` 的 DNS 已託管在 Cloudflare,`card-battle` 子網域目前沒有任何記錄。

## Goals / Non-Goals

**Goals:**

- 網頁服務不發布任何主機埠,VPS 不需要為它開放 inbound 埠。
- 以 `https://card-battle.zatchholic.com` 提供服務,憑證由 Cloudflare 處理。
- 從現行 Caddy 版遷移時,進行中的對局不受影響,並且可以回退。
- 通道連接器能自動更新,不需要人工維護版本。

**Non-Goals:**

- 不更動 SSH 的存取方式(已經只走 Tailscale)。
- 不設定 Cloudflare Access、WAF 規則或速率限制。應用程式本身仍對公開網域上的所有人開放,和現在一樣。
- 不修改應用程式、前端、`Dockerfile` 與 CI workflow。
- 不保留以 VPS IP 直連的備用入口。
- 不影響單機發行:launcher 的 quick tunnel 是另一種用法,沒有共用的程式碼或設定。

## Decisions

### 用 token 執行的遠端管理通道,不用本機設定檔

在 Cloudflare Zero Trust 後台建立通道,取得一組 token,`cloudflared` 以 `tunnel --no-autoupdate run` 搭配環境變數 `TUNNEL_TOKEN` 執行。轉送規則(Public Hostname `card-battle.zatchholic.com` → `http://app:8000`)設定在 Cloudflare 後台,建立時會自動加上 `card-battle` 的 CNAME 記錄。

- 替代方案:本機管理的通道(`config.yml` + 憑證 JSON 檔 + `cloudflared tunnel route dns`)。好處是轉送規則可以進版本控制;壞處是 VPS 上要多放憑證檔、要在本機裝 `cloudflared` 並登入才能建立。這裡只有一條轉送規則,版本控制的價值不大,因此選擇只需要一個 secret 的 token 方式。轉送規則的內容改寫在 README 裡。

### 拿掉 Caddy,`cloudflared` 直接連 `app:8000`

TLS 在 Cloudflare 邊緣終止,`cloudflared` 到 `app` 是 compose 內部網路,Caddy 留著已經沒有作用(沒有額外的路由、快取或憑證工作)。

- 替代方案:保留 Caddy 放在通道後面。多一個元件和一跳,沒有對應的好處,不採用。

### compose 不發布任何埠

`app`、`cloudflared`、`watchtower` 都不設 `ports`。Docker 發布的埠會直接寫入 iptables,繞過 `ufw`;不發布埠就沒有可以被繞過的東西,不需要依賴主機防火牆設定正確。供應商的雲端防火牆另外移除 80 / 443 的 inbound 規則,作為第二層防護。

### token 放在 `.env`,缺少時讓 compose 直接失敗

compose 以 `TUNNEL_TOKEN: ${TUNNEL_TOKEN:?...}` 取用 VPS 部署目錄 `.env` 裡的值。沒設定時,`docker compose` 在解析設定階段就失敗,並顯示缺少的變數,不會啟動一個連不上 Cloudflare、只會不斷重試的容器。`.env` 加入 `.gitignore`,README 以 `umask 077` 建立,權限為 600。

### `cloudflared` 交給 watchtower 自動更新

`cloudflared` 使用 `cloudflare/cloudflared:latest` 並貼上 watchtower 的 label。容器內關閉 cloudflared 自己的更新機制(`--no-autoupdate`),版本更新統一由 watchtower 負責。

- 理由:`app` 刻意只在打 tag 時才更新,是因為重啟 `app` 會讓所有對局消失。重啟 `cloudflared` 則只會讓 WebSocket 斷線,前端在斷線 1.5 秒後自動重連,並由 `welcome` 訊息取回完整狀態(`frontend/app.js` 的 `openWS`),房間狀態留在 `app` 裡不受影響。因此 `cloudflared` 不需要人工挑時間更新;放著不更新反而會逐漸落後於 Cloudflare 支援的版本。
- 替代方案:釘選版本並手動更新。避免拉到有問題的新版本,但需要人記得更新。目前規模下,自動更新加上「出問題時改釘舊版」的回退方式就足夠。

### 應用程式不需要調整代理相關設定

改用通道後,`app` 看到的連線來源會是 `cloudflared` 容器的 IP。伺服器目前沒有任何地方使用連線端 IP 或由請求組出網址(分享連結取自前端的 `location.origin`,WebSocket 依頁面協定選擇 `ws` / `wss`),因此不需要開啟 uvicorn 的 `--proxy-headers` 或信任轉發標頭。之後若要依 IP 做速率限制,應改讀 Cloudflare 的 `CF-Connecting-IP` 標頭。

### WebSocket 保活

Cloudflare 的免費方案支援 WebSocket。`uvicorn[standard]` 預設每 20 秒送一次 ping,閒置中的對局連線也有流量,不會因為閒置被切斷;萬一還是被切斷,前端也會自動重連。

## Risks / Trade-offs

- [服務可用性依賴 Cloudflare,且沒有 IP 直連的備用入口] → 接受。Cloudflare 長時間故障時,依下方回退步驟改回 Caddy 版。
- [TLS 在 Cloudflare 終止,Cloudflare 看得到明文流量] → 接受。服務沒有帳號、密碼或個資,玩家 token 只在單一房間內有效。
- [token 外洩時,他人可以用這條通道跑自己的連接器,分走部分流量] → token 只放在 VPS 的 `.env`(權限 600、不進 repo);懷疑外洩時到 Cloudflare 後台重新產生 token,再更新 `.env`。
- [自動更新拉到有問題的 `cloudflared` 版本,網站暫時無法連線] → 把 image 改釘到上一個正常的版本,執行 `docker compose up -d`。
- [`http://` 網址不會自動導向 HTTPS,WebSocket 會跟著走 `ws://`] → README 建議在 Cloudflare 開啟「Always Use HTTPS」。這是整個 `zatchholic.com` 的設定;若其他子網域需要明碼 HTTP,改用只針對 `card-battle` 的規則。
- [應用程式本身的弱點不會因為通道而消失] → 不在這次範圍。公開網域上的 API 與 WebSocket 和現在一樣對所有人開放。

## Migration Plan

假設 VPS 上正在跑 Caddy 版(`:80` 的 `Caddyfile`)。

1. **Cloudflare**:在 Zero Trust 建立 Cloudflared 類型的通道,複製 token。新增 Public Hostname:子網域 `card-battle`、網域 `zatchholic.com`、服務 `HTTP` / `app:8000`。若 `card-battle` 已經有 A 記錄,先刪除。
2. **VPS**:在 `/opt/gash-card-battle/.env` 寫入 `TUNNEL_TOKEN=...`,`chmod 600 .env`。
3. **本機**:把新的 `docker-compose.yml` 用 `scp` 傳到 VPS(`Caddyfile` 不再需要)。
4. **VPS**:`docker compose up -d --remove-orphans`。`caddy` 被移除、`cloudflared` 啟動;`app` 的設定沒有變,不會被重建,進行中的對局保留。
5. 確認 `https://card-battle.zatchholic.com` 能開啟,並實際建立一間線上房間,確認 WebSocket 連線正常。
6. 收尾:供應商的雲端防火牆移除 80 / 443 inbound 規則,從外部確認 IP 的 80 / 443 連不上;刪除 VPS 上的 `Caddyfile`;`docker volume rm` 舊的 `caddy-data` / `caddy-config`(volume 名稱會帶 compose 專案名稱前綴)。

**回退**:放回舊的 `docker-compose.yml` 與 `Caddyfile`,執行 `docker compose up -d --remove-orphans`,並重新開放防火牆的 80 埠。在第 6 步刪除 volume 之前回退,Caddy 不需要重新設定。

## Open Questions

- VPS 端的現況(SSH 只走 Tailscale、`ufw` 未啟用、使用 Linode 雲端防火牆)取自 2026-09 的 archive,需要使用者確認是否仍然成立。不成立時只影響 README 的防火牆說明,不影響這次的設計。
