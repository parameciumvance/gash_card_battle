# Design

## Context

- `tools/download_images.py` 目前讀 `cards.json` 的 `image_url`(由 `build_cards_json.py` 從 TTS 卡表 xlsx 的 A 欄超連結取得),以 `https://drive.google.com/uc?export=download&id=<ID>` 下載 PNG 原圖,在記憶體轉成 WebP q80 存檔。
- 使用者維護的資料夾 `1cXx4gpa41HiycU4hIN74xbp1Aj3hiE-k` 公開分享,內含 1557 個 `{卡號}.webp`。這些檔案就是同一套 WebP q80 轉檔的結果(第一、二彈 135 張由使用者先前上傳,其餘由本專案一次性下載轉檔後上傳;M-050 由使用者補上)。遊戲用的 `{卡號}.webp` 對應卡表中 j 版優先的那一列,和 `load_tts` 的選法相同;其他版本以原始編號命名(如 `M-xxxe.webp`),腳本不使用。
- `image_url` 只有下載腳本使用;`CardDef.image_url` 在引擎與前端都沒有讀取。

## Goals / Non-Goals

**Goals:** 卡圖只有一個來源(使用者的資料夾);腳本不需要 API 金鑰或登入。

**Non-Goals:** 不改卡圖格式、檔名、`frontend/assets/cards/` 的位置與 `/api/meta` 的計數;不處理部署端的補圖流程(README 既有的 `docker compose cp` 不變);不改 xlsx 作為 `sets` 與英文卡名來源的角色。

## Decisions

### 以 `embeddedfolderview` 取得檔名 → 檔案 ID

公開資料夾的 `https://drive.google.com/embeddedfolderview?id=<資料夾 ID>` 回傳 HTML,每個檔案有 `id="entry-<檔案 ID>"` 與 `flip-entry-title` 檔名。實測一次回傳全部 1557 筆,沒有分頁。

- 替代方案:Drive API v3 `files.list` 需要 API 金鑰(要放進設定或環境變數);在 repo 維護「卡號 → 檔案 ID」對照表,則每次補圖都要改 repo,違背「以資料夾為準」。
- 這是非正式介面,格式可能改變。解析不到任何檔案時,腳本直接報錯結束(不是把每張卡都記成失敗),讓問題一眼可見。

### 資料夾 ID 寫成腳本常數

資料夾是專案唯一的卡圖來源,不是部署設定,不放環境變數。換資料夾時改常數。

### WebP 原樣存檔,其他格式才轉檔

資料夾中的檔案已經是 q80 WebP,再轉一次只會多一次有損壓縮。以檔頭(`RIFF....WEBP`)判斷;不是 WebP 時(例如將來有人放 PNG 進資料夾,但檔名仍是 `.webp`)交給既有的 `to_webp()`,維持「卡圖一律是 WebP」的規格。

### 移除 `image_url`

`cards.json`、`build_cards_json.py`、`CardDef` 一起移除,避免出現兩個看似都能當來源的地方。`load_tts` 改為只回傳 `sets`;原本「沒有連結的列跳過」的條件隨之拿掉,沒有卡圖連結的列也能提供 `sets`(現有卡都有連結,`cards.json` 結果不變,由重跑轉換後比對確認)。

## Risks / Trade-offs

- [Google 改變 `embeddedfolderview` 的 HTML] → 解析不到時明確報錯;測試以固定的 HTML 樣本驗證解析,修正時只動解析函式。
- [資料夾被改成非公開] → 同上,列表或下載失敗,報錯 / 記入失敗清單,遊戲照常以文字卡面顯示。
- [資料夾中同名檔案重複] → 以第一筆為準;目前 1557 個檔名皆唯一。

## Migration Plan

已下載的 `frontend/assets/cards/*.webp` 不受影響(續抓跳過)。部署端卡圖 volume 不變。要以資料夾的版本整批更新時,刪除本機 `.webp` 後重跑腳本。
