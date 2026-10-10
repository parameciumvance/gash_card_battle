## Why

`engine._start_battle`(戰術攻擊)與 `_start_mamodo_battle`(無戰術攻擊,M-027)各寫了一份戰鬥開始的骨架:建立戰鬥、啟用「下一場戰鬥」待命、發出 `battle_started`、逐一消耗待命。兩者真正不同的只有攻擊來源的驗證與付費,以及哪些待命適用(「術」相關的待命不適用於無戰術攻擊)。目前兩邊消耗的待命都與效果文一致,但以後新增一個作用於「下一場戰鬥」的待命時,必須記得兩邊都加並各自判斷適用,漏加也不會有測試失敗。

## What Changes

- 戰鬥開始改為「準備攻擊來源」+「共用流程」:兩種攻擊來源各自驗證、付費、記錄,回傳戰鬥的初始欄位與脈絡(是否為戰術、使用魔物的家族);建立戰鬥、啟用待命、發出事件與消耗待命共用。
- 待命的消耗改由一張「待命種類 → 適用條件 → 套用方式」表驅動,適用條件明寫:`spell_bonus`、`injure_instead` 限戰術;`attack_undefendable` 有限定魔物時須為該家族的戰術;`no_protect_book` 都適用。宣告時效果(擲幣等)只限戰術。
- 行為完全不變:事件的種類、欄位與順序都相同。
- `game-engine/design.md` 記錄這張表與新增待命時的做法。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

(無,行為不變;`.openspec.yaml` 設 `skip_specs: true`)

## Impact

- `src/gash/engine/engine.py`(`_start_battle`、`_start_mamodo_battle`)。
- 測試:新增鎖定事件順序的特性測試(重構前後都要通過)。
- 文件:`openspec/specs/game-engine/design.md`。
