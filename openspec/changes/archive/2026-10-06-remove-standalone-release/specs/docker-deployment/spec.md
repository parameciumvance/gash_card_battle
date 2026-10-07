## MODIFIED Requirements

### Requirement: Production 容器映像檔
專案 SHALL 提供獨立於開發容器(`.devcontainer/Dockerfile`)的 production `Dockerfile`,只安裝 `pyproject.toml` 核心依賴(不含 `dev` extras),進入點為單一 uvicorn 行程(不帶 `--reload`,不使用多 worker)。房間狀態存於行程記憶體,服務 MUST NOT 以多 replica/多 worker 方式水平擴展。映像檔 SHALL 以 build arg `GASH_VERSION` 帶入版本號並設為同名環境變數;CI 建置時 SHALL 傳入觸發部署的 tag 名稱。

#### Scenario: 映像檔不含開發工具與測試檔案
- **WHEN** 建置 production 映像檔
- **THEN** 映像檔內不包含 `tests/`、`tools/`、`.devcontainer/`、`pytest`/`openpyxl`/`pillow` 等僅供開發使用的檔案與套件

#### Scenario: 容器啟動即提供服務
- **WHEN** 以此映像檔啟動容器並對映對外埠
- **THEN** 瀏覽器可連上首頁,且可建立本機測試模式或線上房間並完成一局對戰

#### Scenario: 映像檔帶版本號
- **WHEN** 推送 tag `v0.9.1` 觸發建置,並以產出的映像檔啟動容器
- **THEN** `GET /api/meta` 的 `version` 為 `v0.9.1`
