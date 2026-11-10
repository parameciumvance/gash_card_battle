# Design

## Context

- 2026-11-10 explore:atwiki 卡頁 pages/1467、1468、280、1477、1501 都沒有 FAQ,只有解說。使用者決定:M-073 只有從翻開頁以外使用才算;M-077 作用在使用當下的回合,M-030 維持只在自己回合有效(在對手回合用沒有價值,M-077 可以打斷對手)。

## Decisions

### D1:M-073

- `ScheduleAnyPageUse(mamodo="ティオ", by_name=True, exclude_last=True, defense_only=True, discard_after_battle=True)`:沿用 P-037 的「X の術」判定;`defense_only` 只允許防禦。
- 從翻開頁以外使用時消耗待命(`_consume_any_page`),並把(玩家、頁)記在戰鬥的 `discard_after_battle`;`_end_battle` 時把仍在魔書的那張卡棄掉(防禦被無效也棄,已使用過)。翻開頁照一般規則,不消耗待命(使用者決定)。
- 屬於「使用其他頁卡片的效果」,Ex-060 作用中不能使用(`uses_other_pages` 自動涵蓋)。

### D2:M-074 + S-135

- `reg.stack_on("M-074", family="ウマゴン", spell_only=True)`、`reg.action_discard("M-074", "top")`、`reg.partner_discard_guard("M-074")`。疊放對象沿用 family 的規則(非疊放型的ウマゴン)。
- S-135 比照 S-086:`CanStackFromBook("M-074")` + `OwnBookCopiesOf("M-074")` + `StackFromBookOnto()`。

### D3:M-077

- `EndThisBattlePhase` 節點:排 `end_battle_phase` 待命與 `skip_end_flip`(`data["this_turn"]`,不論誰的回合)。
- `_run_deferred_effects` 在沒有待決事項與待詢問的干擾時,消耗 `end_battle_phase` 並進入結束階段;干擾無效時快照還原,待命隨之消失,戰鬥階段照常繼續。
- 結束階段的效果照常解決;強制翻頁時 `skip_end_flip` 的判定:擁有者是回合玩家(M-030),或 `this_turn`(M-077)。

### D4:M-084

- `turn_pages(..., by=)`:效果的使用者;`by` 是對手時累加被翻玩家的 `pages_turned_by_opponent`(本回合,回合結束歸零)。傷害不經過 `turn_pages`,不算;PR-012 擋下的翻頁沒有真的翻,不算(Inferred)。
- 條件 `pages_turned_by_opponent > 0`;效果翻對手魔書該張數(本身也以 `by` 記錄,對手的 M-084 可以翻回來,卡頁解說)。
