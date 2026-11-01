## 1. 測試先行

- [x] 1.1 `tests/test_season3_effects_4.py`:7 張每張至少一個依效果文寫的行為測試(可選效果的使用 / 不使用、選擇者、使用條件的錯誤碼、次數);執行並確認修改前失敗
- [x] 1.2 機制測試:Ex-026 付 MP 與每回合 2 次、M-012 與 Ex-026 並列;P-039 受「不能使用搭檔的效果」;P-037 戰術與事件卡合計 1 次、排除最後一頁、其他魔物使用ブラゴ的戰術也算(依名稱);Ex-037 費用 +1 與事件卡張數限制;PR-001 不使用時保留、依實際費用判斷、離場後另一隻ガッシュ・ベル也適用;PR-006 從翻開頁也加成、魔物效果攻擊不加成;P-041 回翻 0 張不觸發、對手沒有魔物時只有魔書傷害;確認修改前失敗

## 2. 引擎機制

- [x] 2.1 擲硬幣子階段的 `coin_reflip(mp_cost, per_turn)`、選項帶卡號、`coin_set_heads` 支援搭檔(design D1)
- [x] 2.2 `spell_any_page` 待命擴充(事件卡、家族、排除最後一頁、費用增減、只限下一場戰鬥的攻擊)與事件卡從非翻開頁使用(D2)
- [x] 2.3 PR-001 的 `spell_free_once` 待命與宣告時詢問(D3)
- [x] 2.4 PR-006 的加成待命(D4)
- [x] 2.5 P-041 的觸發與選擇(D5)

## 3. 卡片登記

- [x] 3.1 7 張登記於 `effects/cards/` 對應檔案(依卡號排序)
- [x] 3.2 `data/pending_cards.json` 移除 7 張;`tests/test_season3_cards.py` 的開放張數更新;`python -m pytest tests -m "not slow and not browser" -q` 全過(1443 passed;E-010 借用測試把 P-037 加入「有使用條件」的名單)

## 4. 前端與 NPC

- [x] 4.1 擲幣選項的來源卡、`spell_free_use` 等新選項標籤、作用中效果文字(zh-TW / en / ja,`build_zh_cn.py` 產生 zh-CN);魔書中非翻開頁的事件卡可使用;相關瀏覽器測試通過
- [x] 4.2 NPC 自我對戰牌組含這批卡不卡住(slow 自我對戰測試)

## 5. 驗證

- [x] 5.1 全套 `python -m pytest tests -q` 通過;`openspec validate --all --strict` 與基準相比沒有新增失敗(1834 passed、9 skipped;之後新增的自我對戰測試 `tests/test_season3_effects_4.py` 35 passed;抽查後的修正完成後全套 1846 passed、9 skipped)
- [x] 5.2 本機實際操作抽查(使用者)

## 6. Reconciliation(指南 §13)

- [x] 6.1 同步 delta spec 回 `card-effects` 主 spec
- [x] 6.2 `card-effects/design.md`:「行為決定與理由」加入這批的解讀(依 design D6 的狀態),「回翻 0 張不算用過回翻效果」改為 Confirmed;機制清單補上這批的擴充
- [x] 6.3 capability map 視需要更新(不需要)

## Workflow follow-up

- 歸檔:`openspec archive season3-effects-4 --skip-specs -y`(主 spec 已手動同步),在 `season3-effects-4` 分支提交;合併 main 與推送等使用者指示

## 7. 抽查後的修正(使用者 2026-11-01)

- [x] 7.1 PR-001 的詢問顯示成 M-008《策士》的說明:`spell_discount` 的標題寫死了 M-008 的內容。PR-001 改用新的決策種類 `spell_free`(來源卡 PR-001);`spell_discount` 的標題改為通用,減費與魔力變化由選項帶出、來源卡為 M-008;新增守門測試 `test_choice_titles_are_generic`(修改前失敗),決策標題不得含卡名與具體數值。`tests/golden/battle_start.json` 重新產生,差異只有減費選項多了 `cost` / `power`
- [x] 7.2 P-037 讓行動列塞滿「從魔書使用《…》(第 N 頁)」,而且列出ブラゴ用不了的其他魔物戰術(使用者 2026-11-01):畫面清單判斷使用的魔物未定時,改為「場上名為ブラゴ、且能使用這張卡的魔物」(先寫 `test_p037_any_page_list_only_brago_spells_and_events`,修改前失敗);行動列改為只放一個按鈕(多張時「從魔書使用(N 張可用)」)開魔書網格,刪除 `ui.any_page_spell_page`。battle-ui「從魔書任意頁使用戰術」新增 delta spec;`tests/test_level3_ui.py::test_any_page_spell_buttons_per_page`(M-037 每頁一個按鈕)依新規格改為 `test_any_page_cards_single_button`
