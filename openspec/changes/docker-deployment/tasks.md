## 1. Production Dockerfile

- [x] 1.1 新增 `Dockerfile`(repo 根目錄,與 `.devcontainer/Dockerfile` 區隔):base image `python:3.12-slim`,`pip install -e .`(不含 `dev` extras;MUST 用 editable 安裝,見 design.md 更正說明),複製 `src/`/`frontend/`/`data/`/`pyproject.toml`,`CMD` 為 `uvicorn gash.api.app:app --host 0.0.0.0 --port 8000`(不含 `--reload`)。
      **驗收條件**:`docker build -t gash-test .` 成功;`docker run --rm -p 8000:8000 gash-test` 啟動後,`curl http://localhost:8000/api/meta` 回應 200。
      實際結果:此開發沙盒環境沒有 Docker daemon(`docker`/`podman` 指令皆不存在,無法安裝有特權的容器執行環境),改以等效方式驗證:在乾淨的暫存目錄複製 Dockerfile 會 `COPY` 的檔案(`pyproject.toml`/`src/`/`frontend/`/`data/`)、建一個全新 venv、執行 Dockerfile 裡同樣的 `pip install -e .`、啟動 `uvicorn gash.api.app:app --host 0.0.0.0 --port 8000`,確認 `GET /api/meta` 與首頁 `GET /` 皆回應 200(`{"tunnel_url":null,"assets":{...}}`)。這驗證了 Dockerfile 每一步驟的邏輯正確,但**真正的 `docker build`/`docker run` 仍需要在有 Docker 的環境(VPS 本身或使用者本機)另行驗證一次**,列入 4.1 README 章節的操作步驟供使用者實際部署時驗證。
- [x] 1.2 確認映像檔不含開發/測試/單機發行專用內容。
      **驗收條件**:`docker run --rm gash-test find / -maxdepth 3 -iname "tests" -o -iname "pytest*"` 找不到對應檔案(容器內沒有 `tests/` 目錄、沒有安裝 `pytest`)。
      實際結果:同上,沒有 Docker 可實際跑這個指令;改為靜態核對 `Dockerfile` 的 `COPY` 指令只列出 `pyproject.toml`/`src/`/`frontend/`/`data/` 四項(不含 `tests/`/`tools/`/`.devcontainer/`/`ref/`),且 `pip install -e .`(未加 `[dev]`)依 `pyproject.toml` 的 `dependencies`/`optional-dependencies` 定義只會裝 `fastapi`/`uvicorn[standard]`,不會裝 `pytest`/`pyinstaller`/`openpyxl`。

## 2. docker-compose 與 Caddy

- [x] 2.1 新增 `docker-compose.yml`:`app` 服務(用 1.1 的 Dockerfile 或 GHCR 映像檔,視環境變數/建置參數決定;掛一個具名 volume 到 `GASH_ASSETS_DIR` 指向路徑,不對外開放埠)、`caddy` 服務(對外開放 80,掛載 `Caddyfile`,depends_on `app`)、`watchtower` 服務(輪詢 GHCR 自動更新有 label 的 `app` 容器,見 design.md「實作階段最終更正」——CI 不再主動連進 VPS)。
      **驗收條件**:VPS 上以 IP 直連情境下,`docker compose up -d` 後瀏覽器連 `http://<VPS_IP>/` 能看到首頁,能建立本機測試模式對局並完整跑完一局(含 WebSocket 即時更新)。
      實際結果:此開發沙盒沒有 Docker,無法實際跑 `docker compose up`。已用 `python3 -c "import yaml; yaml.safe_load(...)"` 驗證 YAML 語法正確、服務/欄位結構符合預期(`app` 無對外 port、掛 `card-assets` volume 到 `/app/assets`、`caddy` 對外開 80/443)。**真正的 `docker compose up -d` 端到端驗證(含建房、WebSocket)MUST 在使用者的 VPS 或任何有 Docker 的機器上補做一次**,已列入 4.1 README 部署步驟。
