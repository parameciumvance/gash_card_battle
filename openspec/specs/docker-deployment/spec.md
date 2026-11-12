# docker-deployment Specification

## Purpose

在 VPS 上以容器長期常駐提供線上對戰服務。

Scope:production 容器映像檔、經 Cloudflare Tunnel 對外服務、CI 的測試 / 建置分流、VPS 端的自動更新與健康檢查、從本機操作正式站的維運腳本(卡圖同步、維護公告的發布與撤下、狀態查詢)。不含房間 / 對戰行為本身(見 `online-room`、`battle-api`)。

## Requirements

### Requirement: Production 容器映像檔
專案 SHALL 提供獨立於開發容器(`.devcontainer/Dockerfile`)的 production `Dockerfile`,只安裝 `pyproject.toml` 核心依賴(不含 `dev` extras),且 MUST 依帶 hash 的 lock 檔安裝(版本與 hash 固定,建置用的工具也在 lock 內,不另外下載未驗證的套件);基底映像檔 MUST 以 digest 指定,進入點為單一 uvicorn 行程(不帶 `--reload`,不使用多 worker)。房間狀態存於行程記憶體,服務 MUST NOT 以多 replica/多 worker 方式水平擴展。映像檔 SHALL 以 build arg `GASH_VERSION` 帶入版本號並設為同名環境變數;CI 建置時 SHALL 傳入觸發部署的 tag 名稱。

#### Scenario: 映像檔不含開發工具與測試檔案
- **WHEN** 建置 production 映像檔
- **THEN** 映像檔內不包含 `tests/`、`tools/`、`.devcontainer/`、`pytest`/`openpyxl`/`pillow` 等僅供開發使用的檔案與套件

#### Scenario: 容器啟動即提供服務
- **WHEN** 以此映像檔啟動容器並對映對外埠
- **THEN** 瀏覽器可連上首頁,且可建立本機測試模式或線上房間並完成一局對戰

#### Scenario: 映像檔帶版本號
- **WHEN** 推送 tag `v0.9.1` 觸發建置,並以產出的映像檔啟動容器
- **THEN** `GET /api/meta` 的 `version` 為 `v0.9.1`

#### Scenario: 相依依 hash 安裝
- **WHEN** lock 檔中某個套件的 hash 與下載到的檔案不符
- **THEN** 映像檔建置失敗,不推送

### Requirement: CI 測試與建置分流
CI SHALL 區分「一般提交」與「正式發布」兩種流程:push 或 pull request 到主分支或開發分支(`dev`)時只執行測試套件,不得觸碰部署環境;僅當推送符合版本號格式(`v*`)的 tag 時,才建置映像檔並推送至容器登錄庫。正式發布時,更新內容(見 `battle-ui`「更新內容」)MUST 已有與該 tag 相同版本號的條目,否則 CI MUST NOT 建置映像檔;建置推送後 SHALL 以該版的繁體中文更新內容建立 GitHub Release。CI MUST NOT 持有任何能連進 VPS 的常駐憑證(SSH 金鑰、VPN 授權等)——容器更新由 VPS 端自行輪詢容器登錄庫觸發,不是 CI 主動推送。

#### Scenario: 一般 push 不影響線上服務
- **WHEN** 開發者 push 一般commit 到主分支
- **THEN** CI 執行測試套件,不建置映像檔、不連線 VPS、線上服務不受影響

#### Scenario: 開發分支的 push 執行測試
- **WHEN** 開發者 push commit 到 `dev`
- **THEN** CI 執行測試套件,不建置映像檔、不連線 VPS

#### Scenario: 打版號 tag 觸發建置
- **WHEN** 開發者推送符合 `v*` 格式的 tag(如 `v0.2.0`),更新內容已有 `v0.2.0` 的條目
- **THEN** CI 建置映像檔並推送至容器登錄庫、標上該版號與 `latest`,並以 `v0.2.0` 的繁中更新內容建立 GitHub Release,流程到此結束,不連線 VPS

#### Scenario: 缺少更新內容時不發布
- **WHEN** 開發者推送 tag `v0.2.1`,但更新內容沒有 `v0.2.1`
- **THEN** CI 失敗並指出缺少的版本,不建置映像檔,線上服務維持原版本

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

### Requirement: 維運腳本的連線
專案 SHALL 提供在本機執行的維運腳本,經 ssh 操作 VPS 部署目錄中的 compose 服務,不需要登入 VPS 手動執行指令。ssh 目標 SHALL 預設為 `dev@dev-vps`,可由環境變數 `GASH_VPS` 覆蓋;部署目錄 SHALL 預設為 `/opt/gash-card-battle`。腳本 MUST NOT 在 VPS 上留下暫存檔,MUST NOT 讀取或傳送部署目錄的 `.env`。ssh 連線或遠端指令失敗時,腳本 SHALL 以非 0 結束並顯示遠端的錯誤訊息。

