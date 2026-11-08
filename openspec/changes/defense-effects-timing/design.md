# Design

## Context

見 proposal.md「Why」。現有三種寫法:

| 寫法 | 卡 | 防禦被無效時 |
|---|---|---|
| 宣告時直接生效 | S-025、S-069(防禦)、S-106 `NegateAttack`;S-027 `AdjustDefenseDamage`;S-079 `GrantGuardImmune`;S-106 `TurnOwnPagesOncePerTurn` | 仍有效(不符規則) |
| 宣告時記下,`_resolve_showdown` 才生效 | S-021 `NegateAttackAtEffectsEnd`、S-095 `RememberInBattle("defender_no_damage_family")` | 不生效 |
| 魔力勝負時計算 | 魔力加成(S-016 等),`side_breakdown` 的 `_negate` | 不生效 |

戰術已有依戰鬥時點呼叫的掛鉤(`on_declare`、`on_win`、`on_counter`、`on_defense_damaged`),宣告時的結果以 `RememberInBattle` 記在 `battle.data`、結算時以 `BattleRemembered` 讀取(S-069 攻擊時的擲幣)。

## Goals / Non-Goals

**Goals:**
- 防禦戰術的宣告時效果都在「効果の使用」的最後解決,防禦被無效時不解決。
- 擲幣與選對象仍在宣告時(規則「※重要」)。

**Non-Goals:**
- 攻擊方的宣告時效果(見 proposal「不改」)。
- 魔物效果防禦(M-039 等):目前只有固定合計魔力,沒有其他宣告時效果。

## Decisions

### D1:戰術掛鉤 `on_effects_end`

`SpellRider` 新增掛鉤 `on_effects_end`(效果樹,與 `on_win` / `on_counter` 同類)。`_resolve_showdown` 在魔力勝負計算前,本場防禦戰術沒被無效時執行它的 `on_effects_end`;被無效時不執行。宣告時的擲幣結果由 `on_declare` 以 `RememberInBattle(key="defense_coin_heads")` 記下,`on_effects_end` 以 `BattleRemembered` 判斷。鍵名與攻擊方 S-069 的 `coin_heads` 分開,因為雙方可能同時使用 S-069。

**替代方案:**
- 用效果樹的 `Standby`(待命種類 `effects_end`)延後解決——第一版這樣做。但效果文沒有【スタンバイ】,放進 `state.standby` 會讓它成為 P-034 / E-036 等「待命中的效果」的對象,也會顯示成待命;使用者指出後改為掛鉤。
- 為每種效果各自在 `battle.data` 記旗標、由引擎逐一處理(S-021 / S-095 原本的寫法)——每張新卡都要改引擎。
- 在傷害計算時檢查 `defense_negated`——只能涵蓋減傷,攻擊無效與翻魔書仍會提前發生。

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

`NegateAttackAtEffectsEnd` 與 S-095 的 `defender_no_damage_family` 特例移除,改用一般節點(`NegateAttack`、新的「本回合自己的某家族魔物不受傷害」節點)。S-106「そうしたなら」以新條件節點 `AttackNotNegated` 判斷:解決時攻擊尚未被無效,才使攻擊無效並翻魔書。

### D3:顯示

這些效果不是待命,不出現在作用中效果列表(與原本的 S-021、S-095 相同);擲幣結果照舊顯示在記錄。戰鬥中效果的時機期間,快照的 `attack_negated` 為 false,雙方 pass 後魔力勝負的結果才顯示無效。

## Risks / Trade-offs

- [既有測試以「宣告後攻擊立即無效」為前提] → 依新時機改寫,另加「防禦被無效時不生效」的測試(先確認在修正前失敗)。
- [NPC 依 `attack_negated` 判斷是否值得出效果] → 延後後 NPC 在效果時機看到的是尚未無效的攻擊,可能多出效果;屬策略差異,不影響正確性。
- [S-106 翻魔書延後,翻完即敗的時點改到魔力勝負前] → 依規則,行為正確。
