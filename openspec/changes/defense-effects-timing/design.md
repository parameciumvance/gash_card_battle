# Design

## Context

見 proposal.md「Why」。現有三種寫法:

| 寫法 | 卡 | 防禦被無效時 |
|---|---|---|
| 宣告時直接生效 | S-025、S-069(防禦)、S-106 `NegateAttack`;S-027 `AdjustDefenseDamage`;S-079 `GrantGuardImmune`;S-106 `TurnOwnPagesOncePerTurn` | 仍有效(不符規則) |
| 宣告時記下,`_resolve_showdown` 才生效 | S-021 `NegateAttackAtEffectsEnd`、S-095 `RememberInBattle("defender_no_damage_family")` | 不生效 |
| 魔力勝負時計算 | 魔力加成(S-016 等),`side_breakdown` 的 `_negate` | 不生效 |

效果樹已有脫離式的 `Standby`(排程後立即完成,觸發時只解決 `then`),待命會出現在快照的作用中效果列表(`_effects_view`),`expires: "battle"` 的待命在 `_end_battle` 清除。

## Goals / Non-Goals

**Goals:**
- 防禦戰術的宣告時效果都在「効果の使用」的最後解決,防禦被無效時不解決。
- 擲幣與選對象仍在宣告時(規則「※重要」)。

**Non-Goals:**
- 攻擊方的宣告時效果(見 proposal「不改」)。
- 魔物效果防禦(M-039 等):目前只有固定合計魔力,沒有其他宣告時效果。

## Decisions

### D1:以待命種類 `effects_end` 延後解決

新增時機 `EffectsEnd`(`kind = "effects_end"`),防禦戰術的效果樹寫成 `When(SideIs("defense"), Coin(..., then=Standby(EffectsEnd(), expires="battle", then=<效果>)))`。`_resolve_showdown` 在魔力勝負計算前,依建立順序取出本場戰鬥的 `effects_end` 待命:防禦戰術未被無效時以 `effect_tree_resume` 解決,被無效時直接移除、不解決。

- 只對來源是本場防禦戰術(`battle.defense_spell`)且擁有者是防禦方的待命檢查「防禦被無效」;目前只有防禦戰術會排這種待命。
- 戰鬥在魔力勝負前結束(例如攻擊方魔物離場)時,`expires: "battle"` 照舊清除,不解決。

**替代方案:** 為每種效果各自在 `battle.data` 記旗標、由 `_resolve_showdown` 逐一處理(S-021 / S-095 現在的寫法)——每張新卡都要改引擎,不採用。或在 `side_breakdown` / 傷害計算時檢查 `defense_negated`——只能涵蓋減傷,攻擊無效與翻魔書仍會提前發生,不採用。

### D2:各卡改寫

| 卡 | 宣告時 | 「効果の使用」的最後 |
|---|---|---|
| S-021 | 擲 2 次 | 至少 1 次正面:攻擊無效 |
| S-025 | 擲 1 次 | 正面:攻擊無效 |
| S-027 | 擲 2 次 | 至少 1 次正面:這場攻擊的傷害 -1 |
| S-069(防禦) | 擲 1 次 | 正面:攻擊無效 |
| S-079 | — | 本場戰鬥以ウォンレイ保護時不受傷害 |
| S-095 | 擲 1 次 | 正面:本回合自己的キャンチョメ不受傷害 |
| S-106 | — | 攻擊無效;實際使攻擊無效時(攻擊尚未被無效)翻自己魔書 1 頁 |

`NegateAttackAtEffectsEnd` 與 S-095 的 `defender_no_damage_family` 特例移除,改用一般節點(`NegateAttack`、新的「本回合自己的某家族魔物不受傷害」節點)。`NegateAttack` 在攻擊已被無效時不重複發事件,並以 `ctx` 記錄是否實際無效,供 S-106「そうしたなら」判斷(新條件節點)。

### D3:顯示

`effects_end` 待命在作用中效果列表顯示為「效果使用結束時生效」(i18n `effect.standby.effects_end`),來源卡照一般待命顯示。戰鬥中效果的時機期間,快照的 `attack_negated` 為 false。

## Risks / Trade-offs

- [既有測試以「宣告後攻擊立即無效」為前提] → 依新時機改寫,另加「防禦被無效時不生效」的測試(先確認在修正前失敗)。
- [NPC 依 `attack_negated` 判斷是否值得出效果] → 延後後 NPC 在效果時機看到的是尚未無效的攻擊,可能多出效果;屬策略差異,不影響正確性。
- [S-106 翻魔書延後,翻完即敗的時點改到魔力勝負前] → 依規則,行為正確。
