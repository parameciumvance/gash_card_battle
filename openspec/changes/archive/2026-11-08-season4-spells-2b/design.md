# Design

## Context

見 proposal。魔物效果攻擊 / 防禦目前以 `reg.MAMODO_ATTACK` / `MAMODO_DEFENSE` 依卡號查詢(引擎、快照、NPC 各自查);不受傷害是 `no_damage` modifier(指定 slot);對手魔物的選項規格分散在多個類別。

## Decisions

### D1:S-113 賦予的《格闘》

- `GrantFamilyFighting` 加一筆 modifier(kind `granted_fighting`,對象玩家、`data["family"]`,期間到自己的下一回合結束)。新增 `engine.mamodo_attack_spec(game, player, slot)` / `mamodo_defense_spec(...)`:先看卡號登記,沒有時看這種 modifier(以當下的家族判斷,期間中上場的也算)。引擎、快照、NPC 改用這兩個函式。
- 規格:費用 0、合計魔力 10000、傷害 1、每回合 1 次;使用記錄的鍵含來源(`fighting:S-113`),攻擊與防禦共用(攻擊只在自己的回合、防禦只在對手的回合)。多張 S-113 只有 1 個《格闘》(atwiki FAQ A2)。
- 是「魔物の効果」:受「魔物の効果を使えない」限制、可被 M-026 無效,沿用魔物效果攻擊 / 防禦的流程。沒有屬性。
- 若同一隻魔物本身也有魔物效果攻擊,現有的指令無法區分;目前沒有這樣的ガッシュ・ベル(測試確認),之後出現時再加指定。

### D2:S-121 不受傷害、不能被選

- `FamilyNoDamage` 加 modifier(kind `no_damage`,`target_slot` 為 None、`data["family"]`);`_damage_slot` 的不受傷害判斷同時接受指定 slot 與依家族(期間中上場的也算)。保護時以バランシャ承受也不受傷害(atwiki 卡頁解說)。
- `FamilyUnselectable` 加 modifier(kind `unselectable`,`data["family"]`)。新增 `selectable_opponent_slots(game, chooser)`:對手場上、不受這種 modifier 保護的魔物。所有「由效果選對手魔物」的地方改用它:`OpponentMamodo`、`OpponentMamodoExcept`、`OpponentInjuredMamodo`、`OpponentHealthyMamodo`、S-033 / Ex-044 / S-036 的「すべてを選ぶ」、S-057 / S-058 的改打魔物、`opponent_has_mamodo`(選得到對象的使用條件)。只看「選ぶ」:沒寫選ぶ的全體效果不受影響;選搭檔(搭檔卡不是バランシャ)不受影響;自己的保護不受影響。
- 期間到下一回合結束(`DUR_UNTIL_END_NEXT_TURN`),屬【ステイ】,P-034 / E-036 可移除(分類同其他「ステイ」限制)。

### D3:S-136

- 非戰鬥戰術的使用魔物寫進效果 ctx(`user_slot`;`register_spell_nonbattle` 的 handler 多收一個參數)。
- `Choose(OpponentMamodo)` 後 `LockChosenOpponentMamodo(duration=到自己的下一回合結束)`;`LockUserSlot` 以同一旗標鎖住使用的ニャルラト。使用條件:有可選的對手魔物(含 S-121)。

### D4:S-140

- `reg.spell_no_user(number)`:非戰鬥戰術在場上沒有對應魔物時也能使用,沒有使用魔物(仍受整個玩家的「術を使えない」)。有對應魔物時照常以它為使用者。
- 效果:`Choose(OwnBookMamodoNamed("ノリトー・ハッサミー"))` → 放出(沿用 E-012 的可放出判斷:場上未滿、同名)。使用條件:有可放出的。

### D5:S-144

- 限制旗標 `NO_DISCARD_COST_EFFECTS`(對手,到下一回合結束,【ステイ】)。擋下:啟動效果 `mode="discard"`(魔物、搭檔、MJ12、E-010 借用)、`coin_set_heads`(M-034 / P-039)、`jammer(discard_self=True)`(M-032 / Ex-034)。被擋的不提供使用機會,與其他「使えない」相同。

### D6:S-145

`Coin(1)` 正面時 `ScheduleSpellFromNextSpreads(any_spell=True, spreads=4)`;`spell_any_page` 待命的 `any_spell` 也接受 `pages`。比照 S-026 不詢問是否使用(使用者 2026-11-08 確認);「4枚後ろ」比照 M-037 為翻開頁之後 4 個對頁。

## Risks / Trade-offs

- [選項規格遺漏 S-121] → 以測試涵蓋每個列出的規格;新的「選對手魔物」規格須用 `selectable_opponent_slots`(寫進 game-engine design)。
- [S-095 與 D1 / D2 的「期間中上場的也算」不一致] → 已列出,由使用者決定是否一併修正。
