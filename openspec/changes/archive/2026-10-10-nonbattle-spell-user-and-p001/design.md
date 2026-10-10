## Context

- `_nonbattle_spell_user` 未指定使用魔物時回傳 None,費用以 `spell_cost(..., slot=None)` 取未被封鎖者的最低費用;`book_card_used` 事件只有 `player`、`card`、`page`。
- 前端 `logText` 的 `book_card_used` 一律用 `log.book_card_used`(「使用事件卡《…》」)。
- 前端 `pickSpellUser(p, entry, nonbattle, cb)`:非戰鬥時「兩隻以上可選且費用不全相同」才進場上選擇。
- 啟動效果已有 `own_turn`(M-018),`_use_field_ability` 與 `_use_borrowed_effect` 都檢查,快照的 `ability.own_turn` 讓前端停用並顯示「只能在自己的回合使用」。

## Goals / Non-Goals

**Goals:** 記錄正確描述戰術的使用;非戰鬥戰術的使用魔物選擇與攻防一致;P-001 不能在一定沒有效果的時機使用。

**Non-Goals:** 不限制 P-007 或其他「下一場戰鬥」類效果(P-007 攻擊與防禦都有作用)。

## Decisions

### D1:非戰鬥戰術的使用魔物一定具體

- `_nonbattle_spell_user` 未指定時,回傳能用且未被封鎖者中費用最低的第一隻(依場上順序);費用依它計算,結果與原本的最低費用相同。
- `book_card_used` 對戰術加 `mamodo`(使用魔物的頂層卡號);事件卡不加。

### D2:記錄文字

- 事件卡:沿用 `log.book_card_used`,但文字的語意明確為事件卡(現有文字不變)。
- 戰術:新增 `log.spell_used`(「{player} 使用戰術《{card}》」)與 `log.spell_used_by`(「{player} 以〔{mamodo}〕使用戰術《{card}》」),依事件是否帶 `mamodo` 選擇;以 `CARDS[ev.card].type` 判斷類型。

### D3:非戰鬥戰術的選擇規則

- `pickSpellUser`:可選的只有一隻 → 直接送出;兩隻以上 → 場上選擇(攻防、非戰鬥相同)。移除「費用相同就不問」的分支與 `nonbattle` 參數。

### D4:P-001 限自己回合

- `reg.activated("P-001", ..., own_turn=True)`;引擎與前端沿用 M-018 的機制,不需新程式。

### 行為決定(reconciliation 時寫入 `card-effects/design.md`「行為決定與理由」)

- **P-001 只能在自己的回合使用**:對手回合的「次のバトル」是對手的攻擊,自己不會以ガッシュ・ベル的戰術攻擊,效果一定不發生,以時機限制防止無效使用。P-007 在對手回合仍可能作用於自己的防禦戰術,不限制。專案負責人確認,`Confirmed`。這與 P-003 / P-004 / P-006「對象不成立時能用但沒有效果」不同:那些在該時機仍可能有效果,P-001 在對手回合一定沒有。

## Risks / Trade-offs

- [S-026 等多一次選擇] → 與攻防一致,使用者已確認;只有一隻可選時不問。