- [x] 2.2 新增 `Caddyfile`:站台區塊先用預留位置(如註解說明「填入 VPS 公開 IP 或之後的網域」),反代到 `app:8000`。
      **驗收條件**:文件內有清楚註解說明「換成網域即自動 HTTPS,不需其他設定」;實際填入一個測試網域後(若使用者手邊有可測試的網域/DNS)重啟 Caddy,確認能透過 HTTPS 連上且 WebSocket(`wss://`)正常運作——若當下沒有可用網域可測,至少確認純 IP 情境下 HTTP 全流程正常,網域情境列為文件說明並待日後補測。
      實際結果:改用比原設想更簡單的做法——站台區塊直接寫 `:80`(監聽所有介面,不需要填入 VPS 實際 IP 字串),註解說明清楚。同樣受限於沒有 Docker/Caddy 可執行,無法實際驗證重啟後的 HTTP/HTTPS 行為,已列入 4.1 README 步驟由使用者在真正部署時驗證。
- [x] 2.3 `app` 服務加上 `healthcheck`,打 `GET /api/meta`。
      **驗收條件**:`docker compose ps` 顯示 `app` 服務狀態為 healthy(容器啟動一段時間後)。
      實際結果:同上,無法實際執行 `docker compose ps` 驗證;已在 `docker-compose.yml` 的 `app` 服務加上 `healthcheck`(用 `python3 -c "import urllib.request; ..."` 打 `/api/meta`,不需要額外裝 `curl`,`python:3.12-slim` 本身就有 `python3`),邏輯正確性已透過閱讀 Docker Compose healthcheck 語法規格確認。

## 3. GitHub Actions

- [x] 3.1 新增 `.github/workflows/test.yml`:`on: push`(所有分支或至少 main)與 `pull_request` 觸發,跑 `pip install -e ".[dev]"` + `pytest`。
      **驗收條件**:push 一個不影響測試結果的小改動,GitHub Actions 頁面顯示此 workflow 執行且通過;確認此 workflow 沒有任何連線 VPS 或建置/推送映像檔的步驟。
      實際結果:檔案已建立,`python3 -c "import yaml; yaml.safe_load(...)"` 驗證語法正確,步驟只有 checkout/setup-python/安裝依賴/跑 pytest,沒有任何連線 VPS 或映像檔相關步驟。**實際 push 觸發、在 GitHub Actions 頁面看到執行結果,需要使用者實際 push 到遠端 repo 才能驗證**——這是對外可見的操作(觸發 CI、可能通知協作者),不是這次實作階段能代為執行的項目。
