# Tasks

## 1. 下載腳本

- [x] 1.1 先寫測試並確認修改前失敗(`tests/test_download_images.py`,以固定的資料夾 HTML 樣本與假的下載函式代替網路):解析樣本得到檔名 → 檔案 ID;依卡號下載資料夾中的 `{卡號}.webp` 並原樣存檔;資料夾中沒有的卡記入失敗清單且繼續;下載到 PNG 時轉成 WebP;續抓只認 `.webp`;資料夾頁面解析不到任何檔案時報錯結束
- [x] 1.2 `tools/download_images.py` 改為以資料夾常數取得清單後下載(design「以 `embeddedfolderview` 取得檔名 → 檔案 ID」「WebP 原樣存檔」),更新模組說明;1.1 的測試通過
- [x] 1.3 實際執行一次:暫時移走本機數張 `.webp` 後重跑腳本,確認從資料夾補回、內容與資料夾檔案相同,且 M-050 下載成功

## 2. 移除 image_url

- [x] 2.1 `tests/test_build_cards_json.py` 改為斷言轉換結果沒有 `image_url`、`sets` 照舊取自 xlsx,確認修改前失敗
- [x] 2.2 `tools/build_cards_json.py` 移除 `image_url`(`load_tts` 只回傳 `sets`),`src/gash/engine/cards.py` 的 `CardDef` 移除 `image_url`;重跑 `python tools/build_cards_json.py`,`git diff data/cards.json` 只有 `image_url` 被移除;`python -m pytest tests -m "not slow and not browser" -q` 通過

## 3. 文件與收尾

- [x] 3.1 README「資料管線」與「卡圖」改寫:卡圖來源為資料夾、補圖在資料夾操作、刪除 M-050 抓不到的說明與 xlsx 卡圖連結的描述
- [x] 3.2 全套 `python -m pytest tests -q` 通過;`openspec validate --all --strict` 沒有新增失敗
- [x] 3.3 Reconciliation:`card-data/design.md` 的「卡圖」一節記來源資料夾、取得清單的方式與理由、WebP 原樣存檔;刪除第三彈「M-050 沒有卡圖」的說明;資料轉換相關描述中移除 `image_url`;capability map 的 `card-data` 摘要如需更新一併更新

## Workflow follow-up

- 使用者指示後歸檔並提交(歸檔時同步 delta spec)。
