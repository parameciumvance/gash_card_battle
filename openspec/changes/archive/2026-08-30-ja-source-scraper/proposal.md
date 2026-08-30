## Why

`tools/scrape_ja_effects.py` 是這次為了核對/取得日文權威資料(atwiki)而寫的抓取腳本,已實際跑過並修正過幾輪解析邏輯(產品頁收錄清單、個別卡頁的數值/攻防/效果/風味/收錄產品拆解、未知標籤警告機制),但目前沒有 openspec 規格記錄它的行為契約,也沒有自動化測試——邏輯是靠人工拿真實頁面核對出來的,之後改動容易在不知不覺間破壞既有行為。補上規格與測試,讓這支工具跟專案其他資料管線(`extract_cards.py`/`download_images.py`)一樣有明確的行為依據。

## What Changes

- 在 `card-data` capability 新增一個需求,記錄 `tools/scrape_ja_effects.py` 的行為契約:產品頁收錄卡清單解析、資料頭拆解規則(封閉分類 token、依卡片類型的必填欄位、最多跨 2 行)、未知標籤與缺漏必填欄位一律報錯、power 三欄位合併為單一欄位、輸出 CSV 的欄位與續抓行為。
- 補這份規格的過程中發現既有邏輯不符合新確認的規則(攻防列的「不認得就當旗標記錄+警告」太寬鬆、屬性欄位是開放兜底桶會吃進不該吃的 token、power 拆三個互斥欄位不好用、event 卡完全沒解析 AD),於是**同步重寫 `tools/scrape_ja_effects.py` 的資料頭解析邏輯**,改為 token 封閉分類 + raise(不再警告放行)+ 依類型必填欄位 + 單一 power 欄位。
- 重寫 `tests/test_scrape_ja_effects.py`:針對新的純解析函式(`parse_product_page`/`parse_header`/`parse_card_page`)以內嵌的最小合成 HTML 片段測試(不依賴網路、不依賴 `ref/` 下未版控的真實頁面存檔),涵蓋單行/跨行必填欄位判斷、event 卡與魔物卡不需要的欄位、power 四種格式、未知標籤與必填欄位缺漏兩種報錯情境。
- **不包含**:`main()` 的網路抓取/CSV 讀寫流程本身不寫自動化測試(維持跟 `extract_cards.py`/`download_images.py` 一致的慣例,一次性工具只测纯邏輯函式,不 mock 網路)。
- **不包含**:尚未處理的 S-036/S-005 スターター專屬卡補抓(另外單獨處理,不在此變更範圍)。
- **BREAKING**:`data/cards_ja.csv` 欄位結構改變(移除 power_bonus/power_base/power_special/flags_ja,新增 power/effect_icon_ja),既有已抓取的 CSV 需整批重抓(部分先前「成功」的卡片這次可能因出現尚未登記的標籤而報錯,需人工補登記後重跑)。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `card-data`:新增「日文權威資料抓取(atwiki)」需求,記錄 `scrape_ja_effects.py` 的解析契約。

## Impact

- `openspec/specs/card-data/spec.md`:新增需求與情境
- `tools/scrape_ja_effects.py`:資料頭解析邏輯重寫(見上)
- `tests/test_scrape_ja_effects.py`:重寫,純函式測試
- `data/cards_ja.csv`:欄位結構改變,需整批重新抓取(不在此變更內執行,由使用者另外重跑)
