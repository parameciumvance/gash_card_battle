# Tasks

## 1. 畫面字串、規則頁與錯誤訊息

- [x] 1.1 `frontend/i18n/{zh-TW,en,ja}.json` 依 design 對照表改寫 `ui.mamodo_attack`、`ui.mamodo_defense`、`ui.battle_in_hint_mamodo`、`log.battle_started_mamodo`、`log.battle_in_check_mamodo`、`anim.showdown.no_spell`、`anim.showdown.mamodo_defense`、`error.attack.no_mamodo_attack`、`error.defense.no_mamodo_defense` 及其他含舊用語的條目;執行 `python tools/build_zh_cn.py`;`tests/test_i18n_languages.py` 通過
- [x] 1.2 規則頁 `frontend/i18n/rules.{zh-TW,en,ja}.json` 的魔物攻擊說明改用新用語,重跑 `build_zh_cn.py`;`tests/test_rules_page.py`、`tests/test_i18n_languages.py` 通過
- [x] 1.3 `src/gash/engine/engine.py` 中 `attack.no_mamodo_attack`、`defense.no_mamodo_defense` 的中文伺服器訊息改用新用語(錯誤碼不變)
- [x] 1.4 斷言畫面字串的測試改用新字串(`tests/test_level3_ui.py` 的「直接防禦(魔力6500)」、`tests/test_showdown_ui.py` 的「無戰術攻擊」等);相關瀏覽器測試(`test_level3_ui`、`test_showdown_ui`、`test_battle_stage_ui`、`test_effect_usage` 相關)通過

## 2. 註解與測試說明

- [x] 2.1 `src/`、`frontend/*.js`、`tests/` 的註解與測試說明中的「無戰術攻擊」「直接攻擊 / 直接防禦」改為新用語(NPC 註解中意為「馬上攻擊」者除外);只動註解與字串,`git diff` 確認沒有改到識別字;`python -m pytest tests -q -m "not slow"` 除既有的卡圖相關失敗外通過

## 3. Reconciliation 與歸檔(指南 §13)

- [x] 3.1 同步 delta(RENAMED)回 `game-engine`、`battle-ui` 主 spec;直接改各主 spec(`game-engine`、`battle-ui`、`card-effects`、`npc-opponent`、`effect-tree`)需求本文與情境名稱的舊用語;再套用一次 delta 結果相同(歸檔不重複套用);`openspec validate --all --strict` 通過
- [x] 3.2 更新 design:`game-engine/design.md`(含「直接攻擊 / 防禦的使用次數與ジャマー」節名)、`battle-ui/design.md`、`card-effects/design.md`(含「`game-engine` › 需求『無戰術攻擊』」的引用)、`npc-opponent/design.md`;確認 capability map 不需更新
- [x] 3.3 以舊用語 grep `src`、`frontend`(不含 `releases.*.json`)、`tests`、`openspec/specs`、`README.md`、`docs`,確認只剩 NPC 註解中意為「馬上攻擊」的「直接攻擊」,並在完成回報中列出
- [x] 3.4 依使用者指示歸檔並提交
