# Design

## Context

- 本機的 dev container 透過 WSL 的網路在 tailnet 裡,`ssh dev@dev-vps` 走 Tailscale SSH(遠端軟體為 `Tailscale`),由 tailnet 的 ACL 授權,容器裡沒有也不需要 ssh 金鑰。VPS 上的 `dev` 在 `docker` 群組,可以直接執行 `docker compose`。
- 正式站 `app` 容器以 root 執行,映像檔(`python:3.12-slim`)有 `tar`。卡圖 volume 掛在 `/app/assets`,卡圖在 `/app/assets/cards/`(目前 332 張),公告檔是 `/app/assets/announcement.json`。
- 公告的讀取規則在 `src/gash/api/app.py` 的 `read_announcement`,行為由 `battle-api`「維護公告」規定。
- 正式站映像檔不含 `tools/`;既有的 `tools/release_notes.py` 只用標準函式庫,讓 CI 不必安裝專案依賴。

## Goals / Non-Goals

**Goals:**
- 補卡圖、發布 / 撤下公告、查看狀態,各用一個指令在本機完成。
- 公告在上傳前就擋下伺服器不會顯示的內容,並提醒常見的人為錯誤。

**Non-Goals:**
- 不負責部署新版本(仍由 CI + watchtower)、不重啟容器、不改 compose 或 `.env`。
- 不刪除 VPS 上多出來的卡圖。
- 不處理 VPS 部署目錄裡手動留下的 `announcement.json` / `template.announcement.json`(那是舊流程的工作副本,伺服器不讀它們)。

## Decisions

### 一個腳本、子指令

`tools/vps.py cards | announce FILE | announce --clear | status`。ssh 目標、部署目錄、公開網址與遠端指令的執行只寫一次。
- 替代方案:每件事一個腳本。共用的部分要複製或另外抽模組,不值得。

### 遠端指令一律經 `ssh <目標> "cd <部署目錄> && docker compose exec -T app ..."`

- 用 `docker compose exec -T` 進 `app` 容器操作 volume,不依賴 volume 在主機上的實際路徑(`/var/lib/docker/volumes/...` 需要 root)。
- 資料一律從 ssh 的 stdin 串流進去,遠端不經過 `/tmp`:
  - 卡圖:本機用 `tarfile` 把要上傳的 `.webp` 打包寫進 stdin,容器內 `tar -x -C /app/assets/cards`。打包時把擁有者設為 1000:1000(與目前 `cards/` 目錄相同),不帶本機的擁有者。
  - 公告:容器內 `cat > announcement.json.tmp && mv announcement.json.tmp announcement.json`。暫存檔與目標在同一個目錄(同一個檔案系統),`mv` 是原子的,伺服器每次請求即時讀檔也不會讀到一半;`cat` 失敗時刪掉暫存檔。
  - 替代方案:`scp` 到 VPS 再 `docker compose cp`(現行 README 的做法)。要兩次連線,而且會在 VPS 留下暫存檔;容器裡也沒有 rsync。
- 列出遠端卡圖用 `find /app/assets/cards -maxdepth 1 -name '*.webp'`,取檔名比對。
- 遠端指令的組裝與執行集中在一個小類別(例如 `Remote.run(args, stdin=None)`);測試以假的 `Remote` 取代,不需要真的連線。
- 參數一律以 `shlex.quote` 組進遠端命令字串(ssh 會把命令交給遠端 shell)。

### 設定

- `GASH_VPS`:ssh 目標,預設 `dev@dev-vps`。
- `GASH_VPS_DIR`:部署目錄,預設 `/opt/gash-card-battle`。
- `GASH_PUBLIC_URL`:確認用的公開網址,預設 `https://card-battle.zatchholic.com`。
- 都不寫進 repo 以外的設定檔;預設值就是目前的正式環境,換主機時用環境變數覆蓋。

### 公告驗證抽成共用的純函式

新增 `src/gash/announcement.py`:
- `parse_announcement(data, now) -> dict`:依 `battle-api` 的規則檢查並回傳 `{"id", "message", "until"}`;不合格時丟出 `AnnouncementError`,帶原因代碼(`json`、`id`、`message`、`until`、`expired`)。
- `read_announcement`(伺服器)改成:讀檔 → `json.loads` → `parse_announcement`。`expired` 照舊靜默回傳 None;其他原因照舊記一行警告後回傳 None。對外行為不變,既有的 `tests/test_announcement.py` 不改。
- `announcement_warnings(ann) -> list[str]`:只給腳本用的提醒,不影響伺服器。
- 腳本要 import `gash`,所以需要在裝好專案的環境執行(dev container 已經 `pip install -e .`)。與 `release_notes.py` 不同:那支要在 CI 裸跑,這支只在本機跑。
  - 替代方案:腳本自己再寫一份驗證。兩邊規則日後可能不一致,正是這次要避免的問題。

### 提醒的規則

語言以 `frontend/i18n/languages.json` 為準(目前 `zh-TW`、`zh-CN`、`en`、`ja`)。
- 缺少某種語言:提醒該語言的玩家會看到 `zh-TW`(伺服器與前端的備援規則見 `battle-ui`「維護公告橫幅」)。
- 像佔位文字:去掉空白後沒有任何文字字元(Unicode 類別 `L*`),例如 `"..."`、`"123"`、`""`。
- 與 `zh-TW` 完全相同:`zh-TW` 以外的語言。簡中與繁中同字的短句也會被提醒,所以只提醒、不擋。
- `until` 沒有時區:伺服器當作 UTC,顯示換算成 UTC+8 的時間,方便發現少寫 `+08:00`。
- 每次發布都先列出各語言的訊息再詢問(`--yes` 略過)。公告是所有玩家都看得到的內容,值得多看一眼。

### 發布後的確認

查詢 `GASH_PUBLIC_URL/api/announcement`(標準函式庫 `urllib`),比對 `id`(撤下時為 null)。這同時驗證了檔案位置正確、伺服器讀得到、通道與 Cloudflare 都正常。`/api/*` 不是 Cloudflare 預設會快取的副檔名,回應不會是舊的。

## Risks / Trade-offs

- [Tailscale SSH 需要互動確認(check mode)或 ACL 改變] → ssh 失敗時腳本照實顯示 ssh 的錯誤並以非 0 結束;腳本不處理任何驗證邏輯。
- [卡圖同步只比對檔名,換圖不會自動偵測] → 提供 `--force <卡號>`;卡圖很少換,不值得每次比對雜湊(要在遠端算 332 個檔案)。
- [`tar` 串流中斷時可能留下寫了一半的卡圖] → 卡圖以檔名為單位,重跑時該檔已存在會被跳過;中斷時腳本顯示錯誤,提示用 `--force` 重傳那幾張。
- [確認時公開網址暫時連不上(Cloudflare 或通道問題)] → 檔案已經換好,腳本顯示「已上傳,但無法確認」並以非 0 結束,可稍後用 `status` 再看。

## Migration Plan

- README「卡圖」「維護公告」改成以腳本為主,原本的手動指令留作腳本不能用時的備案。
- 不需要改 VPS 或正式站。回退時直接改用 README 的手動指令。
