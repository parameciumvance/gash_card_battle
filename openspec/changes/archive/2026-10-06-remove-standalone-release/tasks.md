## 1. 先寫測試(確認修改前失敗)

- [x] 1.1 `/api/meta` 不含 `tunnel_url`(`tests/test_meta.py`,刪除 `test_meta_reports_tunnel_url`)
- [x] 1.2 邀請連結:`/api/meta` 即使回傳 `tunnel_url`,加入 / 觀戰連結仍以 `location.origin` 組成(瀏覽器測試)
- [x] 1.3 `tests/test_paths.py` 改寫:未設定環境變數時為 repo `frontend/assets/`;環境變數優先(不存在也不改找);沒有 `cards/` 時回報未安裝;不再有凍結佈局與使用者資料夾的測試
- [x] 1.4 `tests/test_version.py`:刪除 `version.txt` 相關測試,環境變數優先於 `git describe`

## 2. 移除與簡化

- [x] 2.1 刪除 `src/gash/launcher.py`、`tools/build_release.py`、`tools/launch_entry.py`、`tests/test_launcher.py`
- [x] 2.2 `src/gash/paths.py` 只留 repo 佈局與 `GASH_ASSETS_DIR` / `frontend/assets/`(design D2)
- [x] 2.3 `src/gash/version.py` 移除 `version.txt`(design D3)
- [x] 2.4 `src/gash/api/app.py` 移除 `launch_info` 與 `/api/meta` 的 `tunnel_url`,`install_dir` 回報卡圖目錄
- [x] 2.5 `frontend/app.js`:`META` 移除 `tunnel_url`,`showWaiting()` 以 `location.origin` 組連結(design D1)
- [x] 2.6 `pyproject.toml` 的 `dev` 移除 `pyinstaller`;`.gitignore` 移除 `gash.spec`、`data/version.txt`

## 3. 文件

- [x] 3.1 README:刪除「單機發行」一節;VPS 部署的開頭、版本號、卡圖段落、專案結構移除單機版說明
- [x] 3.2 `todo.md` 移除單機版相關項目

## 4. Reconciliation 與歸檔(指南 §13)

- [x] 4.1 同步 delta spec 回 `battle-api`、`battle-ui`、`docker-deployment` 主 spec;刪除 `standalone-release` capability;`docker-deployment` 的 Purpose 不再提單機發行(OpenSpec 1.6 不允許 MODIFIED 拿掉既有 scenario,改為手動同步後以 `openspec archive --skip-specs` 歸檔)
- [x] 4.2 Reconcile affected capability design and rationale:`battle-api/design.md`(版本號、快取段落)、`battle-ui/design.md`(意見回報設定)、`card-data/design.md`(轉檔位置)移除單機版
- [x] 4.3 Update capability map:移除 `standalone-release`,系統概觀與閱讀入口改為只有 VPS 部署
- [x] 4.4 `openspec validate --all --strict`、`python -m pytest` 全過後歸檔
