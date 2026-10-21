## Context

啟動效果以 `PlayerState.used_abilities`(`"{zone}:{卡號}"`)與 `used_per_game` 記錄,`_use_field_ability` 檢查;直接攻擊(`_validate_mamodo_attack` / `_prepare_mamodo_attack`)與直接防禦(`_declare_mamodo_defense`)沒有記錄。快照 `_ability_view` 只送效果規格,前端 `abilityUsableNow` 只看時機與 MP。ジャマー(M-026)以快照還原,`_queue_jammer` 在效果使戰鬥開始 / 結束時放棄。結束階段效果流程(`_resolve_end_phase_effects`)目前收 M-047 / E-041 / E-042,E-038 在強制翻頁之後另外處理。

## Goals / Non-Goals

**Goals:** 直接攻擊 / 防禦每回合 1 次;畫面正確反映已使用;E-038 時機符合規則;M-026 能無效直接攻擊 / 防禦。

**Non-Goals:** 既有常駐效果的「使えない」檢查(todo);其他效果的ジャマー對象擴充。

## Decisions

### D1:直接攻擊 / 防禦的使用紀錄
沿用 `used_abilities`,鍵為 `"mamodo_attack:{卡號}"` 與 `"mamodo_defense:{卡號}"`(與啟動效果 `"mamodo:{卡號}"` 分開,M-039 的《格闘》《ガード》各自計算)。在付費時記錄(直接攻擊在戰鬥開始 `_prepare_mamodo_attack`,直接防禦在宣告),宣告時驗證已用過就拒絕(`attack.used` / `defense.used`)。以卡號計(棄掉後重新放出同編號的卡,本回合仍不能用,與啟動效果一致)。

### D2:快照的已使用旗標
`_slot_view` 加 `ability_used`、`partner_ability_used`(本回合已使用或一場限 1 次已用)、`mamodo_attack_used`、`mamodo_defense_used`,值為 `"turn"` / `"game"` / `false`。前端 `abilityUsableNow` 與直接攻擊 / 防禦按鈕依此停用並帶原因(`ui.ability.used_turn` / `ui.ability.used_game`)。只送給所有視角都看得到的資訊(使用本來就公開)。

### D3:E-038 納入結束階段效果
`_end_phase_effects` 加入回合玩家的 `end_phase_mp` 待命;`_resolve_end_phase_effect` 對它 `gain_mp`。移除 `_continue_end_phase` 中強制翻頁之後的處理。E-038 是自己回合使用(A),所以只收回合玩家的。

### D4:M-026 無效直接攻擊 / 防禦
ジャマー的動作種類 `mamodo_effect` 擴充:直接攻擊在戰鬥開始(付費、記錄、`battle_started` 之後,`_ask_injure_target` 等宣告時效果之前)、直接防禦在宣告之後,若對手有可用的 `mamodo_effect` ジャマー,以新的佇列形式 `game.jammer = {"player", "negated", "battle_side": "attack" | "defense"}` 詢問(不存快照)。使用時:付 M-026 的費用並記錄,`battle.attack_negated` / `defense_negated = True`、`<side>_negated_by = "M-026"`,發 `effect_negated`。連鎖:被無效的一方有可用的 M-026 時,以同樣的形式詢問,使用則把該側的無效旗標清除(恢復)。宣告時效果(擲幣、選對象)在ジャマー詢問結束後才繼續(攻擊:`_attack_declare_effects`;防禦:進入效果步驟)。
- 不採用快照還原:直接攻擊本身就是開始戰鬥,還原牽動流程;規則書第 42 頁「無効にする」也定義為取消戰鬥中的攻擊與防禦。

### D5:確認(使用者 2026-10-21)
直接攻擊 / 防禦每個效果每回合 1 次;M-026 可無效它們,以攻擊 / 防禦無效處理;E-038 在強制翻頁之前並參與排序。

## Risks / Trade-offs

- [ジャマー詢問插在戰鬥開始與宣告時效果之間] → 詢問結束後才續行;測試直接攻擊時有 S-089 待命的情況順序正確。
- [快照欄位增加] → 只加布林 / 字串,前端缺欄位時視為未使用。
