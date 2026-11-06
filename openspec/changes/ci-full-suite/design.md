# Design

## Context

- `test.yml`:push / PR 到 `main`,Python 3.12,`pip install -e ".[dev]"` 後 `pytest`。`.[dev]` 裝了 playwright 套件但沒有下載 Chromium,`tests/conftest.py` 的 `browser` fixture(session scope)啟動失敗時 `pytest.skip`,所有用到它的測試都略過。
- `deploy.yml`:推 `v*` tag 時檢查更新內容 → 建置推 GHCR → `gh release create`,不跑測試。
- 瀏覽器測試的頁面由多個 fixture 建立(`page`、構築器的 `builder`、測試內自建的 context),都來自 session 的 `browser`。
- repo 為 public,Actions 不計分鐘數。

## Goals / Non-Goals

**Goals:** CI 的綠燈代表全套通過;沒有通過全套的 commit 不會被發布;CI 失敗時看得到畫面。

**Non-Goals:** 不改測試內容;不平行化測試(瀏覽器測試共用一個伺服器,見 AGENTS.md);action 釘 SHA、Dependabot 另做(todo)。

## Decisions

### Deploy 以 reusable workflow 呼叫同一份 Test

`test.yml` 加上 `workflow_call`,`deploy.yml` 新增 `test` job:`uses: ./.github/workflows/test.yml`,`build-and-push` 設 `needs: test`。
- 兩邊跑的是同一份定義,不會出現「Deploy 的測試步驟忘了跟著改」。
- 替代方案:Deploy 查詢該 commit 的 Test 結果。tag 可能打在沒有對應 Test 執行的 commit 上(例如 Test 被取消、或只在本機合併),查不到時仍要自己跑,不如直接跑。

### 安裝 Chromium 並快取

- `setup-python` 開 `cache: pip`(以 `pyproject.toml` 為 key)。
- `~/.cache/ms-playwright` 以 playwright 版本為 key 快取;之後一律執行 `python -m playwright install --with-deps chromium-headless-shell`:快取命中時不重新下載,只補系統套件(apt)。與 devcontainer 的 `postCreateCommand` 同一個指令。
- Python 版本維持 3.12,與 production 映像檔(`python:3.12-slim`)相同。

### concurrency 與逾時

- `test.yml` 頂層 `concurrency: { group: test-${{ github.ref }}, cancel-in-progress: true }`。被 Deploy 以 `workflow_call` 呼叫時 `github.ref` 是 tag,每個 tag 各自一組,不會取消別的發布。
- 測試 job `timeout-minutes: 25`(本機全套約 8 分鐘,CI 預估 10–12 分鐘,留一倍以上餘裕)。不設的話,卡住的瀏覽器測試要 6 小時才會失敗。

### 失敗截圖

- `tests/conftest.py` 加 `pytest_runtest_makereport` hookwrapper:測試本體(`call`)失敗時,截下 `browser` 所有 context 中所有頁面,存到 `test-results/<測試名稱>-<n>.png`。此時 fixture 還沒 teardown,頁面都還開著;所有頁面都來自 session 的 `browser`,不必知道是哪個 fixture 建的。測試沒有用到瀏覽器時(`browser` 不在 `item.funcargs`,且 session 沒有啟動過)不做事。截圖失敗只記警告,不影響測試結果。
  - 只截 `call` 階段:setup 失敗多半是伺服器或資料問題,畫面沒有參考價值。
- `test.yml` 在失敗時(`if: failure()`)以 `actions/upload-artifact` 上傳 `test-results/`,保留 7 天。`.gitignore` 排除 `test-results/`。

## Risks / Trade-offs

- [CI 機器較慢,瀏覽器測試的時間相關斷言不穩] → 先實際跑一次觀察;若有不穩定的測試,在這個 change 內修正等待條件,不加重試掩蓋。
- [部署多等約 10 分鐘] → 定版本來就不急;watchtower 每 5 分鐘輪詢。
- [Chromium 的系統套件每次都要 apt 安裝,約 30–60 秒] → 可接受;快取系統套件的做法複雜且脆弱。

## Migration Plan

- 在 `ci-full-suite` 分支推上 GitHub 並開 PR 到 `dev`:PR 會以分支上的新 `test.yml` 執行,實際確認全套在 CI 通過、略過數與本機相同、時間在預估內。另外用一個故意失敗的瀏覽器測試確認截圖 artifact(確認後移除)。
- Deploy 的測試關卡要等下次推 tag 才會實際執行;`workflow_call` 的寫法在 PR 驗證時一併以 `actionlint` 檢查語法。
