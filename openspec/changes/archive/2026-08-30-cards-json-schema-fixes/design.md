## Context

`cards-json-from-ja` 把 `data/cards.json` 的權威來源從 xlsx 換成 `data/cards_ja.csv`,但轉換工具 `tools/build_cards_json.py` 對 `image_url` 採用「沿用轉換前既有 `cards.json` 舊值」的作法,而非重新從 xlsx 抽取——這是當時為了避免調查 wiki 卡圖連結可用性/授權範圍而選擇的最低風險做法。副作用是:讀 xlsx 的唯一工具 `tools/extract_cards.py` 已被刪除,`image_url` 從此變成「只能靠沿用鏈條往下傳」的資料,沒有任何工具能重新從權威來源(xlsx)生成它。

同時,`cards_ja.csv` 的 `effect_icon_ja` 欄位(バトル/非バトル/ジャマー,標示術卡效果是否透過戰鬥宣告流程觸發)在轉換時被整個忽略,沒有進入 `cards.json`。這個欄位是 `spell-engine-fixes` 變更判斷「這張術卡該不該走 declare_attack」的資料依據,必須先補上。

## Goals / Non-Goals

**Goals:**
- `name_en`/`effect_en` 改名為 `name_ja`/`effect_ja`,欄位名稱與實際內容語言一致。
- `image_url` 恢復成可從 xlsx 權威來源重新生成,不再依賴「沿用舊 cards.json」這條脆弱鏈路。
- `effect_icon` 進入 `cards.json`,值為英文枚舉,供後續變更消費。

**Non-Goals:**
- 不重新設計 `image_url` 本身的來源(仍是 Google Drive 連結,仍來自 xlsx 的儲存格超連結),只是恢復「讀取」這個能力,不改變連結內容或改用其他圖床。
- 不處理 `effect_icon` 在引擎邏輯上的消費(何時該讀、怎麼用)——那是 `spell-engine-fixes` 變更的範圍,這裡只負責把資料轉換出來。
- 不批次改名 `data/cards.zh-TW.json` 或其他檔案的欄位——那份檔案的 `name`/`name_ja`/`attr`/`effect` 欄位本來就是正確的中文/日文語意命名,不受影響。

## Decisions

- **`tools/build_cards_json.py` 直接同時讀取 `cards_ja.csv`(主要資料)與 xlsx(僅取 `image_url`),不再讀「轉換前的舊 `cards.json`」**:這樣每次重新生成都是「完全從權威來源重建」,不存在「必須先有上一版輸出才能產生下一版輸出」的自我依賴風險。取 `image_url` 的邏輯複用已刪除的 `extract_cards.py` 的 `parse_card_cell()` 判斷方式(A 欄儲存格若為 `=HYPERLINK(url, 卡號)` 公式則從公式取,否則讀儲存格的 hyperlink 物件),用卡號(去除 e/j 版本尾碼)比對 `cards_ja.csv` 的卡號做 join。`openpyxl` 依賴重新加回 `pyproject.toml`。
- **S-042 沒有對應 xlsx 列,`image_url` 為 null,不視為錯誤**:延續前次變更的既定行為,xlsx 是舊版權威來源,新卡本來就不會出現在裡面。
- **`effect_icon` 英文枚舉值:`battle`/`nonbattle`/`jammer`,空字串(魔物/夥伴/事件卡的多數情況)轉為 `null`**:直接音譯對應 `バトル`/`非バトル`/`ジャマー` 三個值,不額外創造抽象分類名稱,保持跟來源資料的可追溯性。
- **`CardDef` 欄位改名採「一次到位」,不留舊名相容別名**:專案目前只有一個消費端(自己的引擎與測試),沒有外部使用者需要相容期,保留別名只會增加維護負擔。

## Risks / Trade-offs

- **重新引入 `openpyxl` 依賴**:前次變更才剛把它移除,這次又加回來——這是因為前次移除的判斷前提(「不再有任何東西讀 xlsx」)被推翻了。風險低,純粹是依賴管理的來回,不影響功能。
- **`image_url` 改回從 xlsx 讀取後,實際輸出值理論上應與沿用舊值完全相同**(因為 xlsx 內容沒變,只是讀取方式從「間接沿用」改成「直接讀」)——轉換完成後 MUST 與目前 `data/cards.json` 的 `image_url` 逐筆 diff 比對,確認沒有意外差異,才能確認這次改動是純粹的架構修正、不是資料變更。
