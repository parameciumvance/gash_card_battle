## Context

- 卡圖由 `app.py` 的 `StaticFiles` 掛在 `/static/assets/`。Starlette 以 `mimetypes.guess_type()`(嚴格模式)決定 `Content-Type`,判斷不出時退回 `application/octet-stream`。
- `.webp` 在 Python 3.12 的內建表屬於非嚴格的 `common_types`(3.13 起才進嚴格表)。`python:3.12-slim` 沒有 `/etc/mime.types`,所以正式環境判斷不出。
- 既有 middleware 對前端資源加 `no-cache`,卡圖排除在外、沒有任何 `Cache-Control`。
- Cloudflare 的 Browser Cache TTL 設為 Respect Existing Headers;`.webp` 屬於 Cloudflare 預設會在邊緣快取的副檔名,邊緣快取時間依來源的 `max-age`。

## Goals / Non-Goals

**Goals:**

- 卡圖在任何 Python 版本下都回 `image/webp`。
- 卡圖重新渲染時直接使用瀏覽器快取,不必向伺服器確認。

**Non-Goals:**

- 不改前端資源的 `no-cache`,也不改 API 回應。
- 不做卡圖網址版本化(例如 `?v=`);卡圖很少換內容,換的時候清 Cloudflare 快取即可。

## Decisions

### D1:啟動時註冊 `.webp`

`app.py` 載入時呼叫 `mimetypes.add_type("image/webp", ".webp")`,寫入 Python 全域的嚴格對照表,`StaticFiles` 之後就判斷得出。比起自己包一層 `StaticFiles` 指定 `media_type`,這樣改動最小,且不影響其他檔案類型。

### D2:成功回應才帶 7 天快取

middleware 對 `/static/assets/` 之下、狀態碼 200 或 304、且回應還沒有 `Cache-Control` 的請求,加上 `public, max-age=604800`。

- 7 天:卡圖內容固定,只有換格式或重新下載才會變。換格式時網址跟著變;同檔名換內容時,README 說明要清 Cloudflare 快取,瀏覽器端最久 7 天後更新。
- 不用 `immutable`:同檔名仍可能換內容,保留過期後以 `ETag` 確認的機會。
- 404 不帶:Cloudflare 會依 `max-age` 快取 404,缺圖時若帶 7 天,之後補上卡圖也要等一週才看得到。
- 304 也帶:瀏覽器以條件請求確認後,用新的 `max-age` 更新快取時間。

### D3:測試不依賴本機卡圖

CI 沒有卡圖,既有的 `test_card_art_served_from_assets_mount` 與 `test_meta_dev_mode`(斷言 `installed` 為 true)在 CI 會失敗。新的標頭測試用暫存目錄放一張測試用 WebP,把 `/static/assets/` 掛載的 `StaticFiles` 暫時指向該目錄;既有兩個測試一併改用同一個方式,`test_meta_dev_mode` 只檢查欄位與型別。

## Risks / Trade-offs

- [同檔名換卡圖後,玩家最久 7 天看到舊圖] → README 寫明換圖後到 Cloudflare 清快取;瀏覽器端的舊快取最多 7 天自然過期。
- [`mimetypes.add_type` 改的是行程全域的對照表] → 只新增 `.webp`,與 Python 3.13 之後的內建結果相同。
