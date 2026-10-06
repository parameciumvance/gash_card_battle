## Why

部署新版後,電腦上的瀏覽器顯示新的 `index.html`,卻仍在用舊的 `app.js` 與 `style.css`:新的入口框沒有文字、免責聲明與背景紋路都沒有出現,要強制重新整理才正常。

原因是前端檔案(`/`、`/static/`、`/data/`)回應時只有 `ETag` 與 `Last-Modified`,沒有 `Cache-Control`。瀏覽器因此自行推估快取時間,在這段時間內直接使用舊檔,不向伺服器確認。

## What Changes

- 前端檔案的回應加上 `Cache-Control: no-cache`:瀏覽器每次使用前都向伺服器確認。檔案沒變時伺服器回 304(只有標頭),有更新時一定取得新版。
- 卡圖(`/static/assets/`)內容不會改,不加這個標頭,維持現狀。
- API 回應不變。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `battle-api`:新增「前端資源每次確認更新」。

## Impact

- `src/gash/api/app.py`:一個 HTTP middleware。
- 測試:`tests/test_api.py` 或新測試檔。
- VPS 與單機版行為相同;Cloudflare 依來源的 `Cache-Control` 不在邊緣快取這些檔案。
