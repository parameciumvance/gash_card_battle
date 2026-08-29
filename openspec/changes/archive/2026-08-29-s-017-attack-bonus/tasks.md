## 1. 卡片資料文本(修正抄錄錯誤)

- [x] 1.1 修正 `data/cards.json` 中 S-017 的 `effect_en`,改為權威來源試算表原文:
      "Damage your opponent's Spell Book when you win the Battle as an Attacker. When Attacking, add 2000 Power to this SPELL card."
- [x] 1.2 修正 `data/cards.zh-TW.json` 中 S-017 的中文 `effect` 文本,對應改為「以攻擊方獲勝時,對對手的魔本造成傷害。以此術攻擊時,此術魔力+2000。」

## 2. 引擎效果邏輯

- [x] 2.1 在 `src/gash/engine/effects/spells.py` 新增 `_attack_self_bonus(amount)` helper:`on_declare` 時若 `side == "attack"`,將 `amount` 累加進 `battle.data["attack_spell_bonus"]`(重用既有攻擊方合計加值欄位,`engine.py:_side_total` 已會讀取)
- [x] 2.2 將 S-017 的 `reg.spell_rider` 註冊由 `on_declare=_defense_self_bonus(2000)` 改為 `on_declare=_attack_self_bonus(2000)`;S-016 的註冊維持不變

## 3. 測試

- [x] 3.1 修改 `tests/test_cards.py::test_s017_defense_bonus`(或新增測試)驗證:攻方宣告 S-017 時,`showdown` 的 `attacker_total` 含 +2000 加值
- [x] 3.2 新增情境驗證:防方宣告 S-017 時不再獲得 +2000 加值(僅魔物基礎魔力 + 術魔力本值)
- [x] 3.3 執行 `python -m pytest` 確認全數通過,含 S-016 既有測試未受影響

## 4. 收尾

- [x] 4.1 執行 `openspec validate s-017-attack-bonus` 確認 proposal/design/specs/tasks 格式正確
