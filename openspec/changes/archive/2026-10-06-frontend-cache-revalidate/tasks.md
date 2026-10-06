## 1. 先寫測試

- [x] 1.1 `/`、`/static/app.js`、`/static/style.css`、`/static/i18n/zh-TW.json`、`/data/cards.json` 回應帶 `Cache-Control: no-cache`;帶 `If-None-Match` 時回 304;`/static/assets/` 與 `/api/meta` 不帶。確認修改前失敗

## 2. 實作

- [x] 2.1 `app.py` 的 HTTP middleware(design D2)

## 3. Reconciliation 與歸檔(指南 §13)

- [x] 3.1 同步 delta spec 回 `battle-api` 主 spec
- [x] 3.2 Reconcile affected capability design and rationale:`battle-api/design.md` 補前端資源快取(做法與理由)
- [x] 3.3 `openspec validate --all --strict`、`python -m pytest` 全過後歸檔
