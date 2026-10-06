## 1. 先寫測試

- [x] 1.1 `app_version()`:環境變數優先、其次版本檔、再其次 git、都沒有為 `dev`;`/api/meta` 回傳 `version`。確認修改前失敗
- [x] 1.2 瀏覽器測試:首頁顯示版本號;意見回報的環境資訊含 `ver=`。確認修改前失敗
- [x] 1.3 靜態測試:`Dockerfile` 宣告 `GASH_VERSION`,`deploy.yml` 以 tag 名稱傳入

## 2. 實作

- [x] 2.1 `src/gash/version.py`、`/api/meta`(design D2)
- [x] 2.2 `Dockerfile`、`deploy.yml`、`build_release.py`、`.gitignore`
- [x] 2.3 前端顯示與環境資訊(design D3),i18n(簡中由工具產生)
- [x] 2.4 README:版本號的來源

## 3. Reconciliation 與歸檔(指南 §13)

- [x] 3.1 同步 delta spec 回各主 spec
- [x] 3.2 Reconcile affected capability design and rationale:`battle-api/design.md`(版本號來源)、`docker-deployment/design.md`(build arg)
- [x] 3.3 `openspec validate --all --strict`、`python -m pytest` 全過後歸檔

## 4. 待處理(不在本次範圍)

- [x] 4.1 (移到根目錄 todo.md)單機版 zip 命名仍用 `pyproject.toml` 的版本號(`0.1.0`),與畫面顯示的 tag 版本不一致;是否改用 tag 由使用者決定
