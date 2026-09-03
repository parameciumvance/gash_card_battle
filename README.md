# 金色のガッシュベル!! THE CARD BATTLE — 對戰網頁

《魔法少年賈修 CCG》規則全自動裁決的同機雙人(hotseat)對戰網頁。
規則依據 [ref/raw/rule3.md](ref/raw/rule3.md),卡池為第一彈(Series 1 Level 1)全 67 種卡。

## 啟動

```bash
pip install -e ".[dev]"
uvicorn gash.api.app:app --reload
# 瀏覽器開 http://127.0.0.1:8000/
```

首頁四個入口:

- **本機測試模式**:兩人共用同一畫面輪流操作(全視角),雙方可各選牌組;附金手指面板,
  可直接編輯雙方的魔本頁面卡號與 MP,方便湊測試場面(見下)。
- **建立房間**:線上約戰。選擇回合計時(不限時/30/60/120 秒每動作)與自己的牌組後
  產生 6 碼房號、加入連結與觀戰連結;把加入連結傳給朋友,對方選好牌組即開局。
- **加入房間**:輸入朋友給的房號,選自己的牌組後加入。
- **牌組構築**:編排自己的 32 頁魔本(見下)。

## 牌組構築

魔本構築是**排版**:頁位=出牌時機、對頁=同時翻開的手牌、最後一頁的術費用為 0。
構築器以 16 個對頁呈現魔本,左側卡池(可依類型/對應魔物/收錄產品篩選,如 Level 1、The Best Booster 1):

- 點卡池的卡 → 放入選中頁位(或下一空頁);點頁位選中,再點另一頁位=移動/互換(也可拖拉);
  點選中的有卡頁位=移除。
- 七條構築規則即時提示(32 頁全滿、首頁魔物、末頁術、中級 12+、上級 22+、同號 ≤4、魔物 ≤8);
  違規的牌組可以儲存(標記不合法)但不能帶進對戰。伺服器在開局時仍會做最終驗證。
- 牌組存在瀏覽器(localStorage);「匯出牌組碼」產生一行 `gash1:...` 文字,
  可備份或貼給朋友,對方「匯入牌組碼」即得同一副。清瀏覽器資料前記得匯出。

預組「賈修+蒂歐+凱喬美」(`data/decks/level1.json`)永遠可選,也可作為構築起手複製。

### 新增一個預設牌組

預組是**資料驅動**的:伺服器啟動時掃描 `data/decks/*.json`,前端從 `GET /api/decks` 取得清單
動態生成選單。新增一個預組 = **丟一個 JSON 檔**(重啟伺服器後生效),不需改任何程式碼。

```jsonc
// data/decks/level3.json
{
  "id": "level3",                    // 唯一識別(建議同檔名)
  "name": "第三彈預組",              // 選單顯示名(最省:只寫這行)
  "pages": ["M-xxx", "S-xxx", ...]   // 32 頁卡號,須通過構築規則(首頁魔物、末頁術…)
}
```

- **顯示名**依序解析:`name_key`(經 i18n 字典 `frontend/i18n/zh-TW.json` 解析,可多語)→ 內嵌 `name` → `id`。
  只要在地化就加 `name_key` 並補各語系 i18n 條目;否則直接寫 `name` 即可。
- 檔案若無法通過構築驗證,啟動掃描時會被排除(記 log),不影響其他預組。
- 請求端只以 `{preset: <id>}` 指定,伺服器用 id 查掃描到的白名單載入,絕不轉為任意檔案路徑。

構築器左側卡池的「產品」篩選(如 Level 2)是依 `cards.json` 每張卡的 `sets` 欄自動產生的,
與預組無關 — 只要卡在卡池裡就能手動構築,新增預組只是多一個「開局即可選的完整 32 頁」捷徑。

