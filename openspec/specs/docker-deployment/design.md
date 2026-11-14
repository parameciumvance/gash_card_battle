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
- **相依鎖定**(ci-supply-chain):相依依 `requirements.lock`(pip-compile,帶 hash,含建置用的 setuptools)以 `--require-hashes` 安裝,專案本身 `--no-deps --no-build-isolation -e .`;基底映像檔以 digest 指定。理由:原本打 tag 當下才解析版本,PyPI 上當時有什麼就上線什麼、事後也無法重現;`-e .` 的建置隔離還會另外下載沒有 hash 的 setuptools。

## 單一行程

房間狀態只存在單一行程的記憶體,沒有外部儲存。服務 MUST 只跑一個 uvicorn 行程,不能多 worker 或多 replica,否則同一房間的請求可能落到沒有該房間資料的行程。因此每次重啟 `app`,進行中的對局都會消失。

## 發布與更新

- CI 只在推送 `v*` tag 時建置映像檔並推上 GHCR(標上版號與 `latest`),一般 push 只跑測試。
- **CI 測試**(ci-full-suite):`test.yml` 在 push / PR 到 `main`、`dev` 時執行全套,含瀏覽器測試(安裝 `chromium-headless-shell`;原本沒有安裝,`browser` fixture 啟動失敗而整批略過,CI 綠燈只代表引擎與 API)。Python 3.14 與 production 映像檔、開發容器相同(python-314:原本 CI 與正式站 3.12、開發容器 3.14,本機用到新版寫法要到 CI 才發現;改為一致升到 3.14。`requires-python` 仍為 `>=3.12`,3.12 下全套亦通過)。`cache: pip`、依 playwright 版本快取 `~/.cache/ms-playwright`(系統套件每次 apt 安裝);`concurrency` 以 `test-<ref>` 分組、取消同分支的舊執行;`timeout-minutes: 30`(平常約 10 分鐘,字型套件的鏡像站偶爾很慢)。
- **發布前的測試關卡**:`deploy.yml` 的 `test` job 以 `workflow_call` 呼叫同一份 `test.yml`,`build-and-push` 設 `needs: test`。兩邊用同一份定義,不會漏改;不採「查詢該 commit 的 Test 結果」,因為 tag 可能打在沒有對應 Test 執行的 commit 上。被呼叫時 `github.ref` 是 tag,concurrency 各自一組,不會取消別的發布。
- **失敗截圖**:`tests/conftest.py` 的 `pytest_runtest_makereport` 在瀏覽器測試本體失敗時,截下 `browser` 所有 context 的頁面到 `test-results/`(fixture 尚未 teardown,頁面都還開著);`test.yml` 失敗時上傳為 artifact,保留 7 天。
- **權限與釘版本**(ci-supply-chain,2026-11-11 盤點):repo 的預設 workflow 權限為唯讀;`test.yml` 宣告 `contents: read`(被 `workflow_call` 呼叫時也不會超過),`deploy.yml` 預設 `permissions: {}`,只有 `build-and-push` 可寫入。第三方 action 以 commit SHA 引用、註解版本號;CI 依 `requirements-dev.lock` 安裝。Dependabot 每週為 action、pip、Dockerfile、compose 開分組 PR 到 `dev`。守門測試 `tests/test_ci_supply_chain.py`。
  - 理由:原本預設權限可寫入、`test.yml` 沒有宣告,每次 push 時未鎖版本的相依與第三方 action 都以可推 GHCR 的 token 執行,任一環節被入侵即可推映像檔,由 watchtower 自動上線,不必等打 tag。
- VPS 端由 watchtower 每 300 秒輪詢,有新版就拉取並重啟該容器。CI 不持有任何能連進 VPS 的憑證(SSH 金鑰、VPN 授權)。
  - 理由:只要 CI 有能力觸發 VPS 執行指令,Secrets 外洩時這個能力就會一起外洩,加固憑證只能縮小傷害範圍。直接拿掉這個能力,外洩時最多只能推一個惡意映像檔到 registry。代價是部署要等下一次輪詢。
- `app` 只在打 tag 時才有新版,維護者藉此挑對局少的時間發布(重啟會讓對局消失)。
- **更新內容與 GitHub Release**:`deploy.yml` 在建置前執行 `tools/release_notes.py check <tag>`,更新內容(`frontend/i18n/releases.zh-TW.json`)的最新一版必須等於 tag,否則不建置,線上維持原版本。映像檔推送後以 `markdown <tag>` 的輸出(繁中)執行 `gh release create`,工作需要 `contents: write`(另有 `packages: write` 推 GHCR)。
  - 要求「最新一版 = tag」而非「存在該版」:新版本一定寫在最前面,tag 打錯成舊版號時也會擋下。
  - 檢查放在 deploy 而非 test:一般 push 時還沒有 tag,無從比對。
  - Release 在推送之後才建立:建立失敗(權限、網路)不影響部署,可用同一個工具的輸出手動補建。
  - 工具只用標準函式庫,CI 不必安裝專案依賴;映像檔不含 `tools/`,工具只在 CI 用。
- watchtower 本身以版本與 digest 指定,不自動更新(ci-supply-chain):它掛載 Docker socket,等於 VPS 的 root 權限。升級由 Dependabot 的 PR 提醒;VPS 的 compose 檔是手動複製的快照,合併後要重新 `scp` 並 `docker compose up -d watchtower`。
- `cloudflared` 使用 `latest`,有新版就自動更新,容器內關閉它自己的更新機制(`--no-autoupdate`)。
  - 2026-11-11 盤點後使用者決定維持自動更新(讓 Cloudflare 的修正自動套用),不釘版本。
  - 理由:重啟 `cloudflared` 不會重啟 `app`,房間狀態保留,前端的 WebSocket 斷線後 1.5 秒自動重連並由 `welcome` 取回完整狀態,所以不需要挑時間;不更新反而會逐漸落後於 Cloudflare 支援的版本。新版有問題時,把 image 改釘到上一個正常的版本。

