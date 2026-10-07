## Why

錄製時發現卡圖的兩個 HTTP 回應標頭問題:

- 正式環境的卡圖回應 `Content-Type: application/octet-stream`。映像檔是 `python:3.12-slim`:Python 3.12 把 `.webp` 放在非嚴格的 `common_types`,映像檔裡也沒有 `/etc/mime.types`,Starlette 以嚴格模式判斷不出類型,就退回 `application/octet-stream`。本機是 Python 3.14,內建表已有 `.webp`,所以沒被測試抓到。
- 卡圖沒有 `Cache-Control`,瀏覽器只能依 `Last-Modified` 推估快取時間。剛下載的卡圖推估出的時間很短,重新渲染時會先向伺服器確認,卡面短暫空白,在牌組編輯器切換篩選時最明顯。

## What Changes

- 卡圖 `.webp` 回應 `Content-Type: image/webp`,不依賴 Python 版本或系統的 MIME 對照檔。
- 卡圖的成功回應(200、304)帶 `Cache-Control: public, max-age=604800`(7 天)。找不到的卡圖(404)不帶長期快取,之後補上的卡圖才不會被瀏覽器或 Cloudflare 擋住。
- README 補充:同檔名換卡圖內容時,要到 Cloudflare 清除快取。
- 卡圖相關測試改用暫存的卡圖目錄,不再依賴本機有沒有下載卡圖(CI 沒有卡圖,`test_meta.py` 有兩個測試因此失敗)。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `battle-api`:新增「卡圖回應標頭」(Content-Type 與快取時間)。「前端資源每次確認更新」不變:卡圖仍不帶 `no-cache`。

## Impact

- 程式:`src/gash/api/app.py`(註冊 `.webp` 的 MIME type、middleware 對卡圖加上快取標頭)。
- 測試:`tests/test_static_cache.py`、`tests/test_meta.py`。
- 部署:Cloudflare 的 Browser Cache TTL 已設為 Respect Existing Headers,瀏覽器會收到 7 天;Cloudflare 邊緣依來源的 `max-age` 快取卡圖,VPS 流量下降。
- 文件:README「卡圖」、`battle-api/design.md`「前端資源快取」。