- [x] 3.2 新增 `.github/workflows/deploy.yml`:`on: push tags: v*` 觸發——build Docker 映像檔、登入 GHCR、推送並標上 tag 版號與 `latest`。**不**連進 VPS(最終架構改為 VPS 端 watchtower 輪詢 GHCR 自動更新,見下方第 5 次更正)。
      **驗收條件**:推送一個測試 tag(如 `v0.0.1-test`),GitHub Actions 頁面顯示 build+push 兩個階段都成功;GHCR 的 package 頁面能看到新推送的映像檔與對應 tag;VPS 上跑 watchtower 的情況下,在下一次輪詢週期內 `docker compose ps` 顯示 `app` 容器已更新重啟(啟動時間為最新)。
      實際結果:檔案已建立並驗證 YAML 語法/結構正確(三個步驟:checkout → GHCR 登入 → build+push 兩個 tag)。**推送測試 tag、實際觀察 watchtower 拉新版,需要使用者在完成 README 的 VPS 初始化步驟後才能驗證**——推送 tag 是對外可見的操作,且此環境沒有可實際連線的 VPS,不是這次能代為執行驗證的項目。
      實作階段更正(使用者第一次實際打 tag 部署,依序踩了三個坑,逐一排查修正):
      1. Build+push 階段報 `denied: installation not allowed to Create organization package`——repo 的 Settings → Actions → General → Workflow permissions 預設是唯讀,`GITHUB_TOKEN` 沒有 push package 的權限,改成 "Read and write permissions" 後解決,不是程式碼問題。
      2. SSH 部署階段報 `ssh: handshake failed: EOF`——最初猜測是 `tailscale/github-action` 沒帶 `tags` 參數導致節點憑證過期,補上 `tags: tag:ci` 後重新部署,問題依舊(log 仍顯示同樣的 `[ -n "" ]`)。回頭直接查該 action `v2` 版本的原始碼才找到真正根因:內部判斷式測試的是 `inputs['oauth-secret']` 是否有值,用傳統 `authkey` 認證時這段邏輯完全不會執行,跟有沒有設 `tags` 無關。真正修正:`deploy.yml` 改用 OAuth client 認證(`oauth-client-id`+`oauth-secret`,對應 GitHub Secrets 改名為 `TS_OAUTH_CLIENT_ID`/`TS_OAUTH_CLIENT_SECRET`),ACL 的 `tagOwners` 宣告仍需保留。詳見 design.md 的第三次更正說明。
      3. 改用 OAuth client 後,連線時改報 `403: calling actor does not have enough permissions to perform this function`——查證確認該 action 是「用 OAuth client 動態產生一把 auth key、再用這把 key 執行 tailscale up」,所以 OAuth client 需要的權限是 **「Auth Keys」類別的「Write」**,不是原先猜測的「Devices」,也不是介面上另一個容易選錯的「OAuth Keys」;且建立時 MUST 指定允許套用的 tag(`tag:ci`),須與 `deploy.yml` 的 `tags` 輸入一致。已更新 README 對應步驟的 scope 說明,詳見 design.md 第四次更正。
      4. 改用 OAuth client 後,「Connect to Tailscale」步驟本身成功(確認 runner 已加入 tailnet),但 `appleboy/ssh-action` 部署仍以同樣的 `handshake failed: EOF` 失敗。逐層排查:VPS 的 `journalctl -u ssh` 在失敗時間點完全沒有這次連線的紀錄;`sudo ufw status verbose` 顯示 `inactive`;一度懷疑是 Linode Cloud Firewall 的預設 inbound drop 擋掉,但用 `tailscale ping` 診斷發現連線走 **DERP relay**(非 P2P 直連)——relay 模式下雙邊都是各自對 DERP 伺服器發起 outbound 連線,任何 stateful 雲端防火牆都不會擋這種回程流量,這個假設其實是錯的。改用原生 `ssh -vvv` 直連後才找到真正根因:回應的 SSH server 軟體版本顯示為 `Tailscale`(不是 VPS 真正的 `sshd`),並在使用者驗證前送出 `tailscale: tailnet policy does not permit you to SSH to this node` 後關閉連線——**Tailscale SSH 這個功能其實有啟用**,依 ACL 的 `"ssh"` 區塊(`src: autogroup:member, dst: autogroup:self`)做存取檢查,`tag:ci` 這種 tagged 節點不算 `autogroup:member`,沒有規則涵蓋而預設拒絕。這個部署設計本來就用專屬 deploy key 走一般 SSH 金鑰驗證,不需要 Tailscale SSH 這層存取控制,修正為在 VPS 上執行 `sudo tailscale set --ssh=false` 關閉即可。詳見 design.md 第五次更正。
      5. 上一項修正(關閉 Tailscale SSH)雖然可行,但重新評估「CI 主動 SSH 進 VPS」這個模式的安全性後,決定改架構:`deploy.yml` 移除所有 Tailscale/SSH 步驟,只做 build+push image 到 GHCR;VPS 上改跑 watchtower 容器定期輪詢 GHCR 自動更新。GitHub Secrets 不再需要任何能連進 VPS 的憑證(`VPS_HOST`/`VPS_USER`/`VPS_SSH_KEY`/`TS_OAUTH_CLIENT_ID`/`TS_OAUTH_CLIENT_SECRET` 全部移除),此項驗收條件與 3.3 也隨之改變,見下。詳見 design.md「實作階段最終更正」。
      6. 以上各項皆需要使用者實際帳號權限才能操作驗證,已記錄在 README 供依循,無法由這次實作代為執行完整驗證。
- [ ] 3.3 (架構改為 watchtower 輪詢後,原本的 Secrets 設定項目已不適用,改為)確認 VPS 上 watchtower 容器已啟動並能拉到 GHCR 映像檔(若 repo 為 private,已完成 `docker login ghcr.io` 並掛載 `~/.docker/config.json` 給 watchtower)。
      **驗收條件**:VPS 上 `docker compose ps` 能看到 `watchtower` 容器狀態為 running;推送一個測試 tag 後,在其輪詢週期內 `app` 容器被自動更新(啟動時間變新)。
      **此項為使用者需在自己的 VPS 上手動完成的一次性操作,不是程式碼變更,無法由這次實作代為執行**——具體步驟已寫進 README「VPS 部署」章節(見 4.1)。完成後請自行勾選。

## 4. 文件與收尾

