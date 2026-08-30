## 1. 轉換工具

- [x] 1.1 建立 `tools/build_cards_json.py`,讀取 `data/cards_ja.csv`,依 design.md 的欄位對應規則(`power` 字串解析、`attr_name` 僅術卡填入、`image_url` 沿用舊值)輸出新的 `data/cards.json`。
      **驗收條件**:執行 `python tools/build_cards_json.py` 成功結束(exit code 0),不需手動修補輸出即可被 `src/gash/engine/cards.py` 載入(`CardDef` 建構不拋例外)。
- [x] 1.2 `power` 解析涵蓋四種格式(base/bonus/special/per_heads)與空字串。
      **驗收條件**:對 `cards_ja.csv` 全 135 筆執行轉換後,人工抽查至少各一筆四種格式各自的輸出(例如一張魔物卡的純數字、一張術卡的加號、`S-021` 的「特殊」、含「×」倍率後綴的卡),確認轉換後 `power_base`/`power_bonus`/`power_special` 三欄與來源語意一致。
- [x] 1.3 `attr_name` 只在 `type=="spell"` 填入,魔物/夥伴卡一律 `null`。
      **驗收條件**:轉換後 `data/cards.json` 中所有 `type != "spell"` 的卡,`attr_name` 均為 `null`;隨機抽查 3 張術卡確認 `attr_name` 等於該卡 `cards_ja.csv` 的 `attr_ja`。
- [x] 1.4 `image_url` 沿用轉換前 `data/cards.json` 的舊值,無對應舊卡號時為 `null`。
      **驗收條件**:轉換前後比對(用轉換前的備份檔案 diff),所有轉換前已存在的卡號 `image_url` 完全不變;S-042 的 `image_url` 為 `null`,轉換過程不拋例外、不中止。
- [x] 1.5 `sets`(前端產品篩選用的收錄產品清單)沿用轉換前 `data/cards.json` 的舊值,無對應舊卡號時為 `[]`。
      **驗收條件**:轉換前後比對,所有轉換前已存在的卡號 `sets` 完全不變;S-042 的 `sets` 為 `[]`;`frontend/app.js` 的產品篩選下拉選單在手動開啟前端後仍列出與轉換前相同的產品清單。
- [x] 1.6 `related_mamodo` 依卡片類型推導:術/夥伴/事件卡直接取 `related_mamodo_ja`;魔物卡以 `name_ja` 去除括號後綴推導。
      **驗收條件**:M-006/M-007(ゴフレ家族)、M-009/M-010(コルル家族)、M-024/M-025(ロブノス形態)、M-027/M-028(バルトロ形態)這 8 張卡的 `related_mamodo` 兩兩家族內相等,且與同家族至少一張術卡或夥伴卡的 `related_mamodo_ja` 相等;所有指示術(`related_mamodo_ja == "コマンド"`)的 `related_mamodo` 等於新的 `COMMAND_ALL` 常數值。

## 2. 產生並核對 `data/cards.json`

- [x] 2.1 執行轉換工具,重新產生 `data/cards.json`。
      **驗收條件**:新檔案恰含 135 筆,卡號集合與 `data/cards_ja.csv` 完全一致(用一行腳本或手動 diff 兩邊排序後的卡號清單,無遺漏、無多餘)。
- [x] 2.2 抽查已知 JA/EN 數值落差卡號(至少 S-017、E-027、M-013)在新資料中已改為 JA 正確值。
      **驗收條件**:三張卡的對應欄位(S-017 效果觸發時機、E-027 費用、M-013 基礎魔力)手動比對 `cards_ja.csv` 原始值與新 `cards.json` 值一致。
- [x] 2.3 備份轉換前的 `data/cards.json`(供 2.1/1.4 diff 使用),完成核對後可移除備份。
      **驗收條件**:備份檔案在完成 1.4/2.1 的 diff 核對前存在;核對完成並記錄於本任務清單後刪除,不留在最終提交中。

## 3. 修正寫死英文字面值(原估 8 個,實作時全文複查發現另有 3 組遺漏,共 11 組)

- [x] 3.1 `src/gash/engine/cards.py:21` `COMMAND_ALL = "Command: All"` → `"コマンド"`。
      **驗收條件**:全文搜尋 `Command: All` 於 `src/` 下無殘留;既有涵蓋指示術判定的測試(`tests/test_cards.py` 或 `tests/test_engine*` 中含指示術情境的案例)重跑通過。
- [x] 3.2 `src/gash/engine/effects/mamodo.py:322` `attr_name == "Wood"` → `== "木"`。
      **驗收條件**:M-023 的屬性相容性判定有至少一個測試案例(既有或新增)以「木」屬性術卡觸發並斷言其行為與修正前對「Wood」判定的既有測試等價;測試通過。
- [x] 3.3 `src/gash/engine/effects/mamodo.py:394` `related_mamodo == "Zatch Bell"` → `== "ガッシュ・ベル"`;`mamodo.py:395` `"Zaker" in name_en` → `"ザケル" in name_ja`(或對應日文欄位)。
      **驗收條件**:涉及葛虛(ガッシュ)/薩克魯(ザケル)身分判定的既有測試(如 `tests/test_cards.py` 中以 M-001 或其夥伴卡觸發的案例)重跑通過,且新增或確認至少一個案例實際執行到該分支(而非只改字串未被任何測試觸發)。
- [x] 3.4 `mamodo.py:254/256/261` 三處 `"Tia"` → `"ティオ"`。
      **驗收條件**:涉及提歐(ティオ)身分判定的效果(對應魔物卡號,查 `cards_ja.csv` 確認卡名)有測試實際觸發該三處分支之一,重跑通過。
