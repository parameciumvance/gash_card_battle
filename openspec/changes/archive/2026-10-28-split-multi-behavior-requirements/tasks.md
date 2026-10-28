# Tasks

## 1. 核對拆分前後等價

- [x] 1.1 逐條比對 10 條被拆分需求與第 4 / 5 批兩條被合併需求的原說明:每一句都出現在某條新需求裡,或列在 design.md「文字調整」中;發現未列出的差異時,修正 delta 或補進「文字調整」。完成條件是比對結果(每條原需求 → 新需求的對照)無遺漏
- [x] 1.2 以腳本比對情境:各 capability 中 REMOVED 原需求的情境名稱集合,與 ADDED 新需求的情境名稱集合相同(只多出「輪到自己時的行動權標示」「擲幣倍率型 power 保留後綴」兩個),且沒有任何情境出現在兩條需求;情境內文逐字未改
- [x] 1.3 確認兩個新情境描述的是現有行為:`python -m pytest tests/test_timing_ui.py -k acting_label tests/test_scrape_ja_effects.py -k "power" -q` 通過(瀏覽器測試需要 playwright 與 Chromium;無法執行時改為閱讀斷言確認,並在此註明)
- [x] 1.4 確認 MODIFIED 的 4 條(「操作與決策互動」「事件動畫」「卡圖網址」「構築器顯示卡號與中級 / 上級」)與主 spec 的差異只有引用名稱,「個別卡片的行動與選項」只有「第 4 批新增的」一處改寫:以 `diff` 比對 delta 區塊與主 spec 區塊
- [x] 1.5 `openspec validate split-multi-behavior-requirements --strict` 通過

## 2. 更新引用

- [x] 2.1 測試檔開頭說明與分節註解中的舊需求名稱改為新名稱(`tests/test_auto_open_pick_ui.py`、`test_builder_card_info_ui.py`、`test_choice_ui.py`、`test_feedback_ui.py`、`test_i18n_languages.py`、`test_landing_ui.py`、`test_level3_ui.py`、`test_npc_ui.py`、`test_rules_page.py`、`test_rules_ui.py`、`test_spotlight_ui.py`、`test_timing_ui.py`、`test_turn_dial_ui.py`),依各檔實際測的行為選對應的新需求;只改註解,`git diff --stat tests` 確認只動到註解行,`python -m pytest tests/test_rules_page.py tests/test_i18n_languages.py -q` 通過
- [x] 2.2 `todo.md`:「規格整理」一項改寫為完成狀態或移除(目標改為「拆開混了多個行為的需求」,本 change 完成);新增「`card-effects` 以批次命名的解讀需求(第 1 / 2 / 4 批的解讀與限制)依卡或機制重整」;新增「規則頁 spec 寫三種語言的內容檔,實際有 zh-TW / zh-CN / en / ja 四個,待決定是否修正 spec」

## 3. Reconciliation 與歸檔(指南 §13)

- [x] 3.1 同步 delta spec 回 `battle-ui`、`card-data`、`effect-tree`、`deck-builder` 主 spec;`openspec validate --all --strict` 通過,說明過長的提示只剩 design.md 列出保留的 7 條
- [x] 3.2 Reconcile 受影響 capability 的 design:`local-test-mode/design.md` 的「金手指面板」改指向新需求名稱;確認 `battle-ui/design.md`、`card-data/design.md`、`effect-tree/design.md` 沒有以舊需求名稱引用規格(節名作為設計主題保留);行為沒有改變,不新增「行為決定與理由」
- [x] 3.3 以舊需求名稱 grep `openspec/specs`、`openspec/capability-map.md`、`docs`、`tests`、`README.md`,確認只剩一般用語(畫面名稱「規則頁」「首頁入口」等)與封存區;確認 capability map 不需更新(責任與覆蓋程度不變)
- [x] 3.4 依使用者指示歸檔並提交