線上模式規則與資訊視角:
- 自己永遠顯示在畫面下方;**對手翻開頁只顯示卡背與頁碼**(依原規則,使用時才展示;
  伺服器端過濾,前端拿不到資料)。E-014/M-011 的檢視效果只對使用者本人揭露內容。
- 斷線重連:重新整理頁面即自動續打(token 存於瀏覽器 localStorage)。
- 回合計時開啟時,逾時由伺服器代打安全動作(pass/不防禦/不保護等),不判負;
  行動記錄會標示「逾時代打」。
- 觀戰連結可分享給任意人數,觀戰者看不到任何一方的翻開頁內容。

限制:對局存在伺服器記憶體,**伺服器重啟即失局**;房間閒置 2 小時自動回收;無帳號與配對。

## 單機發行(給非開發者的玩家)

### 玩家怎麼用(三步驟)

1. **解壓** `gash-card-battle-vX-win64.zip` 到任意資料夾。
2. **(選配)放卡圖**:把另行取得的 `assets` 資料夾(內含 `cards/*.jpg`)放到
   `%LOCALAPPDATA%\gash-card-battle\assets`(首次啟動會自動建好這個資料夾;
   之後更新版本不必重放,所有版本共用)。沒放也能玩,缺圖卡面以卡背佔位。
3. **點兩下 `gash.exe`**:伺服器啟動、瀏覽器自動開啟。終端機會顯示
   `邀請網址:https://xxx.trycloudflare.com` — 建立房間後把「加入連結」
   貼給朋友(LINE/Discord),對方點連結、選牌組即開打,**什麼都不用裝**。

注意:邀請網址**每次啟動都不同**(像一次性的房號),關掉視窗即失效;
沒有網路或缺 `cloudflared.exe` 時自動降級為本機/區網模式,遊戲照常。

### 維護者怎麼打包

```bash
pip install -e ".[dev]"                       # 內含 pyinstaller
python tools/build_release.py                 # 於 Windows 上執行產出 win64 zip
# 選項:--cloudflared <路徑>(指定 cloudflared 執行檔;缺省找 PATH)
#       --skip-cloudflared(不附通道,發行物僅支援本機/區網)
```

