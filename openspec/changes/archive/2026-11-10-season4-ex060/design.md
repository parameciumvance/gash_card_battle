# Design

## Context

- 2026-11-10 explore:Ex-060 的 atwiki 卡頁(pages/434)只有解說,沒有 FAQ;規則頁 94、2077、2078 沒有相關裁定。解說提到它擋「好きなページ」的使用與放出(フライング・ビート等),也擋 ガッシュ・ベル《失われた記憶》(M-016)這類移動頁的效果。
- 使用者決定:(1) 使用其他頁卡片的效果:擋發動也擋使用;(2) 持有者自己的 E-027 讓對手放出時,對手也受限;(3) 重疊算放出;(4) Ex-053 的遺漏另開 change。

## Decisions

### D1:今のページ與作用對象

- 「今のページ」= 目前翻開的兩頁(`open_pages()`),與一般放出、使用卡片的判定相同。
- 常駐效果表 `reg.outside_page_lock("Ex-060")`;`outside_page_locked(game, player)`:player 的對手場上有未被「使えない」擋下的這類卡。
- 只限制持有者的對手**自己的魔書**(「相手自身の魔本」);對手影響持有者魔書的效果(E-016、E-037 等)不受限。限制的是「相手は…できない」的動作,不論是誰的效果(D3)。

### D2:使用其他頁卡片的效果(使用者決定:擋發動也擋使用)

- 判定:卡片的效果樹含「允許從其他頁使用卡片」的待命節點(`ScheduleSpellFromAnyPage`、`ScheduleAnyPageUse`、`ScheduleEventFromChosenPage`、`ScheduleSpellFromNextSpreads`),即 P-015、P-025、P-037、PR-006、M-037、S-145、Ex-037。以卡為單位判定(目前這些卡都只有這一個效果)。
- 發動:啟動效果(`ability.other_pages`)、非戰鬥戰術(`spell.other_pages`)、事件卡(`event.other_pages`)、戰術宣告(`spell.other_pages`)都檢查。S-145、PR-006 是非戰鬥戰術,整張不能使用。
- 使用:`_spell_any_page_standby` 在受限時不回傳待命,Ex-060 上場前建立的待命也不能從其他頁使用卡片;翻開的兩頁照常使用(不經待命)。

### D3:放出、棄掉、移動頁

- 自己魔書頁的選項規格在受限時只列翻開的兩頁:`AttachablePartnerPagesInOwnBook`、`DeployableMamodoInOwnBook`(含 `MamodoOrPartnerPagesInOwnBook`)、`OwnBookPartnerNamed`、`OwnBookCopiesOf`(S-043、S-048、S-086,重疊算放出)、`OwnBookEvents`、`CanStackFromBook`、`OwnEarlierPages`(M-016 要把前面的頁換過來,前面的頁不會是翻開的頁,所以不能使用)。
- 選項規格以 ctx 的玩家判斷:E-027 第 1 項由對手選、放出(`AsOpponent`),Ex-060 持有者自己用 E-027 時,對手也只能選翻開的兩頁(使用者決定)。
- 目前沒有棄掉自己魔書其他頁卡片的效果;之後的卡(如 M-073 的「使った術カードを捨て札にする」)要套用 `outside_page_locked`。
- 不受影響(Inferred):放回魔書空頁(E-033、M-025、S-146:卡片原本不在魔書裡)、回翻魔書(P-018、PR-007、E-005:移動的是翻開位置,不是卡片)。
