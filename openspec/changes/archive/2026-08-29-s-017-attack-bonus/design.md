## Context

`src/gash/engine/effects/spells.py` 目前用同一個 `_defense_self_bonus(amount)` helper 同時處理 S-016(+1000)與 S-017(+2000):在 `on_declare` 時,若 `side == "defense"`,把 `amount` 累加進 `battle.data["defense_self_bonus"]`;`engine.py:_side_total` 在計算防禦方合計魔力時讀取這個 key 加上去。核對權威來源試算表(`openspec/specs/card-effects/Zatch Bell CCG List for TTS.gsheet`)確認 S-017 官方原文為「When Attacking, add 2000 Power」,現行「防禦時」的資料與行為是抽取/轉錄錯誤,S-016 不受影響(其官方文本確實是防禦時)。

`engine.py:_side_total` 對攻擊方另有獨立、通用的 `battle.data["attack_spell_bonus"]` 累加值(其他效果如 S-032 一類的硬幣加值已在用,見 `spells.py` 約 281 行),攻擊方合計魔力已會讀取這個值。

## Goals / Non-Goals

**Goals:**
- S-017 的自身魔力加值改為在「以此術攻擊時」宣告觸發(+2000),防禦時不再觸發。
- S-016 行為維持不變(仍是防禦時 +1000)。
- 不引入新的 `battle.data` key、不修改 `engine.py:_side_total`。

**Non-Goals:**
- 不變更 S-017 的傷害值(`damage: 2`)或香草的「攻擊方獲勝時對魔本造成傷害」效果。
- 不處理其他卡片的加值邏輯重構。

## Decisions

- **重用既有的 `attack_spell_bonus` 累加欄位,而非新增 `attack_self_bonus`**:`_side_total` 對攻擊方已經會讀取 `battle.data.get("attack_spell_bonus", 0)` 並計入合計魔力(見 engine.py:725, 738)。S-017 的 `on_declare` 在 `side == "attack"` 時直接對這個既有欄位累加 2000,即可達到效果,不需觸碰 `engine.py`。
  - 替代方案(否決):比照 `defense_self_bonus` 新增一個 `attack_self_bonus` key 並修改 `_side_total` 讀取——多一處引擎改動,且與現有攻擊方加值機制重複,徒增維護面。
- **拆開 S-016/S-017 的共用 helper**:新增 `_attack_self_bonus(amount)`(對稱於現有 `_defense_self_bonus`),S-017 改註冊為 `reg.spell_rider("S-017", on_declare=_attack_self_bonus(2000))`;S-016 的註冊不動。

## Risks / Trade-offs

- **依賴防禦加值設計的既有測試** → `tests/test_cards.py` 中原驗證「S-017 防禦時 +2000」的案例(誤植行為)需要改為驗證「攻擊時 +2000」與「防禦時不再加值」兩個情境。
- **依賴舊(錯誤)行為構築魔本的玩家** → 這是修正 bug,行為變更無法避免;`data/cards.json`/`data/cards.zh-TW.json` 一併更新為正確的「攻擊時」文本,與官方試算表一致。