產出 `dist/gash-card-battle-v{版本}-{平台}.zip`(~40MB,**不含卡圖**),
每版獨立解壓即用。cloudflared 至官方
[cloudflare/cloudflared releases](https://github.com/cloudflare/cloudflared/releases) 下載。
卡圖包 = 把 `frontend/assets/` 資料夾單獨壓縮另行發佈(內容含版權素材,請自行斟酌散布範圍)。

卡圖目錄的解析順序(第一個含 `cards/` 的目錄生效):
`GASH_ASSETS_DIR` 環境變數 → 執行檔旁 `assets/` → 使用者資料夾(上述)→ repo `frontend/assets/`。
開發環境可 `python -m gash.launcher` 走與發行版相同的啟動流程。

## VPS 部署(長期常駐、給不特定人玩)

跟上面的單機發行(給朋友臨時開一次)不同,這是把服務架在自己的 VPS 上長期開著。
流程是 push 一般 commit 只跑測試、打版號 tag 才建置映像檔並部署,平時不會打斷進行中的對局。

**已知限制**:房間狀態存在單一行程的記憶體裡,**服務 MUST 只跑單一 uvicorn 行程**,
不能開多個容器/多個 worker 分攤流量(那樣同一房間的請求可能被路由到沒有該房間資料的行程)。
**每次部署重啟容器,當下進行中的對局都會消失**——這也是為什麼用「打 tag」而非「每次 push」
觸發部署,方便你挑對局少的時間點發布。

### 一次性設置

以下每一步都標明要在**本機**(你自己平常用的電腦)還是 **VPS**(遠端伺服器)執行,
不要搞反——尤其是 SSH 金鑰那步,金鑰要在本機產生,私鑰不會、也不需要留在 VPS 上。

1. **(VPS)安裝 Docker**(Ubuntu 24.04):SSH 登入 VPS 後執行
   ```bash
   curl -fsSL https://get.docker.com | sh
   ```
   (內含 Docker Compose plugin,`docker compose` 指令即可使用,不需要另外裝 `docker-compose`。)

2. **(VPS)建立部署目錄**:
   ```bash
   mkdir -p /opt/gash-card-battle
   ```

3. **(本機)把 `docker-compose.yml` 與 `Caddyfile` 傳到 VPS 剛建立的目錄**(這兩個檔案在
   repo 根目錄,在你本機的 repo 資料夾下執行):
   ```bash
   scp docker-compose.yml Caddyfile youruser@your-vps-ip:/opt/gash-card-battle/
   ```
   VPS 上**不需要**整份 repo 原始碼,只需要這兩個檔案——服務本體是從 GHCR 拉映像檔運行的。

4. **(本機)產生一把只給部署用的 SSH 金鑰**(不要用你平常登入 VPS 的個人金鑰),
   並把公鑰送到 VPS:
   ```bash
   ssh-keygen -t ed25519 -f ~/.ssh/gash_deploy_key -C "gash-card-battle deploy-only"
   ssh-copy-id -i ~/.ssh/gash_deploy_key.pub youruser@your-vps-ip
   ```
   這兩行指令的 `youruser@your-vps-ip` 是**從本機連去 VPS**,執行時本機能連到 VPS 才會動;
   如果 `ssh-copy-id` 卡住沒反應,先確認你是在本機(不是在 VPS 上)執行這行指令。
   完成後 VPS 的 `~/.ssh/authorized_keys` 會多一行對應這把 deploy-only 金鑰的公鑰,
   可以 SSH 進 VPS 用 `cat ~/.ssh/authorized_keys` 確認(建議加上註解方便之後撤銷)。

   **`ssh-copy-id`/`ssh` 卡住的疑難排解**(這步最容易卡):
   - **卡在 `Connecting to ... port 22.` 沒有任何後續輸出**:通常是連不到這個位址。
     若 VPS 的 IP 長 `100.x.x.x`(Tailscale/CGNAT 位址),代表 VPS 的 SSH 只開放在
     Tailscale 內網——本機也要連上**同一個 tailnet** 才能連過去。若是用 **WSL** 執行這些
     指令,注意 WSL2 有自己獨立的網路(跟 Windows 宿主機分開),Windows 端裝了 Tailscale
     不代表 WSL2 也能連,WSL2 裡要另外裝一份(`curl -fsSL https://tailscale.com/install.sh
     | sh && sudo tailscale up`,用同一個帳號登入同一個 tailnet)。用 `tailscale status`
     確認本機真的是 Connected 狀態。
   - **能力 `ssh` 直接登入,但 `ssh-copy-id` 還是卡住**:通常是 VPS 關閉了密碼登入
     (`PasswordAuthentication no`)——`ssh-copy-id` 預設想先用密碼登入才能塞入新公鑰,
     VPS 不接受密碼就會卡住等一個不會出現的密碼提示。這時候跳過 `ssh-copy-id`,直接用
     你已經能登入的那把金鑰把公鑰內容接上去:
     ```bash
     cat ~/.ssh/gash_deploy_key.pub | ssh youruser@your-vps-ip "cat >> ~/.ssh/authorized_keys"
     ```

5. **在 GitHub repo 網頁的 Settings → Secrets and variables → Actions,切到 "Secrets"
   分頁(不是 "Variables" 分頁——Variables 是明文儲存,這幾個值都不該用)新增**:
   - `VPS_HOST`:VPS 的 IP 位址(見下方「若 VPS 的 SSH 只開放在 Tailscale 內網」)
   - `VPS_USER`:上一步用來登入 VPS 的使用者名稱
   - `VPS_SSH_KEY`:上一步在**本機**產生的**私鑰**內容(`~/.ssh/gash_deploy_key` 檔案全文,
     不是 `.pub` 那個公鑰檔)

   **若 VPS 的 SSH 只開放在 Tailscale 內網(沒有對公網開放,如 IP 長 `100.x.x.x`
   這種 CGNAT/Tailscale 位址)**:`VPS_HOST` 直接填這個 Tailscale 位址即可,但 GitHub
   Actions 的執行環境本身不在你的 tailnet 裡,`deploy.yml` 已經多加了一步用
   `tailscale/github-action` 讓 runner 臨時加入 tailnet,你只需要額外:
   - 到 [Tailscale admin console](https://login.tailscale.com/admin/settings/keys) →
     Settings → Keys,產生一把 **reusable** 的 auth key
   - 在 GitHub repo Secrets 多新增一欄 `TS_AUTHKEY`,值就是這把 auth key
   - 到 [Access Controls](https://login.tailscale.com/admin/acls/file) 編輯 ACL policy
     檔案,加入(或在既有 `tagOwners` 區塊裡補一行):
     ```json
     "tagOwners": {
       "tag:ci": ["autogroup:admin"],
     },
     ```
     **這步不能省略**——`deploy.yml` 裡的 `tailscale/github-action` 帶了 `tags: tag:ci`
     這個參數,用意是讓每次 workflow 建立的節點標記為 ephemeral(用完即焚)並自動核准;
     如果 tailnet 沒有先宣告這個 tag,`tailscale up` 會失敗。沒設定這步的後果是:
     每次部署都會在 Tailscale admin console 的 Machines 清單留下一個**永久節點**,
     過一段時間憑證到期變成 `Expired` 殭屍記錄,實際連線會在 SSH 握手階段失敗
     (`ssh: handshake failed: EOF`)——這是實際部署時踩過的坑,如果你已經累積了幾台
     `github-xxxxx` 的過期機器,可以到 Machines 頁面手動刪除清掉。

6. **確認 GHCR 映像檔可被 VPS 拉取**:如果 repo 是 public,建置後第一次要到
   `https://github.com/<你的帳號>?tab=packages` 把對應的 package 設為 public,
   之後 VPS `docker compose pull` 才不需要登入;如果 repo 是 private,要 SSH 進 **VPS**
   先 `docker login ghcr.io`(用一組有 `read:packages` 權限的 Personal Access Token)。

### 發布新版本

**(本機)** 在 repo 資料夾下打 tag 並推上 GitHub:
```bash
git tag v0.1.0
git push origin v0.1.0
```

推 tag 後 GitHub Actions 會自動建置映像檔、推上 GHCR、SSH 進 VPS 執行
`docker compose pull && docker compose up -d`(這段是 CI 自動做的,你不用手動登入 VPS)。
可以到 repo 的 Actions 頁面看執行進度。

### 之後補上網域

**(本機)** 把 `Caddyfile` 裡的 `:80` 改成你的網域(如 `example.com`),
`scp Caddyfile youruser@your-vps-ip:/opt/gash-card-battle/` 覆蓋過去;
**(VPS)** 再執行 `docker compose restart caddy`——Caddy 會自動申請並續期 HTTPS 憑證,
不需要另外裝 certbot 或手動管理憑證,前端也不用改(WebSocket 連線本來就是依當下的
`http`/`https` 自動切換成 `ws`/`wss`)。

### 卡圖

`docker-compose.yml` 已經預留一個 volume 掛到 `GASH_ASSETS_DIR`,但這次沒有處理實際
怎麼把卡圖檔案放進這個 volume——照單機發行的提醒,卡圖含版權素材,請自行斟酌散布範圍。

## 測試

```bash
python -m pytest        # 引擎規則、67 張卡逐卡效果、API 整合、整局劇本
```

## 專案結構

```
src/gash/
  paths.py              資源目錄解析單點(開發/凍結佈局、卡圖搜尋順序)
  launcher.py           單機啟動器(uvicorn + cloudflared 通道 + 開瀏覽器)
  engine/               純 Python 遊戲引擎(無 IO,指令進 → 事件出)
    state.py            狀態模型:魔本頁序、MP、魔物槽、modifier、待命、戰鬥子狀態
    engine.py           規則主體:階段流程、輪流行動權、戰鬥五步驟、傷害/保護、勝敗
    cards.py / deck.py  卡片定義載入、魔本構築合法性驗證
    effects/            效果系統
      registry.py       引擎 ↔ 卡片效果的掛鉤介面
      primitives.py     效果原語(加魔力、禁止旗標、待命、互動式硬幣…)
      mamodo.py / partners.py / events.py / spells.py   逐卡 handler
  api/
    app.py              FastAPI:房間端點、指令轉發、WebSocket 推送、逾時代打
    rooms.py            房間模型、token 身分、計時器(等待者推導與安全預設指令)
    views.py            視角過濾:snapshot(game, viewer) 與事件過濾(資訊不外洩的單點)
frontend/               無框架靜態前端(中文 UI,文字全走 i18n 字典)
  i18n/zh-TW.json       介面文字與行動記錄模板
  assets/cards/         卡圖(缺圖時自動以文字卡面呈現)
data/
  cards_ja.csv          日文權威來源(atwiki 抓取結果),cards.json 的轉換輸入
  cards.json            卡片結構化數值資料(由 cards_ja.csv 轉換,日文為準)
  cards.zh-TW.json      卡片中文文本(卡名/效果),獨立於數值、可自由校對
  decks/level1.json     預組魔本(32 頁)
tools/
  scrape_ja_effects.py  atwiki 日文權威資料抓取 → data/cards_ja.csv
  build_cards_json.py   cards_ja.csv → cards.json 轉換
  download_images.py    卡圖批次下載(Google Drive,支援續抓與失敗清單)
  build_release.py      發行打包(PyInstaller onedir → 單一 zip,不含卡圖)
```

## 資料管線

1. `python tools/scrape_ja_effects.py` 抓取 atwiki.jp 日文權威頁面,輸出 `data/cards_ja.csv`。
2. `python tools/build_cards_json.py` 將 `data/cards_ja.csv` 轉換為 `data/cards.json`;
   `image_url`/`sets` 沿用轉換前既有 `data/cards.json` 的舊值(新卡無舊值可沿用時為空)。
3. `python tools/download_images.py` 批次下載卡圖至 `frontend/assets/cards/{卡號}.jpg`;
   已存在自動跳過,失敗清單寫入 `_failed.txt`,缺圖不影響遊戲。

## 翻譯校對

卡片中文文本集中在 `data/cards.zh-TW.json`,以卡號為 key:

```json
"S-001": {"name": "薩喀爾", "name_ja": "ザケル", "attr": "雷", "effect": "…"}
```

改動此檔只影響顯示,不影響任何遊戲邏輯;介面用語則在 `frontend/i18n/zh-TW.json`。
未來新增語言 = 並列新增 `cards.<lang>.json` 與 `i18n/<lang>.json`。

## 架構備註

- 後端為權威伺服器:規則、隨機數、狀態、資訊過濾全在伺服器;前端只渲染視角化快照與送指令。
- 身分 = token:指令帶 `X-Player-Token`,伺服器由 token 決定玩家,payload 自報身分無效。
- 事件流帶全域序號:`GET /api/rooms/{code}/events?since=N` 增量同步(同樣經視角過濾),
  WebSocket 推送與 HTTP 回應以序號冪等,斷線重連即補齊。
- 視角過濾收斂在 `api/views.py` 單點:未翻開頁對所有人保密、翻開頁只對持有者可見、
  決策選項只送決策者、觀戰為純公開視角。引擎完全不知道「視角」存在。
