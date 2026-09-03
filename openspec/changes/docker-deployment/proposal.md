## Why

目前只有兩種對外分享對局的方式:開發用的 `uvicorn --reload`(僅 127.0.0.1)、與給非開發者的單機發行版(PyInstaller exe + cloudflared 一次性隧道,見「單機發行」)。使用者已有一台 Ubuntu 24.04 VPS(裝 Docker、無 nginx、暫無網域),想長期、穩定地把伺服器架在上面給不特定人隨時連進來玩,並用 CI/CD 自動化建置與部署,不需要 exe 打包與 cloudflared 隧道那套(那是設計給「使用者自己電腦短暫開著」的情境,VPS 常駐用不到)。

核心需求:容器化這個 FastAPI 服務,搭配反向代理與 GitHub Actions,建立「打 tag → 建置映像檔 → 部署上 VPS」的流程,現在先以 IP 直連運作,之後補上網域時只需調整反代設定。

## What Changes

- 新增 production 用 `Dockerfile`(與 `.devcontainer/Dockerfile` 分開——後者是開發容器,含 vim/npm/openspec CLI 等工具,不適合當服務映像檔):只安裝 `pyproject.toml` 的核心依賴(`fastapi`/`uvicorn[standard]`,不含 `dev` extras),進入點為 `uvicorn gash.api.app:app --host 0.0.0.0 --port 8000`。
- 新增 `docker-compose.yml`:`app`(本服務)+ `caddy`(反向代理)兩個服務。`app` 透過 `GASH_ASSETS_DIR` 環境變數指向一個掛載的 volume(卡圖部署方式另案處理,這次只預留掛載點,卡圖目錄可為空,缺圖時前端既有的文字卡面備援機制照常運作)。
- 新增 `Caddyfile`:現在監聽 VPS 對外 IP 的 80 埠、反代到 `app:8000`(含 WebSocket upgrade,Caddy 對此免額外設定);之後補網域時只需把位址換成網域(Caddy 會自動簽發並續期 HTTPS 憑證),不需改動其他部分。
- 新增 `.github/workflows/test.yml`:push/PR 到 main 時跑 `pytest`,不觸碰 VPS。
- 新增 `.github/workflows/deploy.yml`:push 符合 `v*` 格式的 tag 時觸發——建置 Docker 映像檔、推到 GitHub Container Registry(GHCR)並標上該 tag、SSH 進 VPS 執行 `docker compose pull && docker compose up -d`。
- README 新增「VPS 部署」章節,記錄一次性手動設置步驟(VPS 上安裝 Docker/Docker Compose、準備 `docker-compose.yml`/`Caddyfile`、GitHub repo Secrets 需要哪些欄位)——這些是維護者一次性操作,不是 CI 能自動化的部分。

## Capabilities

### New Capabilities

- `docker-deployment`:容器化部署與 CI/CD 流程的行為契約。

## Impact

- 新增檔案:`Dockerfile`、`docker-compose.yml`、`Caddyfile`、`.github/workflows/test.yml`、`.github/workflows/deploy.yml`
- `README.md`:新增部署章節
- 不影響:現有的單機發行(`tools/build_release.py`/`gash.launcher`)、引擎/前端程式碼——這次純粹是部署層,不動任何遊戲邏輯
- 需要使用者在 GitHub repo 設定 Secrets(VPS 連線資訊、SSH 部署金鑰)與在 VPS 上執行一次性初始化指令,這些不屬於本次程式碼變更範圍,會記錄在 README 供操作依循
