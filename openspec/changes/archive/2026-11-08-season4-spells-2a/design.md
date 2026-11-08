# Design

## Context

8 張卡的日文效果文與 atwiki 卡頁已對照(見 proposal)。防禦戰術效果的解決時機見 defense-effects-timing。

## Goals / Non-Goals

**Goals:** 8 張依效果文可用。**Non-Goals:** 非戰鬥的 7 張(下一批)。

## Decisions

### D1:「このバトル中…使えない」從宣告時生效,被無效時解除

S-117、S-131 的限制以 `on_declare` 的 `RestrictInBattle`(`DUR_BATTLE`)加上,modifier 的 `data["lift_side"]` 記下這張戰術是攻擊或防禦;限制的判斷(`restricted` 等)在那一方已被無效時視為不生效。不在每個「使無效」的地方移除,避免遺漏。這是「防禦戰術的效果於『効果の使用』的最後解決」的例外:限制的對象就是戰鬥中效果的時機,延後就沒有作用(atwiki S-117 解說:擋住戰鬥中的事件卡)。使用者 2026-11-08 選擇。

- S-117:對手 `NO_EVENTS`。S-131:雙方 `NO_PARTNER_EFFECTS` 與 `NO_EVENTS`(「パートナーの効果やイベントの効果」;比照 E-008 的搭檔效果失效)。

### D2:S-125

攻擊宣告時,對手場上可被棄掉的搭檔(M-049 保護的除外)依場上順序各擲 1 次(比照 Ex-044「結果不受順序影響,不讓玩家選順序」),記下擲出正面的魔物。獲勝時棄掉這些魔物身上仍在的搭檔,不造成傷害(`no_book_damage`)。

### D3:S-128 / S-129 / S-133

- S-128:`on_effects_end` 以 `AttackAttrIs("雷")` 判斷攻擊戰術的屬性;魔物效果攻擊沒有屬性(atwiki S-113 解說:《格闘》不是雷屬性)。
- S-129:新增 `PlayerState.spell_names_by_turn`(宣告時記錄戰術卡名,之後被無效也算;只保留本回合與前一回合,比照 Ex-043 的屬性記錄)。條件 `OwnUsedSpellNamedLastTurn("アシルド")`,卡名完全相符;宣告前預估也求值。
- S-133:`on_damage` 用既有的 `StealOpponentMp(3)`(P-002)。

### D4:S-146

- `SpellRider.declare_condition`(條件規格,ctx 含使用者與使用的魔物 `slot`)在 `_validate_spell_declaration` 檢查,不成立時 `spell.condition`。條件 `UserPowerExceedsOpponentsBy(5000)`:使用的魔物當下的魔力 ≥ 對手每隻魔物的魔力 + 5000,對手沒有魔物時不成立。
- `SpellRider.once_per_turn`:本回合已宣告過同名戰術時 `spell.used`(依 `spell_names_by_turn`)。
- 獲勝時:`AsOpponent` 由對手選自己 1 隻魔物(空頁數不少於疊放張數者才可選),`ReturnSlotToBook` 由上而下逐張詢問放回哪個空頁(比照 M-025 由放回的玩家選頁),搭檔進棄牌區(比照魔物離場),之後結束戰鬥、不造成傷害。沒有可選的魔物時沒有效果。整疊放回、搭檔棄掉為使用者 2026-11-08 選擇。

### D5:Ex-063

`extra_cost=(2, 2, 0, 0)` 沿用宣告時的追加費用選擇;追加的費用記在 `battle.data["defense_extra_cost"]`。`on_effects_end` 以 `AttackDamageIs(values=(1,), with_extra=(1, 2))` 判斷攻擊的當下傷害(含 +N 加成,`_attack_damage_amount`):不追加時剛好 1、追加時 1 或 2 才使攻擊無效。追加費用選項的文字改為「也使 2 傷害的攻擊無效」(選項帶 `effect`)。使用者 2026-11-08 選擇。

## Risks / Trade-offs

- [限制判斷要讀戰鬥狀態] → 只在 `data["lift_side"]` 存在時才讀,其他限制不受影響。
- [S-146 放回後魔書的頁序] → 放回的頁可能在已翻過的位置,照規則屬於該頁。
