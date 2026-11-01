## 1. 測試先行

- [x] 1.1 `tests/test_season3_effects_5.py`:3 張依效果文的行為測試(Ex-025 立即使用 / 中間有行動被拒絕 / 被無效後不能用;M-065 正面無效 / 反面 / 常駐效果不詢問 / MP 減少被擋下時不詢問 / 每個行動 1 次、每回合不限次數;Ex-034 付得起重新解決 / 付不起無效歸 0 / 受「不能使用搭檔的效果」);執行並確認修改前失敗

## 2. 引擎

- [x] 2.1 ジャマー支援搭檔卡、`mp_reduced`、擲幣、不限次數、重新解決(D1〜D3)
- [x] 2.2 行動紀錄 `action_seq` 與 `last_effect_mp_gain`(D4)

## 3. 卡片登記

- [x] 3.1 3 張登記於 `effects/cards/` 對應檔案(依卡號排序)
- [x] 3.2 `data/pending_cards.json` 移除 3 張;`tests/test_season3_cards.py` 的開放張數更新;`python -m pytest tests -m "not slow and not browser" -q` 全過(1460 passed;重複登記測試補上ジャマー的新欄位,`test_room_with_ex_card_rejected` 的範例卡改為仍未開放的 M-058 並改名)

## 4. 前端與 NPC

- [x] 4.1 ジャマー詢問的選項文字(擲幣、重新解決)與 i18n;相關瀏覽器測試通過
- [x] 4.2 NPC 自我對戰牌組含這批卡不卡住(slow 自我對戰測試)

## 5. 驗證

- [x] 5.1 快速測試組、相關瀏覽器測試與新增的 slow 測試通過(全套留到 push 前,AGENTS.md「測試」);`openspec validate --all --strict` 與基準相比沒有新增失敗(新測試檔含自我對戰、`test_level3_ui.py`、`test_choice_ui.py`、`test_choice_locations.py`、`test_effect_usage.py` 共 97 passed)
- [x] 5.2 本機實際操作抽查(使用者)

## 6. Reconciliation(指南 §13)

- [x] 6.1 同步 delta spec 到 `card-effects` 與 `game-engine` 主 spec
- [x] 6.2 `card-effects/design.md`「行為決定與理由」加入這批的解讀(Ex-034 重新解決、M-065 範圍、Ex-025 直後);`game-engine/design.md` 的ジャマー說明補上擴充

## 7. 抽查後的修正(使用者 2026-11-01)

- [x] 7.1 使用ジャマー後行動權沒有換給對手:官方規則書第 39 頁「その直後の自分のアクションでジャマー効果を使い」,使用ジャマー是自己的行動。非戰鬥中使用 M-026 / M-032 / M-065 / Ex-034 後行動權換給對手、連續 pass 歸零(使用者確認既有的 M-026 / M-032 一起改);不使用時不變;戰鬥中攻防的ジャマー不改。先寫 `test_jammer_use_passes_action_to_opponent`、`test_new_jammers_pass_action`(修改前失敗);依舊行為寫的 `tests/test_level2.py::test_m026_waits_for_opponent_effect_choices_then_restores`(行動權留在使用者)改為換給對手。game-engine「ジャマー的使用時機」補上規則與情境
- [x] 7.2 多張ジャマー可用時同時提供(使用者 2026-11-01):一個決策列出所有可用的ジャマー(選項值為卡號,多張時選項文字加卡名),取代依序詢問。先寫 `test_multiple_jammers_offered_together`(修改前失敗);`tests/test_level2.py::test_m026_offered_right_after_opponent_mamodo_effect_and_negates_it` 的選項值期望改為卡號;新增 `tests/test_level3_ui.py::test_jammer_options_named_when_multiple`。game-engine 新增需求「多張ジャマー同時提供」
