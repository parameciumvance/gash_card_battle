## Why

2026-11-11 的 CI 供應鏈盤點(報告:https://claude.ai/artifact/JWzvjVppwMTkjh6M2wUmRR)發現:repo 的 Actions token 預設可寫入,測試 job 每次 push 都以寫入權限執行未鎖版本的相依與第三方 action,任一環節被入侵就能推映像檔,由 watchtower 自動上線。使用者 2026-11-12 決定:repo 預設權限由我改為唯讀;lock 檔一起做;cloudflared 不釘版本。

## What Changes

- token 最小權限:`test.yml` `contents: read`;`deploy.yml` 預設 `permissions: {}`,只有建置 job 可寫入。repo 的預設 workflow 權限已改為唯讀(2026-11-12,`gh api`)。
- action 一律以 commit SHA 引用,註解版本號(維持目前使用的版本,不升主版本)。
- Python 相依改由帶 hash 的 lock 檔安裝:`requirements.lock`(正式映像檔)、`requirements-dev.lock`(CI),含建置用的 setuptools;Dockerfile 與 CI 以 `--require-hashes` 安裝,專案本身 `--no-deps --no-build-isolation`。
- 映像檔釘 digest:`Dockerfile` 的 `python:3.14-slim`;`docker-compose.yml` 的 watchtower(1.24.0)。cloudflared 維持 `:latest` 自動更新(使用者決定)。
- Dependabot:github-actions、pip、docker、docker-compose,每週分組開 PR 到 `dev`。
- 守門測試 `tests/test_ci_supply_chain.py`;README 新增「相依套件與 CI 的安全設定」。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `docker-deployment`:新增「CI 的權限與相依鎖定」;修改「Production 容器映像檔」(依 lock 檔安裝、基底映像檔釘 digest)。

## Impact

- `.github/workflows/*.yml`、`.github/dependabot.yml`、`Dockerfile`、`docker-compose.yml`、`requirements.lock`、`requirements-dev.lock`、`README.md`、`tests/test_ci_supply_chain.py`。
- VPS:compose 檔是手動複製的快照,要重新 `scp` 並 `docker compose up -d watchtower` 才會套用 watchtower 的版本鎖定(目前 1.24.0 與 latest 相同)。
- 正式映像檔的實際建置要到下次打 tag 才驗證(本機沒有 Docker;安裝步驟已在全新 venv 驗證)。