- [x] 3.5 `mamodo.py:266/268/273` 三處 `"Hyde"` → `"ハイド"`。
      **驗收條件**:涉及海爾(ハイド)身分判定的效果有測試實際觸發該三處分支之一,重跑通過。
- [x] 3.6 `src/gash/engine/effects/partners.py:14` `"Zatch Bell"` → `"ガッシュ・ベル"`。
      **驗收條件**:該判定所屬效果(查對應卡號)有測試觸發,重跑通過。
- [x] 3.7 `partners.py:41,182` 兩處 `"Brago"` → `"ブラゴ"`。
      **驗收條件**:布拉哥(ブラゴ)身分判定所屬效果有測試觸發兩處分支之一,重跑通過。
- [x] 3.8 `partners.py:203` `data={"spell_name": "Biraitsu"}` → `data={"spell_name": "ビライツ"}`,並確認下游讀取點(`engine.py:453/584/664` 讀 `sb.data.get("spell_name")` 並與 S-042 名稱比對之處)同步使用日文值比對。
      **驗收條件**:S-042(比雷茲/ビライツ)相關的施放判定有測試觸發此比對鏈路,重跑通過;全文搜尋 `Biraitsu` 於 `src/` 下無殘留。
- [x] 3.9 `partners.py:50`(P-004 相容判定 `_battle_attack_by(g, p, "Gofure")`)`"Gofure"` → `"ゴフレ"`。
      **驗收條件**:P-004(連次)搭配 M-006/M-007(ゴフレ家族)攻擊的傷害加倍效果有測試觸發,重跑通過;全文搜尋 `"Gofure"` 於 `src/` 下無殘留。
- [x] 3.10 `mamodo.py:79`(M-008 スギナ自身待命效果 `data={"mamodo": "Sugino", ...}`)與 `partners.py:62`(P-005 `data={"mamodo": "Sugino"}`)兩處 `"Sugino"` → `"スギナ"`。
      **驗收條件**:M-008/P-005 所屬效果(スギナ家族費用/魔力減免)有測試觸發其中至少一處分支,重跑通過;全文搜尋 `"Sugino"` 於 `src/` 下無殘留。
- [x] 3.11 `partners.py:89`(P-007 `data={"mamodo": "Fein", ...}`)`"Fein"` → `"フェイン"`。
      **驗收條件**:P-007 所屬效果(菲恩/フェイン家族魔力加值)有測試觸發,重跑通過;全文搜尋 `"Fein"` 於 `src/` 下無殘留。

## 4. 淘汰舊抽取管線

- [x] 4.1 刪除 `tools/extract_cards.py`。
      **驗收條件**:檔案不存在;`git grep -n extract_cards` 於整個 repo(含 README、AGENTS.md、CI 設定)無結果。
- [x] 4.2 移除 `openpyxl` 依賴。
      **驗收條件**:`pyproject.toml` 不含 `openpyxl`;`git grep -n openpyxl` 於 `src/`、`tools/`、`tests/` 無結果。

## 5. 測試核對

- [x] 5.1 重跑全部既有測試套件。
      **驗收條件**:`pytest` 執行後,失敗案例清單已逐一檢視——每個失敗要嘛是「斷言記錄舊 EN 數值,已依 `cards_ja.csv` 改斷言」,要嘛是 3.x 任務尚未完成的字面值分支(不應該有第三類原因不明的失敗)。
      實際結果:轉換後首次重跑,196 個舊測試中有 2 個失敗,皆為「card 數量從 134 → 135」的連帶斷言(`test_deck.py`/`test_meta.py`),無第三類原因不明的失敗。
- [x] 5.2 修正因 JA/EN 數值落差變紅的測試斷言。
      **驗收條件**:每一處被修改的斷言,PR/commit 中可指出對應的 `cards_ja.csv` 來源值作為修改依據(不得無來源地調整數字讓測試通過)。
      實際結果:`test_deck.py::test_card_db_has_134_cards` 改名為 `test_card_db_has_135_cards`,卡數斷言改為 135;原本檢查 `effect_en` 含特定英文字的三個子斷言(S-025/E-018/E-022)改為檢查對應的日文措辭(依 `cards_ja.csv` 該三卡的 `effect_ja` 原文);`test_meta.py::test_meta_dev_mode` 的卡圖齊全斷言改為容許少 1 張(S-042 無舊卡圖可沿用,design.md 已記錄此為已知情況,非測試斷言錯誤)。另外,實作階段全文複查 `mamodo.py`/`partners.py` 時發現 3 組先前遺漏的寫死字面值(`"Gofure"`/`"Sugino"`/`"Fein"`,見任務 3.9–3.11),以及 3 個修正後完全沒有測試觸及的分支(M-021/ハイド、M-023/木屬性相容、P-015→S-042 任意頁用術),已在 `tests/test_level2.py` 新增 3 個測試補上覆蓋,並逐一以「暫時改回英文字面值 → 確認測試會失敗 → 改回日文」的方式驗證這些新測試真的會抓到迴歸,而非空過。
- [x] 5.3 全數測試最終通過。
      **驗收條件**:`pytest` 全部通過(exit code 0),總測試數與修正前一致或因新增覆蓋而增加,不因刪除案例而減少既有覆蓋範圍。
      實際結果:199 個測試全數通過(原 196 個,+1 改名無增減、+3 新增覆蓋分支測試)。
