## 1. 名稱

- [x] 1.1 測試:四種語言的 `app.title` 與 `index.html` 的 `<title>` 都是「Gash Card Battle Online」;確認修改前失敗
- [x] 1.2 改 `index.html` 的 `<title>`、四種語言的 `app.title`(簡中重跑 `build_zh_cn.py`)、`build_zh_cn.py` 的說明;1.1 通過

## 2. 網頁圖示

- [x] 2.1 測試:`index.html` 有指向 `/static/favicon.svg` 的 `<link rel="icon">`,`GET /static/favicon.svg` 回應 200 與 `image/svg+xml`;確認修改前失敗
- [x] 2.2 新增 `frontend/favicon.svg`(design D2),在 `index.html` 引用;2.1 通過;截圖確認 16 / 32 / 64px 可辨識

## 3. 標題字

- [x] 3.0 首頁與頂欄的標題字(design D3)、自架 Oswald 子集與授權;測試:結構、`aria-label`、徽章與網頁圖示相同、ONLINE 置中、字型可取得且不向第三方請求;截圖確認桌面與手機

## 4. Reconciliation 與歸檔(指南 §13;主 spec 手動同步,歸檔用 `--skip-specs`)

- [x] 4.1 同步 delta spec 回 `battle-ui` 主 spec
- [x] 4.2 Reconcile affected capability design and rationale:`battle-ui/design.md` 補網站名稱與圖示;`card-data/design.md` 的 `app.title` 說明;capability map 系統概觀改用新名稱並註明原作;README 標題
- [x] 4.3 `openspec validate --all --strict`、全部測試通過後歸檔
