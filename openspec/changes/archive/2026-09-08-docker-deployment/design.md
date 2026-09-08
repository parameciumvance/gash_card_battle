## Context

`gash.api.app` 的房間狀態(`store`)存在單一 Python 行程的記憶體裡,沒有外部資料庫或共享儲存。這對容器化部署有一個關鍵限制:**服務 MUST 以單一行程/單一 replica 運作**,不能水平擴展成多個容器或多個 worker 分攤流量,否則同一房間的不同請求可能被路由到沒有該房間狀態的行程,直接出錯。這次設計全程以此為前提。

現有的單機發行(`gash.launcher` + PyInstaller + cloudflared)是為「使用者自己電腦、短暫開著、每次啟動網址都換」設計的,VPS 常駐場景的假設完全不同(長期在線、固定入口、多人隨時可連),因此不沿用 `launcher.py`,而是直接以 `uvicorn gash.api.app:app`(無 `--reload`)為容器進入點。

## Goals / Non-Goals

**Goals:**
- 提供一份乾淨的 production `Dockerfile`,只含執行期需要的核心依賴。
- `docker-compose.yml` 讓 VPS 上「拉新映像檔、重啟」是單一指令,反向代理與應用服務分離。
- Caddy 設定現在能以純 IP 運作,之後補網域只改一處。
- GitHub Actions 建立「日常 push 只測試、打 tag 才建置部署」的分流,避免每次 push 都打斷進行中對局。
- 卡圖部署方式預留擴充點(volume + `GASH_ASSETS_DIR`),但不在這次實作。

**Non-Goals:**
- 不做零停機部署(重啟容器期間現有對局會中斷,這是接受的既有限制,見 Context)。
- 不做房間狀態持久化(對局仍然「伺服器重啟即失局」,這是現有行為,VPS 部署不改變它)。
- 不處理卡圖的實際部署方式(使用者已表明另案處理,這次只留 volume 掛載點)。
- 不做 rate limit / 房間數量上限等防護機制(現有規模不需要,之後真的遇到濫用問題再處理)。
- 不修改任何遊戲邏輯或前端程式碼。

## Decisions

- **Dockerfile 用單階段建置,base image `python:3.12-slim`**:專案 `requires-python = ">=3.12"`,選 3.12 而非 3.14(避免太新的版本在 slim image 上相容性風險未知);`pip install -e .`(不裝 `dev` extras),不需要 multi-stage(沒有編譯步驟,依賴單純)。容器內只複製 `src/`、`frontend/`、`data/`、`pyproject.toml` — 不含 `tests/`、`tools/`、`.devcontainer/`、`ref/`。
  - **實作階段更正**:MUST 用 `pip install -e .`(editable),不能用 `pip install .`。`src/gash/paths.py:app_root()` 用 `Path(__file__).resolve().parents[2]` 往上推 2 層算出 repo 根目錄(藉此定位 `frontend/`/`data/`)。非 editable 安裝會把檔案複製進 `site-packages/gash/paths.py`,往上推 2 層變成 site-packages 上層的無關目錄,服務會找不到前端靜態檔案而無法啟動;editable 安裝只放一個指回原始碼位置的連結,`__file__` 仍指向容器內複製進去的 `/app/src/gash/paths.py`,往上推 2 層正確算出 `/app`。已用一次性虛擬環境各自安裝驗證兩種方式的 `app_root()` 輸出差異,確認此修正必要。
