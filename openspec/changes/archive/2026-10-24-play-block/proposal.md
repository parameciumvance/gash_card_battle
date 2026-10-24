# Proposal

## Why

魔書中翻開的魔物卡,「放出」按鈕在前端沒有任何判斷:M-046(「シュドルク」を使わないと場に出せない)與 M-027 永遠可按,按下才被引擎以 `play.spell_only` 拒絕;場上已滿 3 隻、同名已達上限、疊放型沒有可疊的變身前魔物時也一樣。搭檔卡雖由前端計算裝備對象,但以卡面的 `related_mamodo` 比對,M-047(「ガッシュ・ベル」としてあつかう)在場時會誤判沒有對應魔物,也沒有判斷同名搭檔。能不能放出應由引擎判斷一次,前端照快照顯示。

## What Changes

- 引擎抽出共用的放出可否判斷,`play_card` 指令與快照都用它;判斷內容與錯誤碼不變(魔物:`spell_only` / `no_base` / `field_full` / `same_name`;搭檔:`no_mamodo` / `partner_exists` / `same_name`)。
- 持有者本人視角的快照中,翻開的魔物頁與搭檔頁附 `play_block`(不能放出時為錯誤碼,可以時為 null);搭檔頁另附 `targets`(可裝備的魔物槽 uid,依引擎的家族判定,含 M-047 視為ガッシュ・ベル)。
- 前端「放出」依 `play_block` 停用並顯示 `error.play.*` 的原因;搭檔的裝備對象改用 `targets`,不再自行比對 `related_mamodo`。
- 不在範圍:時機(是否輪到自己行動、戰鬥中)維持前端既有判斷;NPC 的候選不變。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `battle-api`:新增「魔書中卡片的放出可否」快照欄位(`play_block`、搭檔頁的 `targets`)。
- `battle-ui`:「選擇搭檔卡的裝備對象」改依快照的 `targets`;新增魔物卡「放出」依快照停用並顯示原因。

## Impact

- `src/gash/engine/engine.py`:`_play_card` 的檢查抽成 `play_block(game, player, number)`(與搭檔的裝備對象查詢)。
- `src/gash/api/views.py`:`_player_view` 翻開頁加欄位。
- `frontend/app.js`:`pageButtons`、`partnerTargets` / `pickPartnerTarget`。
- 測試:`tests/test_api*.py` 或相關快照測試、引擎測試、`tests/test_level3_ui.py` 等瀏覽器測試。
