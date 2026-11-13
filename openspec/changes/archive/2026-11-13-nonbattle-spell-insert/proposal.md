## Why

any-page-defense 盤點時發現:確認進入戰鬥時,非回合玩家可以插入 1 個行動,引擎接受使用非戰鬥戰術,行動欄的詳細提示也寫「帶『防(D)』圖示的事件卡或非戰鬥戰術」,但前端在這個時機不提供非戰鬥戰術的「使用」按鈕,只顯示停用的「使用」(原因「非戰鬥中才能使用」)。受影響的是攻防圖示的非戰鬥戰術:PR-009 ラウザルク、S-072 ジオルク(含 P-025 從其他頁使用)、S-140 ヴォルク。

同時發現 E-010 借用的搭檔效果:引擎在插入行動時拒絕(`battle_in.invalid`),但場上效果(`use_field_ability`)可以;借用的效果同樣是「使用效果」的 1 個行動。使用者決定一起處理(2026-11-13)。

## What Changes

- 確認進入戰鬥時,非回合玩家翻開的頁(與從魔書任意頁使用的頁)中的非戰鬥戰術,提供與非戰鬥中相同的「使用」按鈕。
- 引擎在確認進入戰鬥時接受 E-010 借用的搭檔效果作為插入的 1 個行動;行動欄在這個時機同樣顯示「借用效果:〈卡名〉」入口。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `game-engine`:修改「進入戰鬥確認」,寫明插入的 1 個行動包含哪些。
- `battle-ui`:修改「借用效果的使用入口」,新增「確認進入戰鬥時插入的行動」。

## Impact

- `src/gash/engine/engine.py`(`_battle_in_response`)、`frontend/app.js`(`pageButtons`、`renderActionBar`)。
- 測試:`tests/test_battle_in_insert.py`(新)、`tests/test_spell_user_ui.py`。
