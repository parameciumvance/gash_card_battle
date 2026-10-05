## 1. 部署檔案

- [x] 1.1 `docker-compose.yml`:移除 `caddy` 服務與 `caddy-data` / `caddy-config` volume;新增 `cloudflared` 服務(`cloudflare/cloudflared:latest`、`restart: unless-stopped`、`command: tunnel --no-autoupdate run`、`TUNNEL_TOKEN: ${TUNNEL_TOKEN:?...}`、watchtower label、`depends_on: app`);所有服務都不設 `ports`;更新檔頭與 watchtower 的註解(design「compose 不發布任何埠」「token 放在 `.env`」「`cloudflared` 交給 watchtower 自動更新」)
- [x] 1.2 刪除 `Caddyfile`
- [x] 1.3 `.gitignore` 加入 `.env`
- [x] 1.4 驗證 compose 設定:解析 YAML 確認沒有任何服務設 `ports`、`app` 與 `cloudflared` 有 watchtower label、`TUNNEL_TOKEN` 以 `${TUNNEL_TOKEN:?...}` 取值(開發容器沒有 docker,`docker compose config` 的實際檢查移到 3.3)

## 2. 文件

- [x] 2.1 README「VPS 部署」:開頭的架構說明改為 Cloudflare Tunnel;「一次性設置」改為建立通道與 Public Hostname(`card-battle.zatchholic.com` → `HTTP` / `app:8000`)、在 VPS 寫入權限 600 的 `.env`(以 `umask 077` 建立)、只需 `scp` `docker-compose.yml`、供應商防火牆不開放 80 / 443
- [x] 2.2 README:以「網域與 Cloudflare Tunnel」取代目前的「網域」一節,包含建議開啟 Always Use HTTPS(與只針對 `card-battle` 的替代做法)、token 外洩時重新產生、`cloudflared` 有問題時改釘舊版
- [x] 2.3 README:從 Caddy 版遷移與回退的步驟(design「Migration Plan」)

## 3. 上線與驗證(使用者在 Cloudflare 與 VPS 上執行)

- [ ] 3.1 確認 VPS 現況:SSH 只走 Tailscale、`ufw` 未啟用、使用 Linode 雲端防火牆(design「Open Questions」);不成立時修正 README 的防火牆說明
- [ ] 3.2 Cloudflare:建立通道、新增 Public Hostname,確認 `card-battle` 是 CNAME 而不是 A 記錄
- [ ] 3.3 VPS:傳上新的 `docker-compose.yml`,先在沒有 `.env` 時確認 `docker compose config` 失敗並指出缺少 `TUNNEL_TOKEN`;寫入 `.env` 後 `docker compose config` 的輸出沒有任何 `ports`;再 `docker compose up -d --remove-orphans`,確認 `app` 沒有被重建
- [ ] 3.4 驗證:`https://card-battle.zatchholic.com` 能開啟,建立線上房間並以 `wss://` 對戰;對局中執行 `docker compose restart cloudflared`,前端自動重連,對局保留
- [ ] 3.5 收尾:供應商防火牆移除 80 / 443 inbound 規則,從外部確認 VPS IP 的 80 / 443 連不上;刪除 VPS 上的 `Caddyfile` 與舊的 Caddy volume

## 4. Reconciliation 與歸檔(指南 §13)

- [ ] 4.1 同步 delta spec 回 `docker-deployment` 主 spec;`## Purpose` 的「Caddy 反向代理與對外服務」改為「經 Cloudflare Tunnel 對外服務」
- [ ] 4.2 Reconcile affected capability design and rationale:新增 `openspec/specs/docker-deployment/design.md`,整理現行架構(`app` / `cloudflared` / `watchtower`、不發布埠、單一行程限制、watchtower 輪詢取代 CI 連線、token 方式的通道、`cloudflared` 自動更新而 `app` 依 tag 更新的理由、連線端 IP 與 `CF-Connecting-IP`);不放遷移步驟與已放棄的方案
- [ ] 4.3 Update capability map:`docker-deployment` 的責任「反向代理」改為「Cloudflare Tunnel 對外」,Design 覆蓋由 Not documented 改為 Partial
- [ ] 4.4 `openspec validate --all --strict`、`python -m pytest` 全過後歸檔
