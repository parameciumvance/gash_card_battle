## Why

翻開的頁有兩張 S-043 時,用了一張,兩張都顯示「本回合已使用」。非戰鬥戰術的使用紀錄以卡號記錄(`used_nonbattle_spells`),同名的都算用過;戰鬥戰術則以頁計次,兩張 S-001 可以各用一次。規則頁「用過的戰術到下一回合前不能再用」指的是用過的那一張,使用者確認應為每張各一次。

## What Changes

- 非戰鬥戰術的使用紀錄改以頁記錄:用過的那一頁本回合不能再用,同名的其他頁各自可用一次。
- 快照欄位 `used_nonbattle_spells`(卡號)改為 `used_nonbattle_pages`(頁碼),仍只給持有者。**BREAKING**(前端同步修改)。
- 前端依頁判斷「使用」是否停用。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `game-engine`:修改「使用場上與魔書中卡片的效果」(非戰鬥戰術以頁計)。
- `battle-api`:修改「非對戰術使用紀錄快照」(欄位改為頁碼)。
- `battle-ui`:修改「非對戰術使用入口」(依頁判斷)。

## Impact

- `src/gash/engine/state.py`、`engine.py`(記錄與檢查)、`api/views.py`(快照)、`frontend/app.js`。
- 測試:`test_views.py`、`test_spell_user.py`、`test_level2.py`、`test_nonbattle_ui.py`、`test_stack_and_conditions.py` 中依卡號的斷言。