- [x] 4.1 README 新增「VPS 部署」章節,記錄一次性手動設置步驟:VPS 安裝 Docker/Docker Compose、準備 `docker-compose.yml`/`Caddyfile`、GitHub repo Secrets 需要哪些欄位、之後補網域時要改哪個檔案的哪一行。
      **驗收條件**:依照 README 步驟,能在一台全新的 Ubuntu 24.04 VPS 上,不看其他文件、只靠 README 這段內容完成從零到能被 `docker compose pull && docker compose up -d` 部署的一次性設置。
      實際結果:新增「VPS 部署」章節(單機發行之後、測試之前),涵蓋:已知限制提醒(單一行程、重啟即失局)、一次性設置步驟(裝 Docker、部署目錄放兩個檔案、產生 deploy-only SSH key、GitHub Secrets 三個欄位、GHCR 可見性)、發布新版本(打 tag 指令)、之後補網域(改 Caddyfile 一行)、卡圖(維持既有版權提醒)。**依此步驟在真實 VPS 上走一遍、確認真的能部署成功,需要使用者實際的 VPS 環境才能驗證**,這次僅能確保步驟邏輯自洽(對應到已建立的 `docker-compose.yml`/`Caddyfile`/`deploy.yml` 內容一致)。
      實作階段更正(使用者實際照著操作後回報):原始版本只有第 2 步明確寫「VPS 上」,緊接著的「產生部署用 SSH 金鑰」步驟完全沒標示執行地點,導致使用者誤在 VPS 上執行 `ssh-keygen`/`ssh-copy-id`——`ssh-copy-id ... youruser@your-vps-ip` 在 VPS 上執行等於叫 VPS 用 SSH 連回自己的公網 IP,許多雲端網路環境不支援這種「從自己連自己」(hairpin),導致指令卡在連線階段直到逾時,看起來像「按任何鍵都沒反應」。已重寫整節,每一步驟前面都明確標注「(本機)」或「(VPS)」,並把「複製檔案到 VPS」「改網域後覆蓋設定檔」這類步驟拆成本機執行 `scp` + VPS 執行後續指令兩個子步驟,避免同一段文字混雜兩種執行地點。
      實作階段再更正(使用者實際照著修正後版本操作,又遇到兩個新坑):
      1. 使用者的 VPS SSH 只開放在 Tailscale 內網(`100.x.x.x`),本機在 **WSL2** 執行這些指令——WSL2 有自己獨立的網路命名空間,跟 Windows 宿主機分開,Windows 端裝了 Tailscale 不代表 WSL2 也連得上同一個 tailnet,導致卡在 TCP 連線階段。這連帶影響了 3.2(見下)。
      2. 解決網路問題、`ssh` 本身能登入後,`ssh-copy-id` 依然卡住——VPS 關閉了密碼登入(`PasswordAuthentication no`),`ssh-copy-id` 預設想先用密碼認證才能塞入新公鑰,卡在等一個不會出現的密碼提示。
      已在步驟 4 補充「疑難排解」小節,涵蓋這兩種卡住情境與對應解法(WSL2 需另外裝一份 Tailscale;`ssh-copy-id` 卡住時改用 `cat pubkey | ssh user@host "cat >> ~/.ssh/authorized_keys"` 繞過)。
      實作階段再更正(第三次,使用者設定 Secrets 時發現措辭不夠明確):步驟 5「Settings → Secrets and variables → Actions 新增」沒有講清楚要點「Secrets」分頁還是「Variables」分頁——GitHub 這個頁面下兩個分頁並存,Variables 是明文儲存,`VPS_SSH_KEY`/`TS_AUTHKEY` 這類憑證絕對不能放錯分頁。已在該步驟明確加註「切到 Secrets 分頁,不是 Variables」。
      實作階段最終更正(架構改為 watchtower 輪詢後):以上幾輪關於 SSH 金鑰產生、`ssh-copy-id`、WSL2/Tailscale、Secrets 分頁的疑難排解內容,對應的 README 步驟已整段移除(不再需要 deploy-only SSH key、不再需要任何 Tailscale 相關 Secrets)。這些記錄保留作為「CI 直接 SSH 進 VPS」這條路徑當初踩過的坑的歷史紀錄,但**不再對應現在的 README 內容**——現在的 README「VPS 部署」章節已改寫為 5 步驟(裝 Docker、建目錄、傳兩個檔案、確認 GHCR 可見性、`docker compose up -d`),不含任何 SSH 金鑰或 Tailscale 設定步驟。詳見 design.md「實作階段最終更正」。
- [x] 4.2 執行完整測試套件與 `openspec validate docker-deployment`。
      **驗收條件**:`pytest` 全數通過(容器化與 CI 設定不影響既有測試);`openspec validate docker-deployment` 回報 valid。
      實際結果:224 個測試全數通過;`openspec validate docker-deployment` 回報 valid。
