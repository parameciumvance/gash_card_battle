# Design

## Context

- 盤點與風險排序見 proposal 的報告。使用者決定:A 同意以 `gh api` 把 repo 預設 workflow 權限改為唯讀(已執行,回 204,重新讀取為 `read`);B lock 檔一起做;C cloudflared 不釘版本。

## Decisions

### D1:權限

- workflow 頂層一律宣告;`test.yml` `contents: read`(被 `workflow_call` 呼叫時權限不會超過呼叫端);`deploy.yml` `permissions: {}`,`test` job `contents: read`,`build-and-push` 維持 `contents: write`、`packages: write`。

### D2:action

- 釘目前主版本標籤指向的 commit,註解改為完整版本號(checkout v4.4.0、setup-python v5.6.0、cache v4.3.0、upload-artifact v4.6.2、login-action v3.7.0、build-push-action v6.19.2)。各 action 都已有更新的主版本,升級交給 Dependabot 的 PR,不在此 change 改變行為。

### D3:lock 檔

- pip-tools(`pip-compile --generate-hashes --strip-extras --allow-unsafe --all-build-deps`),Dependabot 能直接更新 pip-compile 產生的檔案。`--all-build-deps` 把 setuptools 鎖進去,安裝專案時 `--no-build-isolation`,建置不再下載沒有 hash 的套件。
- 正式映像檔的 lock 不含 dev extras;開發容器維持 `pip install -e ".[dev]"`。
- 驗證:全新 venv 依 Dockerfile 的步驟安裝正式 lock 後可載入服務、沒有開發套件;依 dev lock 安裝後快速測試組 2020 項通過。

### D4:映像檔

- `python:3.14-slim@sha256:9aaa4740…`;watchtower `1.24.0@sha256:e96976bc…`(與當時的 latest 相同)。watchtower 掛 Docker socket,權限最大,不自動換新。cloudflared 維持 `:latest`(使用者:讓 Cloudflare 的修正自動套用)。

### D5:Dependabot

- 四個生態系每週一次、分組成一個 PR、`target-branch: dev`。cloudflared 的 `:latest` 不會被 Dependabot 更新。
