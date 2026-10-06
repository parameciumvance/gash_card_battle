## Why

卡圖副檔名是 `.jpg`,內容卻是 465×679 的 RGBA PNG,每張約 670KB,135 張共約 90MB。玩家第一次進對局時卡面要等一陣子才出現,手機網路下更明顯。卡圖都用透明通道做圓角,不能轉成 JPEG;轉成 WebP(q80)可以保留透明,總量降到約 11MB(每張約 83KB),放大檢視時文字與原圖看不出差別。

## What Changes

- **BREAKING** 卡圖檔一律為 WebP,檔名 `{卡號}.webp`。前端只請求 `.webp`,`/api/meta` 的 `assets.count` 只計 `.webp`。舊的 `.jpg` 卡圖不再使用,也不支援新舊格式混裝;所有環境(開發、VPS)都要用新的下載工具重新下載。
- 下載工具 `tools/download_images.py` 下載原圖後轉成 WebP(q80,保留透明)再存檔,產出 `{卡號}.webp`。
- 前端三處組卡圖網址的地方(卡片元件、聚焦動畫、規則頁)改為共用同一個函式。
- 卡背佔位圖 `frontend/back.jpg`(1329×1926、約 400KB)縮成與卡圖同寬(465px)。
- README 的卡圖安裝與 VPS 卡圖步驟改為 WebP,並寫明換格式時的上傳順序。
- 單機版不做相容處理:已裝 `.jpg` 卡圖的單機玩家更新後會以卡背佔位,需要換成 WebP 卡圖。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `card-data`:「卡圖資產與備援」改為下載後轉成 WebP、存成 `{卡號}.webp`。
- `battle-api`:「執行環境中繼資訊」的 `assets.count` 只計 `.webp`;「卡圖靜態資源外部化」與「前端資源每次確認更新」的卡圖網址改為 `.webp`。
- `battle-ui`:新增「卡圖網址」:卡片元件、聚焦展示、規則頁一律請求 `{卡號}.webp`。

## Impact

- 程式:`tools/download_images.py`、`src/gash/api/app.py`(`/api/meta`)、`frontend/app.js`、`frontend/anim.js`、`frontend/back.jpg`。
- 依賴:`pillow` 加入 `dev` optional dependencies,只有下載工具與測試用到,執行環境(映像檔、單機版)不需要。
- 測試:`tests/test_meta.py`、`tests/test_static_cache.py`、`tests/test_nonbattle_ui.py`、`tests/test_cheat_editor.py` 的卡圖網址;新增下載工具轉檔的測試。
- 部署:VPS 的 `card-assets` volume 要先放入 WebP 卡圖,再打新版 tag;新版上線後刪掉舊的 `.jpg`。
- 文件:README「單機發行」「卡圖」「資料管線」、`card-data/design.md`。
