## Context

見 proposal.md。現況的兩條路徑(`engine.py`):

```
戰術:   重新驗證 → [P-015 任意頁:消耗 spell_any_page 待命] → 記錄頁 → 付費
        → 建立 BattleState(attack_page / attack_spell)→ arm 待命 → battle_started(spell, slot)
        → spell_bonus → attack_undefendable(含限定魔物)→ no_protect_book → injure_instead
        → 宣告時效果(rider.on_declare)
無戰術: 重新驗證 → 付費 → 建立 BattleState(attack_fixed_*)→ arm 待命
        → battle_started(spell=None, mamodo, slot) → attack_undefendable(只限不限定魔物的)→ no_protect_book
```

## Goals / Non-Goals

**Goals:** 一份戰鬥開始的共用流程;待命的適用條件集中在一處、明寫。

**Non-Goals:** 不改任何行為、事件或規格;不動宣告、防禦、效果步驟等其他戰鬥流程。

## Decisions

### D1:攻擊來源

- `_prepare_spell_attack(game, batch, bi)` / `_prepare_mamodo_attack(game, batch, bi)`:各自驗證、付費、記錄(戰術含 P-015 待命的消耗與 `standby_resolved` 事件,順序與現在相同),回傳 `AttackStart`:BattleState 的初始參數、`battle.data` 的初始內容、`battle_started` 事件的欄位、`is_spell`、`mamodo_name`(使用魔物的家族;無戰術攻擊為 None)、`spell` 卡號(宣告時效果用)。
- `_start_battle` 依 `bi.get("mamodo_attack")` 選擇準備函式,之後走共用流程。

### D2:共用流程

建立 BattleState → `st.battle` → `_arm_next_battle_standbys` → `battle_started` → 依 D3 的表消耗待命 → 戰術時執行宣告時效果。

### D3:待命表

```
BATTLE_START_STANDBYS = [
  ("spell_bonus",          適用:是戰術,且 data.mamodo 為 None 或等於使用魔物家族,且(選擇減費 或 非 optional),
                           套用:攻擊戰術魔力 += power_delta),
  ("attack_undefendable",  適用:data.mamodo 為 None;或是戰術且等於使用魔物家族,
                           套用:attack_undefendable = True),
  ("no_protect_book",      適用:都適用,                套用:data.no_protect_book = True),
  ("injure_instead",       適用:是戰術,                套用:data.injure_instead = True),
]
```

- 依表的順序消耗(與現在的事件順序相同),每個被消耗的待命都發 `standby_resolved`。
- 無戰術攻擊不消耗「限戰術」的待命,它們留到下一場戰鬥(與現在相同:現在根本不會去消耗)。
- 新增待命時:在表加一列,寫明適用條件;記在 `game-engine/design.md`。

### D4:以特性測試鎖定行為

重構前先加測試,記錄兩種攻擊在各種待命組合下的完整事件序列(種類與欄位)與戰鬥狀態;重構後必須完全相同。

## Risks / Trade-offs

- [事件順序改變影響前端動畫或記錄] → D4 的特性測試逐一比對事件序列。
- [表的抽象太泛] → 只涵蓋「戰鬥開始時消耗的待命」,不擴及其他時點。