## 版本號

- 版本號就是觸發部署的 tag 名稱:`deploy.yml` 以 `build-args: GASH_VERSION=${{ github.ref_name }}` 傳入,`Dockerfile` 的 `ARG` / `ENV` 存成環境變數(映像檔裡沒有 `.git`,不能執行 `git describe`)。沒有傳入時為 `dev`。
- 首頁顯示版本號,部署後可以直接確認新版是否上線(見 `battle-api/design.md`)。
- Cloudflare 的 Browser Cache TTL 須設為 Respect Existing Headers:預設會把 JS / CSS 的 `Cache-Control` 改寫成 `max-age=14400`,蓋掉來源的 `no-cache`,瀏覽器會沿用舊檔最多 4 小時。這是 Cloudflare 後台的設定,不在 repo 中。

## 對外服務

- **Cloudflare Tunnel**:`cloudflared` 主動向 Cloudflare 建立 outbound 連線,VPS 不需要為網頁服務開放任何 inbound 埠。TLS 在 Cloudflare 邊緣終止,VPS 不做憑證管理。
- **不發布埠**:Docker 發布的埠會直接寫入 iptables、繞過 `ufw`。不發布埠就不需要依賴主機防火牆設定正確;供應商的雲端防火牆也不開放 80 / 443,作為第二層防護。
- **遠端管理的通道**:通道與轉送規則(`card-battle.zatchholic.com` → `http://app:8000`)設定在 Cloudflare Zero Trust 後台,VPS 只需要一組 token。只有一條轉送規則,放進版本控制的價值不大;規則內容記在 README。
- **token**:只放在 VPS 部署目錄的 `.env`(權限 600,`.gitignore` 已排除)。compose 以 `${TUNNEL_TOKEN:?...}` 取值,沒設定時 `docker compose` 在解析設定階段就失敗,不會啟動一個連不上的連接器。
- **WebSocket**:`uvicorn[standard]` 每 20 秒送一次 ping,閒置中的對局連線不會被切斷;萬一被切斷,前端會自動重連。
- **連線端 IP**:`app` 看到的來源都是 `cloudflared` 容器。目前沒有功能使用玩家 IP,所以沒有開啟 uvicorn 的 `--proxy-headers`;之後若需要(例如依 IP 限流),應改讀 Cloudflare 的 `CF-Connecting-IP`。
- **HTTP 導向 HTTPS**:由 Cloudflare 的 Always Use HTTPS(或只針對此網域的 Redirect Rule)負責,不在 repo 的設定裡。前端依頁面協定選擇 `ws` / `wss`,分享連結取自 `location.origin`,所以應用程式不需要知道自己的公開網址。

## 維運腳本(`tools/vps.py`)

開發移回本機後,VPS 只跑正式站;補卡圖、發布 / 撤下公告、查看狀態改由本機的 `tools/vps.py` 經 ssh 執行(2026-11-05,`vps-ops-script`)。

- **連線**:`ssh -o BatchMode=yes <GASH_VPS> "cd <GASH_VPS_DIR> && docker compose ..."`,預設 `dev@dev-vps`、`/opt/gash-card-battle`。`dev-vps` 走 Tailscale SSH,由 tailnet ACL 授權,repo 與 dev container 都不放 ssh 金鑰。BatchMode 讓 ssh 不會停下來問密碼或主機金鑰——互動提示會吃掉 stdin 上串流的資料。
  - 這與「CI 不持有能連進 VPS 的憑證」不衝突:腳本只在維護者本機、以維護者的 tailnet 身分執行,CI 仍然碰不到 VPS。
- **進容器操作 volume**:一律 `docker compose exec -T app`,不依賴 volume 在主機上的路徑(`/var/lib/docker/volumes/...` 需要 root)。`app` 以 root 執行、映像檔有 `tar`。
- **串流,不留暫存檔**:卡圖由本機打成 tar 寫進 ssh 的 stdin,容器內 `tar -x`(擁有者設為 1000:1000,與 `cards/` 目錄相同);公告以 `cat > announcement.json.tmp && mv` 替換。暫存檔與目標在同一個目錄,`mv` 是原子的,伺服器每次請求即時讀檔也不會讀到一半。原本的 `scp` 到 `/tmp` 再 `docker compose cp` 要兩次連線並留下暫存檔,保留在 README 作為備案。
- **卡圖只比對檔名**:換圖用 `--force <卡號>`。每次比對雜湊要在遠端讀 300 多個檔案,卡圖很少換,不值得。只在 VPS 上的卡不刪。
- **公告驗證與伺服器共用**:`src/gash/announcement.py` 的 `parse_announcement` 同時給 `read_announcement`(伺服器)與腳本使用,兩邊對「會不會顯示」的判定不會分歧。`announcement_warnings` 的提醒(缺語言、佔位文字、與 `zh-TW` 相同、`until` 沒有時區)只在發布前使用,不影響伺服器。
  - 理由:10/12 的公告 `zh-CN` 是 `"123"`、`en` / `ja` 是 `"..."`,格式合法、伺服器照樣顯示;格式錯誤或 `until` 已過時伺服器默默視為沒有公告,發布的人不會知道。
  - 腳本因此要 import `gash`,只能在裝好專案的環境執行;與 `tools/release_notes.py`(CI 裸跑、只用標準函式庫)不同。
- **發布後確認**:查詢公開網域的 `/api/announcement` 比對 `id`,同時確認了檔案位置、伺服器讀檔、通道與 Cloudflare。`/api/*` 不是 Cloudflare 預設快取的副檔名。
