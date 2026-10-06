## Context

- 卡圖來源是 `cards.json` 的 Google Drive 連結,原圖是 465×679 的 RGBA PNG,135 張都用透明通道做圓角。下載工具原樣存成 `{卡號}.jpg`(副檔名與內容不符),每張約 670KB,共約 90MB。
- 卡圖是另外安裝的外部資源:開發環境在 `frontend/assets/cards/`,VPS 在 `card-assets` volume,單機版在使用者資料夾。映像檔與單機版 zip 都不含卡圖。
- 前端有三處自行組卡圖網址:`app.js` 的卡片元件、規則頁的 `artUrl()`,以及 `anim.js` 的聚焦展示。
- `/api/meta` 以 `*.jpg` 計算 `assets.count`,首頁依此判斷卡圖是否齊全。
- 專案負責人的決定:統一改格式,所有環境重新下載,不支援新舊格式混裝,單機版不做相容處理。

## Goals / Non-Goals

**Goals:**

- 卡圖總量從約 90MB 降到約 11MB,保留透明圓角,放大檢視時文字清楚。
- 全系統只有一種卡圖格式,前端只有一個地方組卡圖網址。
- 執行環境不增加依賴。

**Non-Goals:**

- 不支援 `.jpg` 卡圖,也不提供把既有 `.jpg` 轉成 WebP 的工具(重新下載即可)。
- 不改卡圖的 HTTP 快取標頭。
- 不處理單機版玩家手上的舊卡圖包。

## Decisions

### D1:WebP q80(有損,保留透明)

本機 135 張實測(Pillow,`method=6`):

| 格式 | 總量 | 每張平均 |
|---|---|---|
| 原圖 PNG | 90.3MB | 669KB |
| WebP 無損 | — | 約 460KB(S-001) |
| WebP q92 | 17.6MB | 130KB |
| WebP q88 | 14.8MB | 110KB |
| WebP q80 | 11.2MB | 83KB |

E-020 的效果文區塊放大兩倍比對原圖、q80、q88,肉眼看不出差別,因此取 q80。

- JPEG:沒有透明通道,圓角會變成色塊。
- WebP 無損:只省三成。
- AVIF:更小,但 Pillow 要另外裝外掛才能編碼;WebP 已經把總量降到原本的八分之一。

### D2:只認 `.webp`,不做相容

前端只請求 `{卡號}.webp`,`/api/meta` 只計 `.webp`,下載工具續抓時也只看 `.webp` 是否存在。

曾考慮由 `/api/meta` 回報已安裝的格式,或讓前端在 `.webp` 失敗時改試 `.jpg`,讓舊卡圖包繼續可用。專案負責人決定不做:所有環境重新下載,系統只維持一種格式。

### D3:在下載工具轉檔,執行環境不轉

`tools/download_images.py` 下載原圖後在記憶體中轉成 WebP 再寫檔,原圖不落地。`pillow` 放在 `dev` optional dependencies,只有工具與測試用到。

曾考慮由伺服器在啟動時把目錄裡的 PNG 轉成 WebP,但這會讓映像檔與單機版多一個依賴、拖慢啟動,還要寫入卡圖 volume。

轉檔是一個獨立函式(輸入原圖 bytes,回傳 WebP bytes),測試直接呼叫它,不需要連網。

### D4:前端共用 `artUrl()`

`app.js` 只保留一個 `artUrl(num)`,卡片元件與規則頁都用它。`anim.js` 本來就在執行時使用 `app.js` 的全域函式(`t`、`pname`),聚焦展示也改呼叫 `artUrl()`。

### D5:卡背縮圖

`frontend/back.jpg` 是 1329×1926、約 400KB,缺圖佔位和對手卡背都會用到。縮成 465×674(與卡圖同寬),維持 JPEG(卡背沒有透明),q85 約 90KB。

## Risks / Trade-offs

- [新版上線時 VPS 還沒有 WebP 卡圖,所有卡面變成卡背] → README 寫明順序:先把 WebP 放進 volume(與舊 `.jpg` 並存,舊版照常讀 `.jpg`),再打 tag;新版上線後才刪 `.jpg`。
- [已裝 `.jpg` 卡圖的單機玩家更新後全部以卡背佔位] → 專案負責人決定接受。首頁會提示卡圖不完整,遊戲照常。
- [重新下載 135 張時 Google Drive 限流] → 工具本來就支援續抓與失敗清單,重跑即可補齊。
- [q80 的壓縮痕跡在細字上可見] → 已在 2 倍放大下比對過;日後若有特定卡看不清,只需調整工具的品質參數重新下載。

## Migration Plan

1. 開發環境:`pip install -e ".[dev]"` 裝 `pillow`,執行 `python tools/download_images.py` 重新下載。舊的 `.jpg` 不再被讀取,可以刪掉。
2. VPS(打 tag 前):本機下載好 WebP,`scp` 到 VPS,`docker compose cp /tmp/cards/. app:/app/assets/cards/` 放進 volume。
3. 打新版 tag,等 watchtower 換上新映像檔,確認卡面正常。
4. 刪掉 volume 裡的舊 `.jpg`:`docker compose exec app sh -c 'rm -f /app/assets/cards/*.jpg'`。

回退:舊版映像檔讀 `.jpg`。若在步驟 4 之前回退,卡圖照常;步驟 4 之後回退,要重新放回 `.jpg`。
