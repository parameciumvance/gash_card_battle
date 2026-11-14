## Why

「X の術」的讀法在 2026-10-31(spell-ownership)定為聯集:對應魔物是 X,或由 X 使用。第 4 彈的 P-045 寫「自分が『ドンボッチョ』で使った術」,可見效果文指「由 X 使用的戰術」時另有寫法。使用者 2026-11-14 裁定:「X の術」單純代表對應魔物為 X 的戰術。

## What Changes

- 「X の術」只看戰術卡的對應魔物,不看使用者;指令戰術不是任何魔物的戰術。
- 行為改變:
  - PR-009、M-058 不擋指令戰術;P-037、PR-001、M-008、P-005 的加成 / 減費 / 任意頁不適用於指令戰術;M-038 的豁免不含它使用的指令戰術。
  - X 使用其他魔物的戰術(M-036 的氷屬性、Ex-056〜058、M-023)不算 X の術:P-022 不適用於フリガロ用レイコム的戰術。
  - 限制類效果變弱(使用者確認接受):E-024 / E-047 / P-033 / E-043 擋不住被限制的魔物使用指令戰術或借用的其他魔物戰術。
- 不變:X 的戰術由其他魔物使用仍算 X の術(ゼオン 用ザケル 時 P-001 適用、E-047 選ガッシュ・ベル 時ゼオン 也不能用ザケル)。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `card-effects`:修改「『〇〇の術』的判定」「第二彈 68 種卡全數可用」(P-022 情境)「無視限制的效果」(M-038)「M-058 不能使用這隻魔物的戰術」。

## Impact

- `src/gash/engine/effects/primitives.py`(`spell_names`)、`src/gash/engine/engine.py`(依名稱的任意頁判斷簡化)。
- 測試:`tests/test_spell_ownership.py`、`tests/test_season3_effects_4.py`、`tests/test_season3_effects_6.py`、`tests/test_spell_user.py`。
