# Tasks

## 1. 測試

- [x] 1.1 守門測試 `tests/test_ci_supply_chain.py`(12 項;在實作前的 `dev` 工作樹上全部失敗,實作後全部通過)。

## 2. 實作

- [x] 2.1 repo 預設 workflow 權限改為唯讀(使用者同意,`gh api`)。
- [x] 2.2 workflow 權限與 action SHA(D1、D2)。
- [x] 2.3 lock 檔、Dockerfile、CI 安裝方式(D3、D4)。
- [x] 2.4 compose 的 watchtower 釘 digest;Dependabot(D4、D5)。
- [x] 2.5 README「相依套件與 CI 的安全設定」。

## 3. 驗證與文件

- [x] 3.1 快速測試組;`openspec validate ci-supply-chain --strict`。(快速組 2032 項,含守門測試 12 項)
- [x] 3.2 reconciliation:`docker-deployment/design.md`、capability-map。
- [ ] 3.3 使用者確認。
- [ ] 3.4 合併後:push 到 dev 時確認 CI 的 token 只有 read、測試照常通過;下次打 tag 時確認映像檔建置成功;VPS 重新 scp compose 並 `docker compose up -d watchtower`。
