## 1. 規格

- [x] 1.1 `card-data` 新增「日文權威資料抓取(atwiki)」需求與情境(見 specs/card-data/spec.md)

## 2. 資料頭解析重寫

- [x] 2.1 `classify_token`:token 封閉分類(類型/級別/費用/傷害/power/元素屬性/效果 icon/回合欄位),不認得直接 raise
- [x] 2.2 `parse_header`:依卡片類型必填欄位(event/術 需要 ad;魔物/術 需要 power),先讀 1 行、不夠再讀第 2 行,仍不夠則 raise
- [x] 2.3 power_bonus/power_base/power_special 合併為單一 power 欄位,保留格式標記(純數字/加號/特殊/x 後綴)
- [x] 2.4 `parse_card_page` 改用 `parse_header` 的回傳消耗行數決定 body_lines 起點(不再固定「術卡才讀第 2 行」)

## 3. 測試

- [x] 3.1 `tests/test_scrape_ja_effects.py` 改用內嵌合成 HTML(不依賴 `ref/` 下未版控的真實頁面)測試 `parse_product_page`(多分類卡號/連結解析)
- [x] 3.2 測試 `parse_header` 單行滿足必填欄位、跨兩行才滿足、event 卡第 1 行即滿足(對應 E-015)、魔物卡不需要 ad
- [x] 3.3 測試 power 四種格式(純數字/加號/特殊/x 後綴)
- [x] 3.4 測試未知標籤與必填欄位缺漏兩種報錯情境
- [x] 3.5 測試 `parse_card_page` 端到端(術卡單行/跨行資料頭、event 卡第 2 行不誤判為資料頭、魔物卡技能文字不誤判)
- [x] 3.6 執行 `python -m pytest` 確認全數通過(185 passed)

## 4. 收尾

- [x] 4.1 執行 `openspec validate ja-source-scraper` 確認格式正確
- [x] 4.2 提醒使用者:`data/cards_ja.csv` 欄位結構已改變,需刪除舊檔並整批重新執行 `tools/scrape_ja_effects.py`

## 5. 實際整批抓取後的修正(S-021/S-040)

- [x] 5.1 `POWER_X_RE` 修正接受乘號「×」(U+00D7),不再只認字母 x(S-040 實際格式)
- [x] 5.2 新增 `KNOWN_DATA_GAPS` 已知資料缺漏清單機制,登記 S-021(對照英文資料核對過的官方頁面漏刊 power)
- [x] 5.3 補測試:× 後綴、已知缺漏覆寫套用、未登記卡號仍照常 raise
- [x] 5.4 執行 `python -m pytest` 確認全數通過(188 passed)
