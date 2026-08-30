## Why

`cards-json-from-ja` 完成後,審查發現三個資料層缺口:

1. `CardDef.name_en`/`effect_en` 欄位名稱標榜「英文」,但轉換後實際內容是日文(`cards_ja.csv` 的 `name_ja`/`effect_ja`),名不符實,容易誤導後續維護者以為這是英文資料。
2. `image_url` 目前靠「沿用轉換前 `data/cards.json` 舊值」這個一次性權宜作法取得——真正從 xlsx 讀取圖片連結的能力(`tools/extract_cards.py`)已在該次變更中刪除。往後任何情況(修正某張卡的連結、xlsx 內容更新)都無法再從權威來源重建這個欄位,只能手動編輯 JSON。
3. `cards_ja.csv` 的 `effect_icon_ja`(バトル/非バトル/ジャマー)欄位完全沒有被轉換進 `cards.json`。這個欄位標示一張術卡的效果是否該透過戰鬥宣告流程觸發,是修正 S-041/S-043/S-048/S-057/S-026 這幾張「非バトル」術卡誤植「不可防禦」問題(見 `spell-engine-fixes` 變更)的資料前置依賴——沒有這個欄位,引擎無從判斷「這張術卡不該走 declare_attack 流程」。

## What Changes

- `CardDef.name_en` → `name_ja`,`effect_en` → `effect_ja`:欄位定義、`_to_def` 讀取 key、`data/cards.json` 檔案本體 key、所有讀取點(引擎程式碼與測試斷言)一併更名。
- `tools/build_cards_json.py` 改為同時讀取 `data/cards_ja.csv`(主要資料)與 xlsx(僅讀取 `image_url`,透過儲存格 HYPERLINK/超連結取得),不再「沿用轉換前 `cards.json`」;`openpyxl` 依賴需要加回來。S-042(權威來源新增、xlsx 沒有對應列的卡)`image_url` 維持為 null,轉換不因此中止。
- 新增 `effect_icon` 欄位轉換:`cards_ja.csv` 的 `effect_icon_ja`(バトル/非バトル/ジャマー)→ `cards.json` 的 `effect_icon`(對應英文枚舉值)。此欄位目前只有資料,尚無任何引擎邏輯讀取——供 `spell-engine-fixes` 變更消費。

## Capabilities

### Modified Capabilities

- `card-data`:「卡片資料轉換」需求——`image_url` 規則由「沿用轉換前舊值」改為「直接從 xlsx 抽取」;新增 `effect_icon` 轉換規則;補充欄位命名為 `name_ja`/`effect_ja`。

## Impact

- `src/gash/engine/cards.py`:`CardDef` 欄位改名,`_to_def` 對應調整
- 引擎程式碼與測試:所有 `.name_en`/`.effect_en` 讀取點(約 10 處)改名
- `tools/build_cards_json.py`:新增讀取 xlsx 取得 `image_url` 的邏輯,新增 `effect_icon` 轉換
- `pyproject.toml`:重新加入 `openpyxl` 依賴
- `data/cards.json`:全面重新生成(欄位改名 + `effect_icon` 新增 + `image_url` 來源改變,但既有卡的 `image_url` 實際值不變,因為 xlsx 內容沒變)
- 不影響:`data/cards.zh-TW.json`、`tools/scrape_ja_effects.py`