- **不用 `--reload`,不用 gunicorn 多 worker**:`--reload` 是開發用的檔案監控機制,正式環境不需要;多 worker 會讓房間狀態(存在單一行程記憶體)在 worker 間不一致,MUST 維持單一 uvicorn 行程。
- **`docker-compose.yml` 兩個服務:`app` + `caddy`**:`app` 不對外開放埠(只在 compose 內部網路),`caddy` 是唯一對外開放 80(之後 443)的服務,反代到 `app:8000`。`app` 掛一個具名 volume 到 `GASH_ASSETS_DIR` 指向的路徑,卡圖之後怎麼填入這個 volume 是另一件事,這次容器啟動時该目錄允許是空的。
- **Caddyfile 現在用 `:80`(監聽所有介面的 80 埠,不綁定特定位址)當站台區塊,之後補網域時把 `:80` 換成網域即可**:比原先設想的「填入 VPS 公開 IP」更簡單——不需要使用者手動查詢/填入 IP 字串,`:80` 這個位址格式本來就代表「監聽這台機器所有介面的 80 埠」。Caddy 對這種非網域格式的位址不會嘗試簽 HTTPS 憑證,現在就是單純明碼 HTTP 反代;換成網域後 Caddy 會自動走 ACME 流程簽發並續期憑證,不需要額外設定 certbot。
- **GitHub Actions 分兩個 workflow**:`test.yml`(`on: push, pull_request` 到 main,跑 `pytest`)與 `deploy.yml`(`on: push tags: v*`,build image → 推 GHCR,標上該 tag 與 `latest`)。`deploy.yml` 到 push image 為止就結束,不連進 VPS(見下方「實作階段最終更正」)。VPS 上的 `docker-compose.yml` 固定引用 GHCR 的 `latest` tag(以「拿到最新已發布版本」為語意),打版號 tag 是為了在 GHCR 留下可回溯的版本紀錄與作為建置觸發點,不是每個容器都各自釘死版本號。
- **(已放棄,見下方最終更正)~~SSH 部署用專屬 deploy-only key,存進 GitHub repo Secrets~~**(`VPS_HOST`/`VPS_USER`/`VPS_SSH_KEY`):不重用使用者個人的 VPS 登入金鑰,降低外洩影響範圍。
  - **實作階段更正(VPS 網路架構跟原假設不同)**:原設計假設 `VPS_HOST` 是一個 GitHub Actions runner(在 GitHub 雲端上)可以直接連到的位址。使用者的 VPS 實際上**沒有公開的 SSH 埠,只能透過 Tailscale 的 tailnet 內網位址(`100.x.x.x` 這個 CGNAT 網段)連線**——這是刻意的安全性選擇(不把 SSH 暴露在公網上),但代表 GitHub Actions 的 runner(不在使用者的 tailnet 裡)沒辦法直接 SSH 過去。修正:`deploy.yml` 在 SSH 部署步驟之前,先用官方的 `tailscale/github-action` 讓 runner 臨時加入該 tailnet,之後才能用 Tailscale 位址連線;新增一個 GitHub Secret `TS_AUTHKEY`(Tailscale 的 reusable auth key,在 Tailscale admin console → Settings → Keys 產生)。`VPS_HOST` 這個既有 Secret 的值改填 Tailscale 位址(即 `100.123.0.19` 這種)而非公網 IP,其餘 SSH 部署邏輯不變。
  - **實作階段再更正(第一次實際部署嘗試後發現,診斷有誤)**:一開始只加了 `authkey` 參數,沒有加 `tags` 參數,猜測是這樣導致每次 workflow 執行都在 tailnet 留下永久節點(而非用完即焚),節點憑證過期變殭屍記錄,連線在 SSH 協定握手階段被斷開(`ssh: handshake failed: EOF`)。當時據此補上了 `tags: tag:ci` 這個參數。
  - **實作階段第三次更正(補上 `tags` 後重新部署,問題依舊,回頭查證該 action 原始碼才找到真正根因)**:直接查 `tailscale/github-action@v2` 的原始碼,發現關鍵判斷式其實是:
    ```bash
    if [ -n "${{ inputs['oauth-secret'] }}" ]; then
      TAILSCALE_AUTHKEY="${{ inputs['oauth-secret'] }}?preauthorized=true&ephemeral=true"
      TAGS_ARG="--advertise-tags=${{ inputs.tags }}"
    fi
    ```
    這個條件式測試的是 `inputs['oauth-secret']`(OAuth client 認證專用欄位)是否有值,**跟 `tags` 或 `authkey` 完全無關**。也就是說,用傳統 `authkey` 方式登入時,不管有沒有設定 `tags`,這整段 if 都不會執行——上一輪「補上 tags 參數」的修正方向從一開始就是錯的,`tags` 這個輸入在 authkey 模式下根本沒被用到。真正修正:改用 **OAuth client** 認證(`oauth-client-id` + `oauth-secret` 兩個輸入,取代 `authkey`),搭配的 GitHub Secrets 也從 `TS_AUTHKEY` 改為 `TS_OAUTH_CLIENT_ID`/`TS_OAUTH_CLIENT_SECRET`;ACL 的 `tagOwners` 宣告仍然需要(OAuth client 產生時要綁定一個已宣告的 tag)。這次教訓:對於行為不如預期的第三方 action,與其憑 log 片段猜測條件式測試的是哪個變數,應該直接去查該 action 對應版本的原始碼確認。
  - **實作階段第四次更正(改用 OAuth client 後,連線時收到 `403: calling actor does not have enough permissions to perform this function`)**:查證後確認 `tailscale/github-action` 底層邏輯是「用 OAuth client 動態產生一把 auth key,再用這把 key 執行 `tailscale up`」,所以 OAuth client 需要的權限是**「Auth Keys」類別底下的「Write」**,不是原先猜測的「Devices」權限,也不是介面上另一個容易選錯的「OAuth Keys」選項。此外,建立 OAuth client 時 MUST 明確指定它被允許套用的 tag(即 `tag:ci`),且這個值必須跟 `deploy.yml` 裡 `tailscale/github-action` 的 `tags` 輸入完全一致,否則一樣會被 API 拒絕。已更新 README 對應步驟的 scope 說明。
  - **實作階段第五次更正(`ssh: handshake failed: EOF` 真正根因:Tailscale SSH 攔截,不是防火牆)**:OAuth client 修好之後,「Connect to Tailscale」步驟本身成功,但後續 `appleboy/ssh-action` 部署仍以同樣的 `handshake failed: EOF` 失敗。排查過程:VPS 的 `journalctl -u ssh` 在失敗時間點附近完全沒有這次連線的紀錄 → 排除是 SSH 協定層問題(如 cipher/KEX 不相容);`sudo ufw status verbose` 顯示 `inactive` → 排除 VM 自己的防火牆;一度懷疑是 VPS 供應商(Linode)的 Cloud Firewall 預設 inbound drop 擋掉,但用 `tailscale ping` 診斷後發現這條連線走 **DERP relay**(非 P2P 直連)——relay 模式下雙邊都是各自對 DERP 伺服器發起 outbound 連線,回程流量對任何 stateful 雲端防火牆而言都是「既有連線的回應」,不會被 inbound drop 規則擋下,因此 Linode Firewall 這個假設其實是錯的,不需要加任何 inbound 規則。真正根因是在 runner 上改用原生 `ssh -vvv` 直連後才浮現:回應的 SSH server 軟體版本顯示為 `Tailscale`(不是 VPS 真正的 `sshd`),並在使用者驗證前送出 `tailscale: tailnet policy does not permit you to SSH to this node` 後關閉連線——代表 **Tailscale SSH 這個功能其實有啟用**,會攔截所有經 tailnet 介面打到 22 埠的連線,依照 ACL 的 `"ssh"` 區塊(`src: autogroup:member, dst: autogroup:self`)做存取檢查;`tag:ci` 這種 tagged 節點不算 `autogroup:member`,沒有規則涵蓋,預設拒絕。這也解釋了為何 VPS 的 sshd 完全沒有這次連線的紀錄(連線在到達真正 sshd 之前就被 Tailscale SSH 自己擋下),以及為何手動從已登入使用者帳號的裝置(WSL)測試會成功(那台裝置符合 `autogroup:member`)。先前在 Tailscale admin console「Machine Details」頁面沒看到 SSH 相關屬性、因此判斷 Tailscale SSH 未啟用,這個判斷其實是誤導的,以實際連線测试结果为准。修正:這個部署設計本來就是用專屬 deploy key 走一般 SSH 金鑰驗證,不需要 Tailscale SSH 這層以 Tailscale 身分為基礎的存取控制,直接在 VPS 上執行 `sudo tailscale set --ssh=false` 關閉即可,讓 tailnet 連線正常交給 VPS 真正的 sshd 處理。教訓:面對「連線建立但後續失敗」的問題,不能只靠防火牆/網路層的間接跡象(如 log 是否留痕)去猜測分層,原生協定客戶端的完整 verbose 輸出往往能直接暴露真正攔截連線的是哪個程式。
  - **實作階段最終更正(放棄 CI SSH 進 VPS,改用 watchtower 輪詢架構)**:`--ssh=false` 這個修正雖然解決了 handshake 問題,但後續評估「CI 主動 SSH 進 VPS」這個模式本身的安全性時,發現無論怎麼加固都有結構性的取捨:
    - 若讓 CI 直接用 deploy key(關掉 Tailscale SSH)或走 Tailscale SSH 的 ACL(幫 `tag:ci` 開規則、拿掉 deploy key),兩種都需要一個「能讓外部的 GitHub Actions runner 觸發 VPS 上執行任意/特定指令」的常駐機密存在 GitHub repo Secrets 裡。就算用雙埠 + `authorized_keys` 的 `command=` forced command 把 deploy key 限制到只能跑部署腳本,一旦攻擊者能讀到該 repo 的 GitHub Secrets(例如透過惡意 workflow、被投毒的第三方 action、repo 權限外洩),存在同一個 Secrets 空間裡的所有憑證(deploy key、Tailscale OAuth secret)會一起洩漏,個別加固措施能收斂單一憑證外洩後的傷害,但無法讓「CI 有能力觸發 VPS 執行指令」這件事本身消失。
    - 改為**移除 CI 對 VPS 的任何主動連線能力**:`deploy.yml` 只做 build + push image 到 GHCR(只需要 `GITHUB_TOKEN`,沒有任何自訂 secret),VPS 上改跑 [watchtower](https://containrrr.dev/watchtower/) 容器,定期(預設 5 分鐘)自己向 GHCR 查詢 `app` 服務用的 image 有沒有新版,有的話自己 `pull` + 重啟(透過 `WATCHTOWER_LABEL_ENABLE=true` + `app` 服務的 `com.centurylinklabs.watchtower.enable=true` label,只管理這一個容器,不動 `caddy`/`watchtower` 自己)。GitHub Secrets 裡不再需要任何能連進 VPS 的憑證,`tailscale/github-action`、`appleboy/ssh-action`、`VPS_HOST`/`VPS_USER`/`VPS_SSH_KEY`/`TS_OAUTH_CLIENT_ID`/`TS_OAUTH_CLIENT_SECRET` 全部移除;VPS 端也不再需要開放 Tailscale SSH 之外的任何額外 SSH 埠或 ACL 規則。
    - 取捨:部署不再是「打 tag 後幾秒內生效」,而是等 watchtower 下一次輪詢週期(可調 `WATCHTOWER_POLL_INTERVAL`);想立即生效可以自己在 VPS 上手動 `docker compose pull && docker compose up -d`。考量到這個部署本來就是刻意用「打 tag」而非「push 即部署」讓維護者控制時機(見上方 Non-Goals 與 Risks),幾分鐘的輪詢延遲跟這個既有取捨方向一致,不是新增的妥協。
    - 教訓:對「要不要讓自動化流程持有能連進正式環境的常駐憑證」這類問題,與其不斷加固憑證本身的存取範圍,有時候更好的方向是直接評估「這個能力是否真的必要」——這裡的答案是不必要,拿掉能力比把能力鎖得更緊更乾淨。
- **部署後健康檢查借用既有 `GET /api/meta`**:`docker-compose.yml` 的 `app` 服務設定 `healthcheck` 打這支既有端點,`deploy.yml` 在重啟後可以等待健康檢查通過再視為部署成功(不需要新增專門的 healthz 端點)。

## Risks / Trade-offs

- **重啟必定打斷進行中對局**:已在 Non-Goals 說明是接受的取捨;打 tag 觸發(而非每次 push)已經把「何時重啟」的控制權交回維護者,可以挑對局少的時間點發布。
- **單一行程的擴展性上限**:如果之後真的需要處理更大流量,現有房間狀態的記憶體內設計會是硬限制,屆時需要另外設計狀態外部化(如 Redis)——這次不處理,先讓「架得起來、能穩定跑」這件事成立。
- **GHCR 映像檔可見性**:若 repo 是 public,GHCR image 需另外在 package 設定裡調成 public,VPS 才能免登入 `docker pull`;若 repo 是 private,VPS 上需要一次性 `docker login ghcr.io`,watchtower 容器也要掛載同一份 `~/.docker/config.json` 才拉得到私有 image。這是操作面的一次性設置,記錄在 README,不是程式碼問題。
- **watchtower 輪詢延遲**:部署不是打 tag 後立即生效,而是等下一次輪詢週期(預設 5 分鐘,可調);換來的是 GitHub Secrets 裡不需要存在任何能連進 VPS 的常駐憑證。與既有的「打 tag 而非 push 即部署」精神一致(見上一條),接受這個延遲。
