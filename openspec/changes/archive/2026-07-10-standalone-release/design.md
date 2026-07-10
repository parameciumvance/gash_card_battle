# Design: standalone-release

## Context

系統目前假設 repo 佈局(`ROOT = Path(__file__).parents[3]`,見 `api/app.py:24`、`engine/cards.py:10`),以 `uvicorn gash.api.app:app` 啟動,僅開發者能用。卡圖(`frontend/assets/cards/*.jpg`,86MB、134 張)在前端只有單一接觸點 `/static/assets/cards/${num}.jpg`(`app.js:320`)。房間全在記憶體、前端 WS 依 `location.protocol` 自動 ws/wss(`app.js:122`),故只要有一個支援 WebSocket 的 https 通道,線上對戰即可跨網工作,前端不需任何網路面改動。

發行需求(與使用者確認):安裝包**不含卡圖**、每版**單獨解壓即用**(不分 full/update);卡圖由維護者另行發佈,玩家安裝一次跨版本共用;未裝卡圖也要完整可玩。

## Goals / Non-Goals

**Goals:**
- 非開發者玩家 A:解壓 → 點兩下 → 取得可貼給 B 的公開邀請連結。
- 玩家 B:零安裝,點連結即加入。
- 單一發行 zip(程式 + runtime + cloudflared),卡圖外部化。
- 開發模式(repo + uvicorn)行為完全不變。

**Non-Goals:**
- 常駐雲端部署(Fly/Render/Docker)— 另案。
- 自動更新器、版本檢查。
- macOS/Linux 發行包(打包腳本不排斥,但驗證僅 Windows)。
- 固定網址(Quick Tunnel 每次啟動隨機,視為特性:一次性、私密)。

## Decisions

### D1. 資源解析:新模組 `gash/paths.py`,單點決定三個目錄

`app_root()`(程式資源:frontend/、data/)與 `assets_dir()`(卡圖)分開解析:

- `app_root()`:凍結環境(`getattr(sys, "frozen", False)`)→ `sys._MEIPASS`(onedir 下即 `_internal/`,frontend/ 與 data/ 以 PyInstaller datas 打入);否則 → repo 佈局 `parents[N]`(現況)。
- `assets_dir()` 依序:`GASH_ASSETS_DIR` 環境變數 → exe 旁 `assets/` → 使用者資料夾(Windows `%LOCALAPPDATA%\gash-card-battle\assets`、其他平台 `~/.local/share/gash-card-battle/assets`)→ repo `frontend/assets/`。取第一個**存在**的;全部不存在時回傳使用者資料夾路徑並標記 `installed=False`(供提示訊息顯示建議安裝位置)。

`api/app.py` 與 `engine/cards.py` 的路徑計算改走此模組。卡圖以獨立 mount `app.mount("/static/assets", StaticFiles(directory=assets_dir()))` 掛在既有 `/static` 之前;開發模式下兩者指向同一實體目錄,行為等價。

替代方案:全部塞進單一 `ROOT` — 不可行,因為卡圖與程式資源的來源自此分離。

### D2. Launcher:`gash/launcher.py`,程式內嵌 uvicorn + 子行程 cloudflared

流程:`uvicorn.Server` 於執行緒內啟動(綁 `127.0.0.1`,port 自動探測避免占用)→ 若 exe 旁存在 `cloudflared(.exe)`,以子行程執行 `cloudflared tunnel --url http://127.0.0.1:<port>`,從 stderr 解析 `https://*.trycloudflare.com`(逾時 30 秒)→ `webbrowser.open` 開本機網址 → 終端顯示公開網址;結束時(Ctrl-C / 視窗關閉)一併終止子行程。

- 公開網址寫入 app 狀態,由 meta API 提供給前端(D4)。
- **重試**:Quick Tunnel 申請偶發 Cloudflare 端 5xx(實測 error 1101,cloudflared 直接退出)→ 至多重試 3 次(間隔 2 秒)再降級。
- **降級**:cloudflared 不存在或重試用盡 → 僅本機模式照常進遊戲,meta 回報 `tunnel: null`,前端邀請區顯示區網網址並註明「外網邀請需 cloudflared」。
- PyInstaller 進入點即 launcher(`gash.exe` = launcher);開發模式另可 `python -m gash.launcher` 測試。

替代方案:要求 A 自行安裝 cloudflared(門檻過高,否決);ngrok(需帳號 token,否決);內嵌 tunnel 進 exe(更新包變大且授權/防毒面更差,採外置檔案)。

### D3. 打包:PyInstaller onedir,單一 zip,卡圖排除

- onedir(非 onefile):防毒誤判率低、啟動快;發行物為 `gash-vX.zip` 解壓後 `gash/`(`gash.exe`、`_internal/`、`cloudflared.exe`)。
- datas:`frontend/`(**排除 `assets/cards/`**)與 `data/` 打入 `_internal`。
- 打包腳本 `tools/build_release.py`:呼叫 PyInstaller、下載/校驗 cloudflared(或取本機既有檔)、組 zip。Windows 產物需於 Windows(或 CI windows runner)建置;腳本本身跨平台。
- 版本號取 `pyproject.toml`,zip 命名 `gash-card-battle-v{version}-win64.zip`。

### D4. 執行環境中繼資訊:`GET /api/meta`

回傳 `{ "tunnel_url": str|null, "assets": { "installed": bool, "count": int, "expected": int, "install_dir": str } }`。前端 boot 時取得:

- 入口/等待畫面的邀請連結改用 `tunnel_url`(有通道時)組 `?join=` 網址;無通道時維持 `location.origin`。
- `assets.installed == false` 或 `count < expected` 時顯示一次性提示(卡圖未安裝/不足,建議路徑 `install_dir`)。

替代方案:塞進既有 room meta — 資產狀態與房間無關,獨立端點較乾淨且入口畫面(尚無房間)就需要它。

### D5. 缺圖降級:前端 onerror 佔位

`cardEl` 的 `img.art` 加 `onerror` → 換成 `/static/back.jpg` 並標記 class(避免重試迴圈)。逐卡處理(而非依 `installed` 全域切換),天然涵蓋「卡圖包舊、新彈卡缺圖」的部分缺圖情境。規則與文字渲染不依賴卡圖,遊戲完整可玩。

## Risks / Trade-offs

- [PyInstaller 防毒誤判] → onedir + 不加殼;README 註明;長期可考慮簽章(非本案)。
- [trycloudflare 網址每次不同] → 視為一次性房間特性;README 說明「每次開房連結都是新的」。
- [Quick Tunnel 為 Cloudflare 免費測試服務,無 SLA] → 降級路徑保證區網仍可玩;若服務變動僅影響外網邀請。
- [cloudflared 輸出格式變動導致解析失敗] → 逾時降級 + 終端印出原始輸出供回報。
- [86MB 卡圖另行發佈,玩家放錯位置] → meta 提示明確顯示建議路徑;支援多個搜尋位置。
- [單行程限制不變] → launcher 固定單 worker;本就是設計現況。

## Migration Plan

純新增,無資料遷移。開發模式啟動方式不變;發行流程為新增項目。回滾 = 不發行。

## Open Questions

- cloudflared 版本鎖定與校驗雜湊由打包腳本固定(實作時選定當時穩定版)。
- CI 自動出包(GitHub Actions windows runner)是否納入本案:預設先提供本機打包腳本,CI 留待需要時加。
