# 金色のガッシュベル!! THE CARD BATTLE — 對戰網頁

《魔法少年賈修 CCG》規則全自動裁決的對戰網頁:線上約戰、NPC 對戰與本機雙人測試。
卡池為第一、二彈共 135 種卡;玩法說明見遊戲內的「規則」頁。
規則以 `openspec/specs/game-engine` 的規格為準(開發時參考的規則書中譯 `ref/raw/rule3.md` 不在 repo 內)。

> 非官方粉絲專案,與原作者及 BANDAI 無關,亦未經授權;免費且不涉商業行為。
> 作品與卡片相關權利屬於雷句誠、BANDAI 及各權利人;權利人如有疑慮,請透過 [GitHub issue](https://github.com/parameciumvance/gash_card_battle/issues) 或遊戲內的「意見回報」聯絡。

## 啟動

```bash
pip install -e ".[dev]"
uvicorn gash.api.app:app --reload
# 瀏覽器開 http://127.0.0.1:8000/
```

首頁五個入口。三種對戰點進去後先到各自的設定頁選暱稱、牌組等,再開始;設定頁會記住上次選的牌組、難度與計時。

- **NPC 對戰**:和伺服器上的電腦對手對戰,即開即玩、不計時,也附金手指面板。
  可選 NPC 的牌組(任一預組、自己儲存的牌組,或「隨機」;隨機抽到哪副要到對局結束才公開)與難度:
  - **一般**:模擬每個可行的行動再評估局面後出手;看不到你的翻開頁,也不會預知擲幣。
  - **木人樁**:永遠不翻頁、pass、不防禦,搭配金手指擺好盤面來測試效果很方便。
- **與朋友對戰**:線上約戰,設定頁上方切換「建立房間」或「加入房間」。
  - 建立房間:選擇回合計時(不限時/30/60/120 秒每動作)與自己的牌組後,產生 6 碼房號、加入連結與觀戰連結;
    把加入連結傳給朋友,對方開啟後會直接進入加入畫面(房號已填好),選好牌組按加入即開局。
  - 加入房間:輸入朋友給的房號,選自己的牌組後加入。
- **本機測試模式**:兩人共用同一畫面輪流操作(全視角),雙方可各選牌組;附金手指面板,
  可直接編輯雙方的魔本頁面卡號與 MP,方便湊測試場面(見下)。
- **牌組構築**:編排自己的 32 頁魔本(見下)。
- **規則**:遊戲規則與卡面圖示說明(依本遊戲實際採用的規則撰寫)。對局中也能從頂欄的「規則」打開;
  點畫面中央的時機指示、或行動欄提示旁的「?」,會直接跳到對應的段落。

**語言**:介面支援中文、English、日本語。第一次開啟時依瀏覽器語言決定(日文 → 日本語、中文 → 中文、其他 → English),
之後可隨時點頂欄的「🌐」切換,選擇記在瀏覽器;對局中切換會重新載入並接回原對局,同房的玩家可各用不同語言。
日文與英文為**初版翻譯,尚未經母語者校對**。英文的卡片效果文是**依日文效果文翻譯**的,
與卡圖(民間英譯版)或 TTS 卡表上的英文不完全相同——遊戲行為依日文效果文,畫面上的文字與行為一致,以畫面為準。

## 牌組構築

魔本構築是**排版**:頁位=出牌時機、對頁=同時翻開的手牌、最後一頁的術費用為 0。
構築器以 16 個對頁呈現魔本,左側卡池(可依類型/對應魔物/收錄產品篩選,如 Level 1、The Best Booster 1):

- 點卡池的卡 → 放入選中頁位(或下一空頁);點頁位選中,再點另一頁位=移動/互換(也可拖拉);
  點選中的有卡頁位=移除。
- 七條構築規則即時提示(32 頁全滿、首頁魔物、末頁術、中級 12+、上級 22+、同號 ≤4、魔物 ≤8);
  違規的牌組可以儲存(標記不合法)但不能帶進對戰。伺服器在開局時仍會做最終驗證。
- 牌組存在瀏覽器(localStorage);「匯出牌組碼」產生一行 `gash1:...` 文字,
  可備份或貼給朋友,對方「匯入牌組碼」即得同一副。清瀏覽器資料前記得匯出。

預組「LEVEL:1 紅書與魔鬼」(`data/decks/level1.json`)永遠可選,也可作為構築起手複製。

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

- **顯示名**:`GET /api/decks` 回傳 `name_key` 與 `name`;前端以 `name_key` 依目前語言查字典,
  字典沒有時用 `name`(伺服器依序以中文字典解析 `name_key` → 內嵌 `name` → `id`)。
  要在地化就加 `name_key` 並在三種語言的 i18n 字典補條目;否則直接寫 `name` 即可。
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

## VPS 部署(長期常駐、給不特定人玩)

把服務架在自己的 VPS 上長期開著。
流程是 push 一般 commit 只跑測試、打版號 tag 才建置映像檔並推上 GHCR,平時不會打斷
進行中的對局。**CI 只負責 build + push image,不會、也不需要連進 VPS**——VPS 上跑一個
[watchtower](https://github.com/nicholas-fedor/watchtower)(原 `containrrr/watchtower` 已於
2025-12-17 封存,改用社群接手維護的分支)容器,定期自己檢查 `app` 與 `cloudflared` 的
映像檔有沒有新版、有的話自動拉取重啟。這樣 GitHub 那邊完全不需要任何能連進 VPS 的憑證
(不用 SSH 金鑰、不用 VPN/Tailscale),外洩風險最高也就是能推一個惡意 image 上你的
registry,碰不到 VPS 的網路邊界。代價是部署不是「打 tag 後幾秒內生效」,而是等
watchtower 下一次輪詢(預設 5 分鐘)。

**對外連線走 Cloudflare Tunnel**:VPS 上的 `cloudflared` 容器主動向 Cloudflare 建立連線,
玩家連 `https://card-battle.zatchholic.com` 的請求經這條通道轉到 `app`。compose 裡沒有任何
服務發布埠,VPS 不需要為網頁服務開放任何 inbound 埠,HTTPS 憑證也由 Cloudflare 處理。
代價是不能再用 VPS 的 IP 直接連線,服務可用性也依賴 Cloudflare。

**已知限制**:房間狀態存在單一行程的記憶體裡,**服務 MUST 只跑單一 uvicorn 行程**,
不能開多個容器/多個 worker 分攤流量(那樣同一房間的請求可能被路由到沒有該房間資料的行程)。
**每次部署重啟 `app` 容器,當下進行中的對局都會消失**——這也是為什麼用「打 tag」而非
「每次 push」觸發建置,方便你挑對局少的時間點發布。`cloudflared` 重啟則不影響對局,
前端會自動重連。

### 一次性設置

1. **(VPS)安裝 Docker**(Ubuntu 24.04):SSH 登入 VPS 後執行
   ```bash
   curl -fsSL https://get.docker.com | sh
   ```
   (內含 Docker Compose plugin,`docker compose` 指令即可使用,不需要另外裝 `docker-compose`。)

2. **(VPS)建立部署目錄**:
   ```bash
   mkdir -p /opt/gash-card-battle
   ```

3. **(Cloudflare)建立通道**(`zatchholic.com` 的 DNS 已在 Cloudflare):
   1. Cloudflare 後台 → Zero Trust → Networks → Tunnels → Create a tunnel,類型選
      **Cloudflared**,名稱自訂(如 `gash-card-battle`)。後台選單名稱偶有調整,找不到時搜尋「Tunnels」。
   2. 安裝連接器的頁面會顯示一段含 token 的指令,**只複製 token**(`eyJ` 開頭那一長串)。
      不用在 VPS 上照它的指令安裝,連接器由 compose 的 `cloudflared` 容器執行。
   3. 新增 Public Hostname:Subdomain `card-battle`、Domain `zatchholic.com`、
      Service Type `HTTP`、URL `app:8000`。Cloudflare 會自動建立 `card-battle` 的 CNAME 記錄;
      若 DNS 裡已經有同名的 A 記錄,先刪掉。

4. **(VPS)寫入通道 token**:用 `read -s` 輸入,token 不會留在 shell history,
   `umask 077` 讓 `.env` 一建立就只有自己能讀:
   ```bash
   cd /opt/gash-card-battle
   (umask 077; read -rsp 'Tunnel token: ' t; echo; printf 'TUNNEL_TOKEN=%s\n' "$t" > .env)
   ```
   `.env` 只放在 VPS,不要 commit(repo 的 `.gitignore` 已排除)。沒有 `.env` 時
   `docker compose` 會直接報錯,提示缺少 `TUNNEL_TOKEN`。

5. **(本機)把 `docker-compose.yml` 傳到 VPS 剛建立的目錄**(在你本機的 repo 資料夾下執行):
   ```bash
   scp docker-compose.yml youruser@your-vps-ip:/opt/gash-card-battle/
   ```
   VPS 上**不需要**整份 repo 原始碼,只需要這個檔案和上一步的 `.env`——服務本體是從
   GHCR 拉映像檔運行的。

   **這份是手動複製過去的快照,repo 更新不會自動同步。** 之後如果又改了
   `docker-compose.yml`(例如新增服務、調整設定),記得重新 `scp` 覆蓋過去,並在
   **(VPS)** 執行 `docker compose up -d` 套用——單純 `docker compose pull` 只會拉新的
   image,不會套用 compose 檔案本身的變更(新增的服務不會自己冒出來)。

6. **確認 GHCR 映像檔可被 VPS 拉取**:如果 repo 是 public,建置後第一次要到
   `https://github.com/<你的帳號>?tab=packages` 把對應的 package 設為 public,
   之後 `docker compose pull`/watchtower 才不需要登入就能拉;如果 repo 是 private,
   要 SSH 進 **VPS** 先 `docker login ghcr.io`(用一組有 `read:packages` 權限的
   Personal Access Token)——這組憑證會存在 `~/.docker/config.json`,watchtower 容器
   要拉私有 image 也得用到它,把 `docker-compose.yml` 裡 `watchtower` 服務下方那行
   註解掉的 `- ${HOME}/.docker/config.json:/config.json:ro` 取消註解即可
   (compose 檔案不會展開 `~`,MUST 用 `${HOME}` 或絕對路徑)。

7. **(VPS)啟動服務**:
   ```bash
   cd /opt/gash-card-battle
   docker compose up -d
   docker compose logs -f cloudflared   # 出現 Registered tunnel connection 表示通道已連上
   ```
   Cloudflare 後台的通道狀態變成 HEALTHY 後,就能開 `https://card-battle.zatchholic.com`。
   之後平常不需要手動介入,watchtower 會自己偵測新版並更新 `app` 與 `cloudflared`
   (`watchtower` 自己不受它管理,只有貼了 label 的服務會被更新)。

8. **(雲端主控台)防火牆**:VPS 供應商的防火牆(如 Linode Cloud Firewall)**不需要開放 80 / 443**,
   已經開放的規則可以刪掉。`cloudflared` 只需要對外連線(outbound 7844 埠),防火牆預設允許
   outbound 的話不用另外設定。

### 發布新版本

**(本機)** 在 repo 資料夾下打 tag 並推上 GitHub:
```bash
git tag v0.1.0
git push origin v0.1.0
```

推 tag 後 GitHub Actions 會自動建置映像檔並推上 GHCR,可以到 repo 的 Actions 頁面看
執行進度。VPS 上的 watchtower 最慢 5 分鐘內會偵測到新版自動更新;想立刻生效,
**(VPS)** 手動執行 `docker compose pull && docker compose up -d` 也可以。

tag 名稱就是版本號:CI 以 build arg `GASH_VERSION` 帶進映像檔,首頁免責聲明下方會顯示
「版本 v0.1.0」,意見回報的環境資訊也會帶上 `ver=v0.1.0`。部署後看首頁的版本號,就能確認
新版是否已經上線。開發環境顯示當下的 `git describe`。

前端檔案帶 `Cache-Control: no-cache`,但 Cloudflare 的 **Browser Cache TTL** 預設會把
JS / CSS 改寫成快取 4 小時。請在 Cloudflare 後台 Caching → Configuration →
Browser Cache TTL 設為 **Respect Existing Headers**,部署後玩家才會立刻拿到新版。

### 網域與 Cloudflare Tunnel

服務網址是 `https://card-battle.zatchholic.com`。轉送規則(Public Hostname →
`HTTP` / `app:8000`)設定在 Cloudflare 後台,不在 repo 裡;要換網域或新增網址都在後台改,
VPS 不用動。前端也不用改:WebSocket 依頁面協定自動使用 `wss`,分享連結取自目前的網址。

- **建議開啟 Always Use HTTPS**(Cloudflare → `zatchholic.com` → SSL/TLS → Edge Certificates),
  讓 `http://` 自動導向 `https://`,否則從 `http://` 進來的玩家連 WebSocket 也會走明碼的 `ws://`。
  這是整個 `zatchholic.com` 的設定;如果其他子網域需要明碼 HTTP,改用只針對
  `card-battle.zatchholic.com` 的 Redirect Rule(HTTP 導向 HTTPS)。
- **懷疑 token 外洩時**:拿到 token 的人可以用這條通道跑自己的連接器、分走流量。到 Cloudflare
  後台替通道重新產生 token(或刪掉通道重建),再依「一次性設置」第 4 步更新 `.env`,
  **(VPS)** 執行 `docker compose up -d` 讓 `cloudflared` 以新 token 重建。
- **`cloudflared` 自動更新後出問題時**:把 `docker-compose.yml` 裡的
  `cloudflare/cloudflared:latest` 改成上一個正常版本的 tag(版本號見 Docker Hub 的
  `cloudflare/cloudflared`),再執行 `docker compose up -d`。釘選版本後就不會再自動更新,
  問題排除後記得改回 `latest`。
- 伺服器看到的連線來源都是 `cloudflared` 容器。目前沒有功能用到玩家 IP;之後若需要
  (例如依 IP 限流),改讀 Cloudflare 的 `CF-Connecting-IP` 標頭。

### 從 Caddy 版遷移

舊版部署是 `caddy` 反向代理、發布 80 埠、以 VPS 的 IP 連線。遷移過程不會重啟 `app`,
進行中的對局不受影響。

1. 完成「一次性設置」的第 3、4 步(建立通道、寫入 `.env`)。
2. **(本機)** `scp docker-compose.yml youruser@your-vps-ip:/opt/gash-card-battle/`。
3. **(VPS)** `docker compose up -d --remove-orphans`:`caddy` 被移除、`cloudflared` 啟動;
   `app` 的設定沒有變,不會被重建。
4. 開 `https://card-battle.zatchholic.com`,實際建一間線上房間確認對戰正常。
5. 收尾:
   - 依「一次性設置」第 8 步刪掉防火牆的 80 / 443 規則,從外部確認 VPS 的 IP 已經連不上。
   - **(VPS)** `rm Caddyfile`;`docker volume ls` 找出名稱以 `caddy-data`、`caddy-config`
     結尾的 volume,用 `docker volume rm` 刪掉。

**回退**(在刪掉 Caddy 的 volume 之前都可以直接回退):在本機 repo 取出遷移前的
`docker-compose.yml` 與 `Caddyfile`,傳上 VPS 後重新套用,並重新開放防火牆的 80 埠:
```bash
# 本機:刪除 Caddyfile 的 commit 的前一版
c=$(git log -1 --format=%H -- Caddyfile)^
mkdir -p /tmp/gash-rollback
git show "$c:docker-compose.yml" > /tmp/gash-rollback/docker-compose.yml
git show "$c:Caddyfile" > /tmp/gash-rollback/Caddyfile
scp /tmp/gash-rollback/* youruser@your-vps-ip:/opt/gash-card-battle/
# VPS
docker compose up -d --remove-orphans
```

### 卡圖

`docker-compose.yml` 已經預留一個 volume(`card-assets`)掛到 `GASH_ASSETS_DIR`
(`/app/assets`),服務會從 `/app/assets/cards/{卡號}.webp` 讀圖。映像檔不含卡圖,也不含
`tools/`,所以要在本機下載後再傳上去。卡圖含版權素材,請自行斟酌散布範圍。

1. **(本機)下載卡圖**:

   ```bash
   python tools/download_images.py    # 產出 frontend/assets/cards/*.webp,支援續抓(需先裝 .[dev])
   ssh youruser@your-vps-ip mkdir -p /tmp/cards
   scp frontend/assets/cards/*.webp youruser@your-vps-ip:/tmp/cards/
   ```

2. **(VPS)複製進 `app` 容器的 volume**(在 `/opt/gash-card-battle` 目錄下):

   ```bash
   docker compose cp /tmp/cards app:/app/assets/
   ```

   若 `/app/assets/cards` 已存在(例如補圖),改用
   `docker compose cp /tmp/cards/. app:/app/assets/cards/`,否則會變成 `cards/cards`。

3. **驗證**:

   ```bash
   docker compose exec app sh -c 'ls /app/assets/cards/*.webp | wc -l'
   ```

卡圖是靜態檔,放進去後不需要重啟;若第一次放圖後網頁仍沒顯示,執行一次
`docker compose restart app` 讓服務重新解析卡圖目錄。CI 換新映像檔、重建容器不會動到
volume,卡圖只需要放一次;但 `docker compose down -v` 會連 volume 一起刪掉,要重放。

**從舊的 `.jpg` 卡圖換成 WebP(一次性)**:服務只讀 `.webp`,所以順序是

1. 依上面步驟 1–2 把 WebP 放進 volume(`/app/assets/cards` 已存在,用 `/tmp/cards/.` 那種寫法)。
   舊的 `.jpg` 先留著,換版前的服務照常讀它。
2. 打新版 tag,等 watchtower 換上新映像檔,確認卡面正常。
3. 刪掉舊檔:`docker compose exec app sh -c 'rm -f /app/assets/cards/*.jpg'`。

順序反過來的話,從新版上線到放好 WebP 之間,所有卡面都會是卡背。

## 意見回報

首頁的「意見回報」與頂欄的「回報」會開啟同一個對話框,提供兩個管道:

- **回報表單**(Google 表單,不需要帳號):連結會預填環境資訊(語言、模式、房號、回合、階段、瀏覽器)。
- **GitHub issue**(需要帳號):範本在 [`.github/ISSUE_TEMPLATE/`](.github/ISSUE_TEMPLATE/),分為問題回報、卡片效果不符、建議三種。

表單網址設在 `frontend/app.js` 開頭的 `FEEDBACK`;`formUrl` 空白時對話框只顯示 GitHub。建立表單的方式:

1. 建立 Google 表單,建議題目:類型(問題 / 卡片效果不符 / 建議)、內容(段落)、卡號(選填)、
   **環境資訊**(段落,選填)、聯絡方式(選填)。不要用「檔案上傳」題,填寫者必須登入 Google 才能上傳。
2. 表單右上「⋮ → 取得預先填入的連結」,在環境資訊欄填任意文字後取得連結。連結中
   `entry.<數字>=` 的 `entry.<數字>` 就是 `contextEntry`,`?` 之前的 `.../viewform` 是 `formUrl`。
3. 填入 `FEEDBACK`,並在 `.github/ISSUE_TEMPLATE/config.yml` 的 `contact_links` 加上表單連結。

## 規格與設計文件

規格與設計知識的組織方式、維護原則與變更流程定義在 [`docs/specification-guide.md`](docs/specification-guide.md),
進行規格驅動的開發(OpenSpec change)前先讀它。理解目前系統時依指南 §15「文件導航」的順序閱讀;
開始一個 change 前依 §11「Required Reading Procedure」。

- `openspec/capability-map.md`:導航入口,列出各 capability 的責任、關係與覆蓋程度。
- `openspec/specs/<capability>/spec.md`:目前的可觀察行為(現行 WHAT)。
- `openspec/specs/<capability>/design.md`:目前的設計與仍有效的理由(現行 HOW / WHY),含卡片效果文的解讀紀錄。
- `openspec/changes/archive/`:歷史變更的理由與過程。

## 卡片效果的寫法

新卡片一律以**效果樹**註冊:效果由 `effects/tree.py` 的節點組合(節點名稱不含卡號),登記放在
`effects/cards/`,依卡片類別分檔(`events.py` / `mamodo.py` / `partners.py` / `spells.py`),
每檔依卡號排序、每張卡的登記集中一處(多個掛鉤各一個 `reg.xxx(...)` 且相鄰),容器節點換行縮排以顯示巢狀層次
(排版規則見 `effects/cards/__init__.py`)。效果停下來等待(玩家選擇、擲幣確認、待命)時,只存續體這份純資料,
不存閉包。註冊入口:

- 事件卡 / 術卡:`reg.event(number, effect=…)`、`reg.spell_rider(number, on_damage= / on_declare= /
  on_win= / on_defense_damaged=…)`、`reg.spell_nonbattle(number, effect=…)`。
- 魔物 / 搭檔卡:`reg.activated(number, mode=…, mp_cost=…, timing=…, condition=…, effect=…)`、
  `reg.on_play` / `reg.on_discard` / `reg.start_phase(number, effect=…)`、`reg.trigger(number, 事件型別, effect=…)`。
- 只回傳值的查詢(常駐魔力加成、使用條件、傷害免疫、術相容、`damage_bonus`)不是效果,
  用 `tree.py` 裡不可變、可呼叫的規格物件登記(如 `reg.static_power(number, value=…)`)。

- 所有卡片都已遷移到效果樹,逐卡登記只在 `effects/cards/`。`registry.py` 仍接受舊的
  `@reg.xxx` 裝飾器寫法(只剩測試使用),新卡不要用;同一張卡的同一掛鉤不能兩種都註冊。
- `Standby.then` 目前只能同步完成(不可包含 `Choose` / `Coin`),註冊時檢查。
- 實作或修改卡片效果前先讀 `AGENTS.md`「實作 / 修改卡片效果」:以日文效果文為準、不可悄悄簡化、
  每張非香草卡都要有依效果文寫的行為測試。
- 效果的執行機制見 `openspec/specs/effect-tree/design.md`,卡片規則機制與效果文的解讀見 `openspec/specs/card-effects/design.md`。

## 測試

```bash
python -m pytest        # 引擎規則、67 張卡逐卡效果、API 整合、整局劇本
```

## 專案結構

```
src/gash/
  paths.py              資源目錄解析單點(repo 佈局、卡圖目錄)
  engine/               純 Python 遊戲引擎(無 IO,指令進 → 事件出)
    state.py            狀態模型:魔本頁序、MP、魔物槽、modifier、待命、戰鬥子狀態
    engine.py           規則主體:階段流程、輪流行動權、戰鬥五步驟、傷害/保護、勝敗
    cards.py / deck.py  卡片定義載入、魔本構築合法性驗證
    awaiting.py         等待者推導與安全預設指令(逾時代打、NPC 共用)
    effects/            效果系統
      registry.py       引擎 ↔ 卡片效果的掛鉤介面
      primitives.py     效果原語(加魔力、禁止旗標、待命、互動式硬幣…)
      tree.py           效果樹:不可變節點(Choose / Coin / Standby / AddPower…)+ 直譯器
      cards/            全部卡片的效果登記,依類別分檔(events / mamodo / partners / spells),各檔依卡號排序
  api/
    app.py              FastAPI:房間端點、指令轉發、WebSocket 推送、逾時代打、NPC 驅動
    rooms.py            房間模型、token 身分、計時器期限、NPC 座位
  npc/                  NPC 對手的決策(只經 determinize 取得盤面,看不到隱藏資訊)
    candidates.py       候選指令列舉(合法與否由引擎在副本上試送判斷)
    determinize.py      隱藏資訊替換:對手未公開頁抽樣、換 RNG
    settle.py           模擬到停點:對手的簡單回應規則
    evaluate.py         局面評估與權重
    views.py            視角過濾:snapshot(game, viewer) 與事件過濾(資訊不外洩的單點)
frontend/               無框架靜態前端(中、英、日介面,文字全走 i18n 字典)
  i18n/languages.json   語言清單(順序即選單順序)
  i18n/<lang>.json      介面文字、行動記錄模板與錯誤碼訊息(zh-TW / en / ja,條目一致)
  i18n/rules.<lang>.json 規則頁內容
  assets/cards/         卡圖 {卡號}.webp(缺圖時自動以文字卡面呈現)
data/
  cards_ja.csv          日文權威來源(atwiki 抓取結果),cards.json 的轉換輸入
  cards.json            卡片結構化數值資料(由 cards_ja.csv 轉換,日文為準)
  cards.zh-TW.json      卡片中文文本(卡名/效果),獨立於數值、可自由校對
  cards.ja.json         卡片日文文本(由 tools/build_card_texts.py 自 cards_ja.csv 產生,勿手改)
  cards.en.json         卡片英文文本(名稱取自 TTS 卡表,效果依日文效果文翻譯)
  decks/level1.json     預組魔本(32 頁)
tools/
  scrape_ja_effects.py  atwiki 日文權威資料抓取 → data/cards_ja.csv
  build_cards_json.py   cards_ja.csv → cards.json 轉換
  build_card_texts.py   產生 cards.ja.json,並把 TTS 卡表的英文名稱寫入 cards.en.json
  download_images.py    卡圖批次下載(Google Drive,支援續抓與失敗清單)
```

## 資料管線

1. `python tools/scrape_ja_effects.py` 抓取 atwiki.jp 日文權威頁面,輸出 `data/cards_ja.csv`。
2. `python tools/build_cards_json.py` 將 `data/cards_ja.csv` 轉換為 `data/cards.json`;
   `image_url`/`sets` 沿用轉換前既有 `data/cards.json` 的舊值(新卡無舊值可沿用時為空)。
3. `python tools/download_images.py` 批次下載卡圖,轉成 WebP 存至 `frontend/assets/cards/{卡號}.webp`;
   已存在自動跳過,失敗清單寫入 `_failed.txt`,缺圖不影響遊戲。

## 翻譯校對

卡片文字依語言分檔:`data/cards.zh-TW.json`、`data/cards.zh-CN.json`、`data/cards.en.json`、`data/cards.ja.json`,以卡號為 key:

```json
"S-001": {"name": "薩喀爾", "name_ja": "ザケル", "attr": "雷", "effect": "…"}
```

改動這些檔只影響顯示,不影響任何遊戲邏輯;介面用語在 `frontend/i18n/<lang>.json`,規則頁在 `frontend/i18n/rules.<lang>.json`。

- `cards.ja.json` 由 `python tools/build_card_texts.py` 自 `data/cards_ja.csv` 產生,不要手改(測試會比對)。
- `cards.en.json` 的 `name` / `attr` 由同一工具自 TTS 卡表寫入;`effect` 是依 `effect_ja` 手寫的翻譯,工具會保留。
  翻譯時「」括起的卡名改成該卡的英文名;卡表與卡圖的英文效果文只作用語參考(兩者與日文效果文有出入)。
- 簡體中文的三個檔(`i18n/zh-CN.json`、`i18n/rules.zh-CN.json`、`data/cards.zh-CN.json`)由
  `python tools/build_zh_cn.py` 自對應的繁中檔產生(OpenCC `tw2sp` + 工具內的術語表 `TERMS`),不要手改。
  **改了繁中就要重跑**,否則測試會失敗。譯名只轉字形(賈修→贾修);要保留或改寫的詞語加進 `TERMS`。
- 日文與英文是初版翻譯,尚未經母語者校對;簡體中文是自動轉換,尚未校對。歡迎修正。

新增語言 = 新增 `i18n/<lang>.json`、`i18n/rules.<lang>.json`、`data/cards.<lang>.json`,並登記到 `i18n/languages.json`。
`tests/test_i18n_languages.py` 會檢查各語言的條目、參數、規則頁段落、卡片涵蓋與錯誤碼是否一致。

## 架構備註

- 後端為權威伺服器:規則、隨機數、狀態、資訊過濾全在伺服器;前端只渲染視角化快照與送指令。
- 身分 = token:指令帶 `X-Player-Token`,伺服器由 token 決定玩家,payload 自報身分無效。
- 事件流帶全域序號:`GET /api/rooms/{code}/events?since=N` 增量同步(同樣經視角過濾),
  WebSocket 推送與 HTTP 回應以序號冪等,斷線重連即補齊。
- 視角過濾收斂在 `api/views.py` 單點:未翻開頁對所有人保密、翻開頁只對持有者可見、
  決策選項只送決策者、觀戰為純公開視角。引擎完全不知道「視角」存在。
- NPC 是房間的一個座位:輪到它時伺服器代為決策,指令走與玩家相同的提交路徑。
  NPC 的決策只經 `npc/determinize.py` 取得「對手隱藏資訊換成抽樣」的盤面副本,
  測試以「換掉隱藏資訊、決定不變」驗證它看不到不該看的資訊。
