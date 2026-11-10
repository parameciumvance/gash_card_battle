# Design

## Context

- 2026-11-10 explore:12 張的 atwiki 卡頁、FAQ 對照完。使用者決定:Ex-053 不分原因;Ex-060 另批;M-079 整張卡不能用。其餘依字面(解讀嚴格依字面的原則)。

## Decisions

### D1:雙方都不能選擇的魔物(M-075、Ex-099)

- `reg.unselectable(number, alone=False)`:常駐效果表;alone 時只在持有者場上只有這隻魔物時作用(Ex-099)。被「使えない」擋下時不作用。
- `primitives.unselectable_by(game, chooser, owner, slot)`:S-121 的 modifier(只對對手)與上面的常駐效果(雙方)。`selectable_opponent_slots` 改用它;新增 `selectable_own_slots`,自己選魔物的選項規格(`OwnMamodo`、`OwnOtherMamodo`、`OwnPartneredMamodo`、`OwnInjuredMamodo`、`ReturnableOwnMamodo`)與 `has_own_mamodo` 類條件改用它。
- 「すべてを選ぶ」也排除(Ex-099 FAQ A2;S-121 的既有決定)。保護、傷害的分配不是「選ぶ」,不受影響。

### D2:M-075 的自我封鎖

- `reg.lock_after_own_spell("M-075")`:玩家以這隻魔物使用戰術(攻擊、防禦、非戰鬥)時,建立以這隻魔物為對象的 `MAMODO_EFFECTS_LOCKED`(`DUR_NEXT_TURN`,擁有者是自己)。下一回合它的「魔物の効果」(含 D1 的不能被選擇)不作用。屬 `mamodo_effects` 分類,可被 E-036 移除(卡頁解說)。

### D3:Ex-051

- 常駐效果表 `reg.last_page_lock("Ex-051")`:持有者的魔書在最後一頁(`pos` 為最後一個對頁)時,對手不能使用事件卡(`event.restricted`)與搭檔的效果(`partner_effect_block_sources` 加上這個來源,含「このカードが場にある→」)。

### D4:Ex-053

- 常駐效果表 `reg.block_discarded_names("Ex-053")`:對手不能放出與「對手本回合進棄牌區的卡」(`discarded_this_turn`)同名的卡。`name_deploy_blocked(game, player, card)` 在 `play_block` 與效果放出的選項規格(魔書中的魔物 / 搭檔、棄牌區的搭檔、M-058)中檢查。

### D5:Ex-054

- `reg.on_play("Ex-054")`:放出時(「このカードが場にある→」,被「使えない」擋下時不作用)對可被選擇的對手魔物逐一建立限制,`data["phase"] = "battle"`(只在戰鬥階段作用)、`DUR_TURN`:魔物 `MAMODO_EFFECTS_LOCKED`、當時的搭檔 `PARTNER_LOCKED`(`data["card"]`,之後才裝上的不算)、MJ12 `FIELD_LOCKED`(`data["field_uid"]`)。`restriction_live` 依 `phase` 判斷。

### D6:Ex-059 / M-070

- 比照 P-042 的 `ScheduleBattleLock`:Ex-059 `(NO_PARTNER_EFFECTS, NO_EVENTS)`、M-070 `(NO_MAMODO_EFFECTS, NO_PARTNER_EFFECTS)`,`mamodo="ガッシュ・ベル"`,自己的回合。

### D7:M-079

- `book_hidden(game, owner)`:owner 場上有未被擋下的 M-079。
- `views_opponent_book(card)`:效果文含「相手の魔本(の今のページ)を見」。對手隱藏魔書時,這些卡的事件卡、非戰鬥戰術、攻防戰術宣告、啟動效果都不能使用(錯誤碼 `*.book_hidden`)。
- P-024 的「看對手翻開的頁」對隱藏魔書的玩家失效;檢視對手魔書的節點(`RevealOpponentBook` 等)在魔書隱藏時沒有選項(擋下 M-079 持有者自己的 PR-013 前半)。

### D8:P-047

- 選項:雙方場上不是魔物、且有「このカードが場にある→」效果(`reg.has_passive`)的卡(搭檔、MJ12)。對手的搭檔受 M-049 / M-066 / M-078 保護時排除。沒有可選時不能使用。

### D9:P-048

- `own_mamodo_discard_blocked(game, player)`:對手場上有未被擋下的 P-048。擋下 player 自己做的棄掉自己魔物:費用(啟動效果 `mode="discard"`、干擾 `discard_self`、擲幣改正面)、1 個行動的棄掉疊放上層(M-046)、自己效果的棄掉(`DiscardChosenMamodo`、`DiscardOwnMamodoByNumber`、`end_phase_discard` 的自己魔物)。傷害、對手效果造成的棄掉不受影響;卡片規則的強制離場(M-047 等)不算棄掉的行為。

### D10:P-049 / PR-012

- P-049:`turn_back_pages` 在戰鬥階段、對手場上有未被擋下的 P-049 時不回翻(`page_turn_restricted`)。`reg.action_discard("P-049", "partner")`。
- PR-012:`turn_pages`(效果造成的翻頁)在戰鬥階段、雙方任一場上有未被擋下的 PR-012 時不翻頁。傷害的翻頁不經過 `turn_pages`,不受影響。

## Risks / Trade-offs

- [放出、棄掉、選擇的路徑分散] → 以列舉的檢查點實作,game-engine/design.md 記下;新增路徑時要一併檢查。
