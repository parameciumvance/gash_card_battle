## Context

- 單機發行包含:`src/gash/launcher.py`(啟動 uvicorn、cloudflared Quick Tunnel、開瀏覽器)、`tools/build_release.py` 與 `tools/launch_entry.py`(PyInstaller 打包)、`tests/test_launcher.py`。
- 為單機版而設、散在共用程式裡的部分:
  - `src/gash/paths.py`:PyInstaller 凍結佈局(`sys._MEIPASS`)、執行檔旁 `assets/`、跨版本共用的使用者資料夾。開發環境也會先找使用者資料夾,再找 repo `frontend/assets/`。
  - `src/gash/version.py`:`data/version.txt`(打包時寫入)。
  - `src/gash/api/app.py`:`launch_info["tunnel_url"]`,由 launcher 填入,經 `/api/meta` 給前端。
  - `frontend/app.js`:邀請連結優先用 `META.tunnel_url`。
- VPS 映像檔以 `GASH_ASSETS_DIR=/app/assets` 指定卡圖目錄,以 `GASH_VERSION` 帶版本號,沒有用到上述任何單機邏輯。

## Goals / Non-Goals

**Goals:**

- 刪除單機版專用的程式、工具、測試與文件。
- 共用程式只保留 VPS 與開發環境需要的路徑:卡圖目錄 `GASH_ASSETS_DIR` 或 repo `frontend/assets/`;版本號 `GASH_VERSION` → `git describe` → `dev`。
- 現行規格不再提到單機版。

**Non-Goals:**

- 不改 VPS 的部署方式、`docker-compose.yml` 的 Cloudflare Tunnel(與單機版的 Quick Tunnel 無關)。
- 不改首頁的卡圖安裝提示與 `install_dir` 欄位;開發與 VPS 仍用得到。
- 不處理已發出的單機版 zip。

## Decisions

### D1:`tunnel_url` 整個移除

前端的邀請連結直接用 `location.origin`。VPS 經固定網域對外,`location.origin` 就是公開網址;開發環境用 localhost 本來就只能本機或區網連線。`/api/meta` 不再帶這個欄位,`launch_info` 一併刪除。

### D2:卡圖目錄只剩兩種來源

`resolve_assets()`:有 `GASH_ASSETS_DIR` 就用它(不存在也不往下找,維持既有行為);否則用 repo `frontend/assets/`。`installed` 仍以目錄下有沒有 `cards/` 判斷。

- 開發環境原本會先找使用者資料夾(`~/.local/share/gash-card-battle/assets`)。拿掉後,即使那裡有舊卡圖也不會再被讀到;開發環境本來就以 repo `frontend/assets/` 為準。
- `AssetsInfo.install_dir` 一律等於 `dir`,刪掉這個欄位;`/api/meta` 的 `install_dir` 改回報 `dir`,前端不變。
- 程式資源(`frontend/`、`data/`)只剩 repo 佈局,`app_root()` 固定為 repo 根目錄。Docker 是 editable 安裝,同樣適用。

### D3:版本號移除 `version.txt`

`app_version()` 依序取 `GASH_VERSION`、`git describe`、`dev`。

### D4:保留的東西

- `.gitignore` 的 `build/`、`dist/`:也是 setuptools 的建置輸出(本機的 `build/` 就是 editable 安裝留下的),不是單機版專用。只移除 `gash.spec`、`data/version.txt`。
- `todo.md` 裡 NPC 一項的「單機真的不夠時」指的是單一主機,不是單機版,不改。

## Risks / Trade-offs

- [已經拿到單機版 zip 的玩家無法再更新] → 專案負責人決定接受;改用 VPS 上的網站。
- [開發者把卡圖放在使用者資料夾的話,升級後不再被讀到] → 首頁會提示卡圖未安裝並顯示 `frontend/assets/` 路徑;README 本來就說明卡圖下載到 `frontend/assets/cards/`。
