# Proposal

## Why

CI 的 Test 只在 `main` 執行,而且沒有安裝 Chromium:`tests/conftest.py` 的 `browser` fixture 啟動失敗,瀏覽器測試整批略過(最近一次 1646 passed、449 skipped;本機全套是 2086 passed、9 skipped)。CI 通過只代表引擎、API 與腳本沒問題,UI 完全沒有測到。新的分支流程(AGENTS.md「分支」)把開發集中在 `dev`,而 `dev` 的推送目前什麼都不跑。

打版號 tag 的 Deploy 也不跑測試:tag 打在沒測過的 commit 上,有問題的版本會直接建置、由 watchtower 部署,重啟還會讓進行中的對局消失。

## What Changes

- Test 在 push 或 pull request 到 `main`、`dev` 時執行,並安裝 Chromium,瀏覽器測試照常執行(全套)。
- Deploy 先執行同一套測試,通過後才建置映像檔;測試失敗時不建置、不建立 Release,線上維持原版本。
- 速度與穩定:快取 pip 與 Chromium;同一分支有新推送時取消還在執行的舊測試;測試工作設逾時上限。
- 測試失敗時保留診斷資料:失敗的瀏覽器測試截下當時的頁面,上傳為 CI artifact。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `docker-deployment`:修改「CI 測試與建置分流」(觸發分支加上 `dev`);新增「CI 執行全套測試」「發布前的測試關卡」「CI 失敗的診斷資料」。

## Impact

- `.github/workflows/test.yml`、`.github/workflows/deploy.yml`。
- `tests/conftest.py`:瀏覽器測試失敗時截圖;`.gitignore` 排除截圖目錄。
- 部署時間多約 10 分鐘(先跑測試);watchtower 每 5 分鐘輪詢,影響不大。repo 為 public,Actions 不計分鐘數。
- 不動應用程式碼與正式站。
