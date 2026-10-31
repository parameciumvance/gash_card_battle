## 1. 測試先行

- [x] 1.1 `tests/test_spell_ownership.py`:依 delta spec 的「『〇〇の術』的判定」逐一寫測試,執行並確認修改前失敗。範圍:
  - 加成類:P-001 / M-054 由 M-029 使用「ザケル」;P-022 由 M-036 使用レイコム 的戰術(既有行為,回歸);P-005 / M-008 由 M-023 使用 スギナ 的戰術;M-054 由另一隻 ガッシュ・ベル 攻擊;P-042 / P-043 以「X」的戰術由其他魔物攻擊;Ex-007 類與 P-022 / P-023 / P-007 各一個。
  - 限制類:E-047 / P-033 / E-024 / S-074 / Ex-044 擋同名的另一隻、擋其他魔物使用該魔物的戰術、選定的魔物離場後仍有效、魔物效果部分只看那一隻;PR-009 擋指令戰術;E-043 有同名的另一隻時選定的魔物不能使用戰術、魔物效果可用,沒有同名時可用自己的戰術;P-043「不能使用防禦戰術」在選定的魔物離場後仍提供並生效,「不能保護」不提供。
  - M-038:其他魔物使用 ロップス 的戰術不受限制。
  - M-005 / M-055(D3a):另一隻 ブラゴ 攻擊時適用。
  - PR-004 / PR-010:資料中名為「ザケル」的戰術的對應魔物只有 ガッシュ・ベル 與 ゼオン(D6 的前提)。
- [x] 1.2 依舊解讀寫、會反轉的既有測試改依新規則,並確認改後在修改前失敗:
  - `tests/test_level2.py`:`test_p005_cost_zero_only_when_sugina_uses_the_spell`、`test_m008_bonus_only_when_sugina_uses_the_spell`
  - `tests/test_season3_effects_2.py`:`test_m054_only_this_mamodo`(改為「ガッシュ・ベル 以外的魔物攻擊時可以防禦」,另加同名的另一隻)、`test_e047_blocks_only_chosen_mamodo_spells`
  - `tests/test_season3_effects_2.py`:`test_m055_not_offered_for_other_mamodo`(原以另一隻 ブラゴ M-033 攻擊;改為 ブラゴ 以外的魔物以自己的戰術攻擊)
  - `tests/test_season3_effects_2.py`:`test_p043_no_defense_spell_of_chosen`(同名的 B 也不能使用防禦戰術)
  - `tests/test_spell_user.py`:`lock()` 輔助比照 E-024 記錄名稱;`test_nonbattle_spell_without_user_skips_locked` 改為同名的另一隻也被擋(`test_nonbattle_spell_same_name_user_also_locked`)
  - 實作中其他因新規則失敗的測試:逐一判斷是應該反轉,還是回歸;應該反轉的補列在這裡。

## 2. 引擎

- [x] 2.1 `primitives.spell_names`(D1)
- [x] 2.2 費用與加成的待命改傳 card / slot,`AttackStart` 帶 `spell_names`;`BATTLE_START_STANDBYS`、防禦宣告的加成、`battle_lock`、`AttackByFamilyWithTarget` 改用 `spell_of`(D2)
- [x] 2.3 指示詞的限制與待命記錄名稱:`MakeNextAttackUndefendable(own_slot)`、`LockChosenOpponentMamodo`、`LockOpponentMamodoPerHeads`、P-043 的 `NO_DEFENSE_SPELL_SLOT`、`RestrictOthersThanChosen`、M-005 的 `damage_delta`、M-055 的 `self_mamodo`。`spell_block` 依名稱判定,所有呼叫端都傳入戰術卡(D3、D4)
- [x] 2.4 M-038 的無視範圍(D5)
- [x] 2.5 更新程式碼註解與 docstring 中「以使用戰術的魔物判定」「只限這隻魔物」等舊說法,不留宣稱舊行為的註解;`python -m pytest tests -m "not slow and not browser" -q` 全過

## 3. 前端與 NPC

- [x] 3.1 可使用戰術的顯示由快照 `users` 決定,確認限制類範圍變大後畫面一致(相關瀏覽器測試,例如 `tests/test_spell_user_ui.py`)
- [x] 3.2 NPC 自我對戰不卡住(slow 自我對戰測試)

## 4. 驗證

- [x] 4.1 全套 `python -m pytest tests -q` 通過;`openspec validate --all --strict` 與基準相比沒有新增失敗(1781 passed;`tests/test_cheat_editor.py::test_post_response_from_closed_editor_preserves_new_draft` 整檔執行時失敗、單獨執行通過,修改前的程式碼整檔執行同樣失敗,與本 change 無關)
- [x] 4.2 本機實際操作抽查(使用者)

## 5. Reconciliation(指南 §13)

- [x] 5.1 同步 delta spec 到 `openspec/specs/card-effects/spec.md`
- [x] 5.2 `openspec/specs/card-effects/design.md`:
  - 刪除「『〇〇の術』以使用戰術的魔物判定」,改成「『〇〇の術』的判定(聯集)」的行為決定。理由:M-029 FAQ、atwiki 2078、使用者 2026-10-31 的決定;確認狀態 `Project Decision`;E-043 的解讀(D4)一併記錄。
  - 改寫規則機制「『〇〇の術』的費用與加成」,記錄 D6 不改的理由。
  - 檢查 P-042 / P-043 / M-054 / E-047 等既有條目,刪除已失效的「依攻擊的魔物」「只限選定魔物」說法。
- [x] 5.3 game-engine 規格中「術を使えない」、M-038 的描述若與新規則不一致,一併更新;capability map 不需要改(不新增 capability)
