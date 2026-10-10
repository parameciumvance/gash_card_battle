## 1. 鎖定現有行為

- [x] 1.1 新增特性測試(`tests/test_effect_characterization.py` 或新檔):戰術攻擊在 P-007(spell_bonus)、P-001(限定魔物的 attack_undefendable,由該家族與非該家族的戰術各一次)、S-026(不限定的 attack_undefendable)、E-013(no_protect_book)、S-057(injure_instead)、P-015 任意頁等待命下,記錄完整事件序列(種類與欄位)與戰鬥狀態;無戰術攻擊(M-027)在同樣的待命下的事件序列,以及「限戰術」的待命未被消耗、仍在 `standby`。確認在重構前全部通過

## 2. 重構

- [x] 2.1 `_prepare_spell_attack` / `_prepare_mamodo_attack` 與共用流程(design D1、D2);1.1 全過
- [x] 2.2 待命表 `BATTLE_START_STANDBYS`(design D3),移除兩個函式中各自的消耗迴圈;1.1 全過,`pytest`(全部)通過

## 3. Reconciliation 與歸檔(指南 §13)

- [x] 3.1 Reconcile affected capability design:`game-engine/design.md` 新增「戰鬥開始與待命表」一節(攻擊來源、共用流程、待命表與新增待命的做法)
- [x] 3.2 規格不變(skip_specs),確認 capability map 不需更新
- [x] 3.3 `openspec validate --all --strict`(與既有基準相比沒有新增失敗)與 `pytest` 全過後歸檔