#### Scenario: 以環境變數指定主機
- **WHEN** 設定 `GASH_VPS=ops@other-host` 後執行任一子指令
- **THEN** 腳本連到 `ops@other-host`,而不是 `dev@dev-vps`

#### Scenario: 連不上 VPS
- **WHEN** ssh 目標無法連線時執行任一子指令
- **THEN** 腳本以非 0 結束並顯示 ssh 的錯誤,不顯示成功訊息

### Requirement: 卡圖同步
維運腳本的卡圖同步 SHALL 比對 VPS 卡圖 volume 中已有的 `{卡號}.webp` 與本機 `frontend/assets/cards/` 中的 `.webp`,只上傳 VPS 上沒有的卡;指定卡號重傳時,這些卡 SHALL 覆蓋 VPS 上的檔案。上傳前 SHALL 列出要上傳的卡號與張數,沒有要上傳的卡時 SHALL 說明並結束;上傳後 SHALL 回報 VPS 上的卡圖總數。只存在於 VPS 的卡圖 MUST NOT 被刪除。同步 MUST NOT 重啟任何容器。

#### Scenario: 只補缺的卡
- **WHEN** 本機有 M-001 與 M-054 的卡圖,VPS 只有 M-001,執行卡圖同步
- **THEN** 只上傳 M-054;VPS 上的 M-001 不變,回報的總數多 1

#### Scenario: 重傳換過的圖
- **WHEN** 指定重傳 M-001,VPS 上已有 M-001
- **THEN** VPS 上的 M-001 換成本機的檔案

#### Scenario: 已經同步
- **WHEN** VPS 上已有本機全部的卡圖
- **THEN** 不上傳任何檔案,說明已經同步

### Requirement: 發布公告前的驗證
維運腳本發布公告前 SHALL 在本機驗證公告檔。伺服器會視為沒有公告的情況(依 `battle-api`「維護公告」:不是合法 JSON、缺少或空白的 `id`、`message` 不是語言對應文字的物件、`until` 無法解析或已過)SHALL 擋下並說明原因,MUST NOT 上傳。驗證 MUST 與伺服器讀取公告檔使用同一套規則。通過後 SHALL 列出各語言的訊息與 `until`,並對可能是錯誤的內容提出提醒(見情境),再詢問是否發布;回答否時 MUST NOT 上傳。以參數明確略過詢問時直接發布。

#### Scenario: 擋下已過期的公告
- **WHEN** 公告檔的 `until` 早於現在
- **THEN** 腳本說明 `until` 已過、伺服器不會顯示,不上傳,以非 0 結束

#### Scenario: 擋下格式錯誤
- **WHEN** 公告檔缺少 `message`
- **THEN** 腳本說明缺少 `message`,不上傳,以非 0 結束

#### Scenario: 提醒佔位文字與缺少的語言
- **WHEN** 公告的 `en` 是 `"..."`、`zh-CN` 是 `"123"`、沒有 `ja`
- **THEN** 腳本提醒 `en`、`zh-CN` 像佔位文字、缺少 `ja`(玩家會看到 `zh-TW`),並詢問是否發布;回答否時不上傳

#### Scenario: 提醒與繁中相同的翻譯
- **WHEN** 公告的 `en` 與 `zh-TW` 的文字完全相同
- **THEN** 腳本提醒 `en` 與 `zh-TW` 相同,可能忘了翻譯

#### Scenario: 提醒沒有時區的 until
- **WHEN** 公告的 `until` 是 `2026-12-01T22:30:00`(沒有時區)
- **THEN** 腳本提醒伺服器會把它當作 UTC,並顯示換算後的台灣時間

### Requirement: 發布與撤下公告
驗證通過(或確認仍要發布)後,維運腳本 SHALL 以原子替換的方式更新 VPS 卡圖 volume 中的公告檔,伺服器在任何時刻都 MUST NOT 讀到寫了一半的內容。撤下公告時 SHALL 刪除該檔案;沒有公告時撤下 SHALL 說明並正常結束。發布或撤下後,腳本 SHALL 查詢公開網域的 `GET /api/announcement`,確認回應與預期一致(發布時 `id` 相符,撤下時為 null),不一致時 SHALL 顯示實際回應並以非 0 結束。發布與撤下 MUST NOT 重啟任何容器。

