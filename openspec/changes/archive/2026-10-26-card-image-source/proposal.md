# Proposal

## Why

卡圖原本依 TTS 卡表(xlsx)A 欄的 Google Drive 連結下載,這些連結不歸本專案管理:M-050、P-130、P-146、PR-029 是非公開檔案(轉到登入頁),E-146 已失效(404),缺圖無法補。使用者已把卡表中所有卡圖(1557 張,含未實作系列,另補上 M-050)以 `{卡號}.webp` 存到自己維護的公開 Google Drive 資料夾,之後卡圖以這個資料夾為準,補圖、換圖只需在資料夾操作。

## What Changes

- 卡圖下載腳本改從使用者維護的公開資料夾(`1cXx4gpa41HiycU4hIN74xbp1Aj3hiE-k`)依檔名 `{卡號}.webp` 下載;資料夾中沒有該檔名的卡記入失敗清單。下載到的已是 WebP 時原樣存檔,不是 WebP 時仍轉成 WebP。
- 續抓(已有 `.webp` 跳過)、只認 `.webp`、失敗不中斷、缺圖以文字卡面顯示等行為不變。
- **BREAKING(資料欄位)**:移除 `cards.json` 的 `image_url`,轉換工具不再從 xlsx 讀取卡圖連結;引擎的卡片定義也移除該欄位(前端與引擎都沒有使用)。xlsx 仍是 `sets`(新卡)與英文卡名的來源。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `card-data`:「卡片資料轉換」移除 `image_url` 欄位規則與其情境;「卡圖資產與備援」的下載來源改為使用者維護的資料夾。

## Impact

- `tools/download_images.py`:來源改為資料夾(取得檔名 → 檔案 ID、下載、WebP 直接存檔)。
- `tools/build_cards_json.py`、`data/cards.json`:不再產生 / 含 `image_url`。
- `src/gash/engine/cards.py`:`CardDef` 移除 `image_url`。
- 測試:`tests/test_download_images.py`、`tests/test_build_cards_json.py`。
- 文件:README「資料管線」「卡圖」、`openspec/specs/card-data/design.md`。
