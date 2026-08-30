## 1. 欄位改名

- [x] 1.1 `src/gash/engine/cards.py`:`CardDef.name_en`→`name_ja`,`effect_en`→`effect_ja`,`_to_def` 對應讀取 key 一併改。
      **驗收條件**:`grep -rn "name_en\|effect_en" src/ tests/ tools/` 無殘留(除了本次變更說明文件外)。
- [x] 1.2 找出所有 `.name_en`/`.effect_en` 讀取點(引擎程式碼與測試斷言)改為 `.name_ja`/`.effect_ja`。
      **驗收條件**:`pytest` 全數通過,無因改名遺漏造成的 `AttributeError`。

## 2. image_url 改回從 xlsx 抽取

- [x] 2.1 `tools/build_cards_json.py` 新增讀取 xlsx 的邏輯(複用已刪除的 `extract_cards.py` 的 `parse_card_cell()` 判斷方式),以卡號(去除 e/j 尾碼)比對 `cards_ja.csv` 的卡號取得 `image_url`。
      **驗收條件**:執行轉換後,`image_url` 有值的卡號數與轉換前一致或更多。
      實際結果:意外發現 S-042 其實一直存在於 xlsx(`S-042e`/`S-042j` 兩列,效果文字與 `cards_ja.csv` 描述的規則完全吻合),只是 Sets 欄位標籤是 `[C]` 而非舊版 `extract_cards.py` 的 `INCLUDE_SETS = {"Level 1", "Level 2", "Series 1 Level 2"}` 過濾條件涵蓋的格式,才被排除、誤以為「英文來源沒有這張卡」。直接讀 xlsx 反而把 S-042 的卡圖連結也找回來了(先前沿用舊 `cards.json` 時 S-042 一直是 null)——這是本次改用直接讀取取代沿用舊值後的正向副作用,不是問題。
- [x] 2.2 `pyproject.toml` 重新加入 `openpyxl` 依賴。
      **驗收條件**:`python tools/build_cards_json.py` 可正常執行,不因缺少 `openpyxl` 報錯。
- [x] 2.3 轉換後的 `image_url` 逐筆比對轉換前(沿用舊值版本)的 `data/cards.json`,確認完全一致。
      **驗收條件**:除 S-042(見 2.1 說明,從 null 變為有值,屬預期內的正向差異)外,其餘 134 張卡的 `image_url` 逐筆比對完全相同。

## 3. effect_icon 轉換

- [x] 3.1 `tools/build_cards_json.py` 新增 `effect_icon` 欄位轉換(バトル→battle、非バトル→nonbattle、ジャマー→jammer、空字串→null)。
      **驗收條件**:抽查 S-041(非バトル→nonbattle)、M-001(バトル→battle)、M-026(ジャマー→jammer)、P-001(空值→None),皆符合對應規則。
- [x] 3.2 `CardDef` 新增 `effect_icon` 欄位(暫無引擎邏輯讀取,僅資料落地)。
      **驗收條件**:`card_db()` 載入後每張卡的 `effect_icon` 可正確讀出對應值,不拋例外。

## 4. 收尾

- [x] 4.1 重新產生 `data/cards.json` 並跑過全部既有測試。
      **驗收條件**:`pytest` 全數通過。
      實際結果:199 個測試全數通過。
- [x] 4.2 `openspec validate cards-json-schema-fixes` 確認格式正確。
      **驗收條件**:指令回報 valid,無錯誤。
