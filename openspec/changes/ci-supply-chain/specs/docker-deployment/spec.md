## MODIFIED Requirements

### Requirement: Production 容器映像檔
專案 SHALL 提供獨立於開發容器(`.devcontainer/Dockerfile`)的 production `Dockerfile`,只安裝 `pyproject.toml` 核心依賴(不含 `dev` extras),且 MUST 依帶 hash 的 lock 檔安裝(版本與 hash 固定,建置用的工具也在 lock 內,不另外下載未驗證的套件);基底映像檔 MUST 以 digest 指定,進入點為單一 uvicorn 行程(不帶 `--reload`,不使用多 worker)。房間狀態存於行程記憶體,服務 MUST NOT 以多 replica/多 worker 方式水平擴展。映像檔 SHALL 以 build arg `GASH_VERSION` 帶入版本號並設為同名環境變數;CI 建置時 SHALL 傳入觸發部署的 tag 名稱。

#### Scenario: 映像檔不含開發工具與測試檔案
- **WHEN** 建置 production 映像檔
- **THEN** 映像檔內不包含 `tests/`、`tools/`、`.devcontainer/`、`pytest`/`openpyxl`/`pillow` 等僅供開發使用的檔案與套件

#### Scenario: 容器啟動即提供服務
- **WHEN** 以此映像檔啟動容器並對映對外埠
- **THEN** 瀏覽器可連上首頁,且可建立本機測試模式或線上房間並完成一局對戰

#### Scenario: 映像檔帶版本號
- **WHEN** 推送 tag `v0.9.1` 觸發建置,並以產出的映像檔啟動容器
- **THEN** `GET /api/meta` 的 `version` 為 `v0.9.1`

#### Scenario: 相依依 hash 安裝
- **WHEN** lock 檔中某個套件的 hash 與下載到的檔案不符
- **THEN** 映像檔建置失敗,不推送

## ADDED Requirements

### Requirement: CI 的權限與相依鎖定
CI 的 workflow SHALL 在頂層宣告最小權限:執行測試的 job 只有讀取權限(包括被發布流程呼叫時),只有建置並推送映像檔、建立 Release 的 job 可以寫入。repo 的預設 workflow 權限 SHALL 為唯讀。第三方 action MUST 以 commit SHA 引用並註明版本號;CI 安裝 Python 相依 MUST 依帶 hash 的 lock 檔。VPS 上掛載 Docker socket 的更新代理 MUST 以版本與 digest 指定映像檔,不自動更新;通道連接器維持自動更新。這些固定的版本 SHALL 由自動化工具(Dependabot)定期開 PR 到開發分支提醒升級,經測試與檢視後合併。

#### Scenario: 測試 job 拿不到寫入權限
- **WHEN** 開發者 push commit 到 `dev`,測試 job 執行
- **THEN** 該 job 的 token 只有讀取 repo 內容的權限,不能推映像檔、commit 或 tag

#### Scenario: action 不隨標籤移動
- **WHEN** 某個第三方 action 的版本標籤被改指到其他 commit
- **THEN** CI 仍執行原本釘住的 commit,直到合併升級的 PR

#### Scenario: 升級經由 PR
- **WHEN** 相依套件、action 或映像檔有新版
- **THEN** 每週一次開 PR 到 `dev`,CI 跑全套測試,合併前不會進入正式環境
