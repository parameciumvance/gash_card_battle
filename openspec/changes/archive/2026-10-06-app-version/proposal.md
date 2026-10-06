## Why

部署後無法從網頁判斷目前跑的是哪一版:Cloudflare 或瀏覽器快取了舊檔時,玩家與維護者都只能猜。回報問題時也不知道是哪一版的問題。

## What Changes

- **版本號**:以 git tag 名稱為版本號(例如 `v0.9.1`),與部署的版號一致。
  - VPS(Docker):CI 建置時以 build arg 傳入 tag 名稱,存為環境變數 `GASH_VERSION`。
  - 單機版:打包時把 `git describe` 的結果寫入發行物的 `data/version.txt`。
  - 開發環境:執行 `git describe --tags --always --dirty`(例如 `v0.9.1-3-gabc1234-dirty`)。
  - 都取不到時為 `dev`。
- **`GET /api/meta`** 回傳 `version`。
- **前端**:首頁免責聲明下方顯示版本號;意見回報的環境資訊加上 `ver=…`。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `battle-api`:修改「執行環境中繼資訊」(回傳版本號)。
- `battle-ui`:修改「首頁免責聲明」(下方顯示版本號)、「意見回報」(環境資訊含版本號)。
- `docker-deployment`:修改「Production 容器映像檔」(映像檔帶版本號)。
- `standalone-release`:修改「發行打包」(發行物帶版本號)。

## Impact

- 新模組 `src/gash/version.py`;`app.py` 的 `/api/meta`。
- `Dockerfile`(`ARG` / `ENV GASH_VERSION`)、`.github/workflows/deploy.yml`(`build-args`)。
- `tools/build_release.py`(寫入 `data/version.txt`);`.gitignore` 排除該檔。
- 前端:`index.html`、`app.js`、`style.css`、i18n。
