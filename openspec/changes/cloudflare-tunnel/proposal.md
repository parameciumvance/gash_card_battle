## Why

目前 VPS 由 Caddy 對外發布 80 埠(補上網域後還要再開 443),網頁服務的埠直接暴露在公網上。改用 Cloudflare Tunnel 後,由 VPS 上的連接器主動向外連到 Cloudflare,網頁服務不需要開放任何 inbound 埠,攻擊面縮小;HTTPS 改由 Cloudflare 處理。這次同時讓服務正式以網域 `card-battle.zatchholic.com` 提供(`zatchholic.com` 的 DNS 已在 Cloudflare)。

## What Changes

- **BREAKING** 移除 Caddy:刪除 `Caddyfile`,`docker-compose.yml` 拿掉 `caddy` 服務與它的 volume。compose 內任何服務都不再發布埠,**不再能用 VPS 的 IP 直接連線**。
- 新增 `cloudflared` 服務:用 Cloudflare 後台建立的通道 token(`TUNNEL_TOKEN`)執行通道,公開網址 `card-battle.zatchholic.com` 轉送到 `http://app:8000`。token 放在 VPS 部署目錄的 `.env`,不進 repo;`.gitignore` 加入 `.env`。
- `cloudflared` 也交給 watchtower 自動更新。重啟連接器只會讓 WebSocket 短暫斷線後自動重連,不會像重啟 `app` 那樣讓進行中的對局消失。
- README「VPS 部署」改寫:建立通道與 Public Hostname、設定 `.env`、從 Caddy 版遷移與回退的步驟、移除 VPS 防火牆的 80 / 443 規則。
- 應用程式與前端不需修改:WebSocket 依頁面協定自動使用 `wss`,分享連結取自 `location.origin`,伺服器也沒有使用連線端 IP。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `docker-deployment`:以「經 Cloudflare Tunnel 對外服務」取代「反向代理與對外服務」(不再有 Caddy、純 IP 運作與 ACME 簽發的情境,改為不對外發布埠、經通道以 HTTPS 提供);修改「VPS 端自動更新與健康檢查」,通道連接器也納入自動更新。

## Impact

- 部署檔案:`docker-compose.yml`(移除 `caddy`、新增 `cloudflared`)、刪除 `Caddyfile`、`.gitignore`。
- 文件:README「VPS 部署」一節。
- 外部系統(一次性手動設定):Cloudflare Zero Trust 建立通道與 Public Hostname(會自動建立 `card-battle` 的 CNAME 記錄)、VPS 上的 `.env`、VPS 供應商防火牆移除 80 / 443 inbound 規則。
- 不受影響:`Dockerfile`、`deploy.yml` / `test.yml`、應用程式與前端程式碼、單機發行(`standalone-release` 的 launcher 用的是一次性的 quick tunnel,與此無關)。
- 遷移時只會移除 `caddy`、啟動 `cloudflared`,`app` 容器的設定沒變、不會被重建,進行中的對局不受影響。