#### Scenario: 發布後確認生效
- **WHEN** 發布 `id` 為 `2026-12-01-maint` 的公告
- **THEN** VPS 上的公告檔換成新內容,`GET /api/announcement` 回傳該 `id`,腳本回報已生效

#### Scenario: 撤下後確認
- **WHEN** 有公告時執行撤下
- **THEN** 公告檔被刪除,`GET /api/announcement` 回傳 null

### Requirement: 正式站狀態查詢
維運腳本 SHALL 提供唯讀的狀態查詢,一次顯示:公開網域 `GET /api/meta` 回報的版本、VPS 上各 compose 服務的狀態(含健康檢查)、卡圖 volume 中的卡圖張數與本機的張數,以及目前的公告(`id`、`until` 與 `zh-TW` 訊息,沒有時說明沒有公告)。狀態查詢 MUST NOT 修改 VPS 上的任何檔案或容器。

#### Scenario: 查詢狀態
- **WHEN** 執行狀態查詢
- **THEN** 顯示線上版本(例如 `v1.3.3`)、`app` / `cloudflared` / `watchtower` 的狀態、VPS 與本機的卡圖張數、目前公告

### Requirement: CI 執行全套測試
CI 的測試套件 SHALL 是全套,包含瀏覽器測試:CI 環境 SHALL 安裝瀏覽器測試所需的 Chromium,瀏覽器測試 MUST NOT 因 CI 缺少瀏覽器而被略過。CI 的 Python 版本 SHALL 與 production 映像檔相同。同一分支有新的推送時,SHALL 取消該分支還在執行的舊測試;測試工作 SHALL 有逾時上限,卡住時以失敗結束。

#### Scenario: 瀏覽器測試在 CI 執行
- **WHEN** CI 對一般 commit 執行測試套件
- **THEN** 瀏覽器測試實際執行;略過的只有測試本身設計為略過的項目(例如被動搭檔不能借用),沒有因缺少 Chromium 而略過的項目

#### Scenario: 連續推送
- **WHEN** 開發者連續推送兩次到 `dev`,第一次的測試還在執行
- **THEN** 第一次的測試被取消,只有第二次的測試跑完

### Requirement: 發布前的測試關卡
推送版本號 tag 時,CI SHALL 先對該 tag 指向的 commit 執行全套測試,通過後才建置映像檔;測試失敗時 MUST NOT 建置映像檔、MUST NOT 建立 GitHub Release,線上服務維持原版本。

#### Scenario: 測試失敗時不發布
- **WHEN** 開發者推送 tag `v0.2.2`,更新內容已有 `v0.2.2`,但該 commit 有測試失敗
- **THEN** CI 在測試階段失敗,不建置映像檔、不建立 Release,watchtower 不會拉到新版

### Requirement: CI 失敗的診斷資料
瀏覽器測試失敗時,SHALL 保存失敗當下各頁面的截圖,CI SHALL 將截圖上傳為該次執行的 artifact,讓開發者不必重現就能看到失敗時的畫面。測試全部通過時 MUST NOT 上傳。

#### Scenario: 瀏覽器測試失敗
- **WHEN** CI 中某個瀏覽器測試失敗
- **THEN** 該次執行的 artifact 有那個測試失敗當下的頁面截圖,檔名可對應到測試名稱

### Requirement: CI 的權限與相依鎖定
CI 的 workflow SHALL 在頂層宣告最小權限:執行測試的 job 只有讀取權限(包括被發布流程呼叫時),只有建置並推送映像檔、建立 Release 的 job 可以寫入。repo 的預設 workflow 權限 SHALL 為唯讀。第三方 action MUST 以 commit SHA 引用並註明版本號;CI 安裝 Python 相依 MUST 依帶 hash 的 lock 檔。VPS 上掛載 Docker socket 的更新代理 MUST 以版本與 digest 指定映像檔,不自動更新;通道連接器維持自動更新。這些固定的版本 SHALL 由自動化工具(Dependabot)定期開 PR 到開發分支提醒升級,經測試與檢視後合併。

#### Scenario: 測試 job 拿不到寫入權限
- **WHEN** 開發者 push commit 到 `dev`,測試 job 執行
- **THEN** 該 job 的 token 只有讀取 repo 內容的權限,不能推映像檔、commit 或 tag

#### Scenario: action 不隨標籤移動
- **WHEN** 某個第三方 action 的版本標籤被改指到其他 commit
- **THEN** CI 仍執行原本釘住的 commit,直到合併升級的 PR

#### Scenario: 升級經由 PR
- **WHEN** 相依套件、action 或映像檔有新版
- **THEN** 每週一次開 PR 到 `dev`,CI 跑全套測試,合併前不會進入正式環境
