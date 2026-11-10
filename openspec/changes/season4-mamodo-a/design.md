# Design

## Context

- 2026-11-10 explore:15 張的 atwiki 卡頁與 FAQ、規則頁「魔力勝負」對照完,依字面決定(使用者的原則:解讀嚴格依字面)。

## Decisions

### D1:魔物效果攻擊的條件(Ex-052 / Ex-055)

- `reg.mamodo_attack(..., condition=)`:條件為選項規格 / 條件物件(`SelfHasPartnerNamed("リィエン")`),不成立時不能宣告(`attack.condition`)。搭檔名稱完全相符。

### D2:M-071

- 規則頁「防御側が大きいか、同じ:攻撃失敗」「攻撃が無効化されている場合、攻撃失敗」:魔力勝負的結果為防禦方勝(引擎 `winner == "defender"`)就是「負けた」。
- 「この魔物で攻撃した」:這隻魔物使用的戰術攻擊或它的魔物效果攻擊。常駐效果,被「使えない」擋下時不生效。在魔力勝負判定後、傷害解決前增加。

### D3:M-072

- 「自分がコイン1個を投げるごとに」:自己擲的每一枚,包括重擲(M-012 等的「投げなおす」);對手替我擲的(E-020)不算,我替對手擲的算。改成正面不是「投げる」,不算。
- 在 `flip_coins` 與 `_reflip_one` 擲出時呼叫;常駐效果,多張各自生效(同名上限 1,實際只會 1 張)。

### D4:MP 增加的限制(M-076、P-044)

- P-044:比照 P-032,`RestrictOpponent(flag=NO_MP_GAIN, duration=DUR_NEXT_TURN)`。FAQ:「次のターン中」包括開始與結束階段,所以開始階段翻頁、結束階段翻頁的 MP 也不增加。
- M-076:對手開始階段(`START`)增加的 MP 合計(`start_phase_mp_gain`)上限 2,翻頁與開始階段效果都算。
- 引擎:MP 增加集中判斷 `mp_gain_allowed(game, player, amount)`,`gain_mp`、開始階段翻頁、結束階段翻頁都經過它;被擋時發 `mp_gain_prevented`。E-052 的退回(`refund`)不受影響(season4-e052 的決定)。

### D5:干擾的費用棄卡(P-046、M-080)

- 一般干擾的流程原本寫死「棄掉整隻魔物、`mamodo:` key」。改為依 `spec["zone"]`:搭檔只棄掉搭檔(`discard_attached_partner`)、key 為 `partner:`;使用紀錄的 `returns` 一併依 zone。
- M-080《乱入》:`reg.jammer(..., opponent_turn=True)` 只在對手是回合玩家時提供;干擾在戰鬥中不能用(既有)。
- M-080《バトル乱入》:`reg.activated(mode="discard", timing="battle", condition=OpponentIsAttacking())`,`NegateAttack`。
- 兩個效果分開計次:干擾的使用 key 在同一張卡也有啟動效果時加後綴(`mamodo:M-080:jammer`)。

### D6:M-081

- `reg.treated_as("M-081", "ゾフィス")`(比照 M-047)。
- 《悪しき力》:`mode="declare"`、`per_game=True`、非戰鬥;選對手 1 隻魔物,新旗標 `MAMODO_EFFECTS_LOCKED`(綁在魔物上,`DUR_GAME`)只擋「魔物の効果」。FAQ A1:同卡號的新魔物不受影響(綁 uid)。分類 `mamodo_effects`(E-036 可移除)。

### D7:Ex-061

- 待命 `reuse_ability`(本回合、1 次、家族「ダニー」):使用「ダニー」的魔物效果(啟動效果、魔物效果攻擊 / 防禦)時,若該效果本回合已用過(或已達次數),可以消耗待命以費用 0 再用 1 次;使用條件照舊(Ex-055 FAQ A1)。未用過的效果不消耗待命。

### D8:P-045

- `reg.coin_set_heads("P-045", spell_user="ドンポッチョ")`:只適用於自己的「ドンポッチョ」使用的戰術擲出的硬幣。判斷:擲幣來源是戰術,且效果的 ctx 中使用的魔物(非戰鬥戰術的 `user_slot`;攻防戰術依 `side` 取戰鬥的使用魔物)家族為ドンポッチョ。效果文「ドンボッチョ」依 FAQ 當作ドンポッチョ。

### D9:其餘

- M-078:`reg.partner_discard_guard`。M-082:選對手魔物、`NO_PROTECT_SLOT`、`DUR_TURN`,雙方回合的非戰鬥。P-050:`StealOpponentMp(amount=2)`。
- M-083:`reg.stack_on(family="ニャルラト")`;《絆のリボン》MP 1、非戰鬥,選自己魔書任一頁(含未翻開)名為「詞音」的搭檔,再選裝備的ニャルラト(比照 E-051 的流程)。

## Risks / Trade-offs

- [MP 增加的路徑分散] → 集中到 `mp_gain_allowed`,測試涵蓋翻頁、效果、結束階段。
