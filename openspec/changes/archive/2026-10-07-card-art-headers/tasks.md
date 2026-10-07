## 1. 先寫測試(確認修改前失敗)

- [x] 1.1 卡圖測試改用暫存卡圖目錄(fixture 把 `/static/assets/` 的 `StaticFiles` 指向暫存目錄);`test_card_art_served_from_assets_mount`、`test_meta_dev_mode` 不再依賴本機卡圖(design D3)
- [x] 1.2 MIME 對照表沒有 `.webp` 時(模擬 `python:3.12-slim`),卡圖回應仍為 `image/webp`
- [x] 1.3 存在的卡圖 200 與 304 都帶 `Cache-Control: public, max-age=604800`;404 不帶;前端資源仍是 `no-cache`

## 2. 實作

- [x] 2.1 `app.py` 註冊 `.webp` 的 MIME type(design D1)
- [x] 2.2 middleware 對卡圖成功回應加上 `Cache-Control: public, max-age=604800`(design D2)

## 3. 文件

- [x] 3.1 README「卡圖」:卡圖快取 7 天,同檔名換內容要清 Cloudflare 快取

## 4. Reconciliation 與歸檔(指南 §13)

- [x] 4.1 同步 delta spec 回 `battle-api` 主 spec
- [x] 4.2 Reconcile affected capability design and rationale:`battle-api/design.md`「前端資源快取」改寫卡圖段落(Content-Type 與 7 天快取的理由)
- [x] 4.3 `openspec validate --all --strict`、`python -m pytest` 全過後歸檔
