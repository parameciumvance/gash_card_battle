## Why

專案負責人決定不再提供單機發行版,服務只以 VPS 容器部署(`docker-deployment`)與開發環境執行。單機版的啟動器、cloudflared 公開通道、PyInstaller 打包,以及為它而設的資源目錄搜尋、`version.txt`、`/api/meta` 的 `tunnel_url` 都沒有其他用途,留著只會增加維護與測試負擔,文件也會誤導。

## What Changes

- **BREAKING** 移除單機發行:刪除 `src/gash/launcher.py`、`tools/build_release.py`、`tools/launch_entry.py` 與對應測試;`dev` 依賴移除 `pyinstaller`。
- **BREAKING** `/api/meta` 移除 `tunnel_url`;前端的加入 / 觀戰連結一律以 `location.origin` 為基底。
- 卡圖目錄只剩兩種來源:環境變數 `GASH_ASSETS_DIR`(VPS)或 repo 的 `frontend/assets/`(開發)。移除 PyInstaller 凍結佈局、執行檔旁 `assets/`、使用者資料夾的搜尋。
- 版本號只剩 `GASH_VERSION` → `git describe` → `dev`,移除 `data/version.txt`。
- README 移除「單機發行」一節與相關說明;`.gitignore` 移除 `gash.spec`、`data/version.txt`。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `standalone-release`:整個 capability 移除(資源目錄解析、啟動器、公開通道、發行打包)。
- `battle-api`:「執行環境中繼資訊」移除 `tunnel_url` 與單機版版本號來源;「卡圖靜態資源外部化」改為定義卡圖目錄(`GASH_ASSETS_DIR` 或 repo `frontend/assets/`),原本由 `standalone-release`「資源目錄解析」規範。
- `battle-ui`:「公開邀請連結」改為一律以 `location.origin` 組連結。
- `docker-deployment`:「Production 容器映像檔」的情境不再提單機發行與 `pyinstaller`。

## Impact

- 程式:刪除 `src/gash/launcher.py`、`tools/build_release.py`、`tools/launch_entry.py`;簡化 `src/gash/paths.py`、`src/gash/version.py`;`src/gash/api/app.py`(`launch_info`、`/api/meta`);`frontend/app.js`(`META`、`showWaiting`)。
- 依賴:`pyproject.toml` 的 `dev` 移除 `pyinstaller`。
- 測試:刪除 `tests/test_launcher.py`;改寫 `tests/test_paths.py`、`tests/test_version.py`、`tests/test_meta.py`;新增邀請連結的瀏覽器測試。
- 文件:README、`.gitignore`、`todo.md`、`capability-map.md`、`battle-api` / `battle-ui` / `card-data` / `docker-deployment` 的 spec 或 design。
- 部署:VPS 不受影響(映像檔本來就不含這些檔案,`GASH_ASSETS_DIR` 照舊);已發出的單機版 zip 不再維護。
