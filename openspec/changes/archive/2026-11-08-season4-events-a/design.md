# Design

## Context

見 proposal。搭檔效果的「使えない」目前只有整個玩家層級(`NO_PARTNER_EFFECTS`),分散在 6 處判斷;E-017 已有「看對手魔書、選卡棄掉」的流程(`RevealOpponentBook` + `OpponentBookCards` + `AwaitBookReviewEnd`)。

## Decisions

### D1:Ex-071 與魔物層級的搭檔限制

- 新旗標 `EFFECTS_LOCKED`(`target_slot` 指定魔物):擋這隻魔物的「魔物の効果」(`_mamodo_effect_blocks`)與它身上搭檔的效果。
- 新增 `partner_effect_block_sources(game, player, slot)`:整個玩家的 `NO_PARTNER_EFFECTS` 加上這隻魔物的 `EFFECTS_LOCKED`。原本直接判斷 `NO_PARTNER_EFFECTS` 的地方(`effect_block_sources`、`ability_block` 的搭檔、干擾、擲幣改正面、P-020 的 MP 鎖、P-031 家族禁止)改用它。限制綁在魔物上,所以之後才裝上的搭檔也被擋(atwiki 卡頁解說)。
- 期間這回合(`DUR_TURN`),【ステイ】;雙方的回合都能用(A/D 欄 AD)。對手沒有可選的魔物時不能用(比照 E-024,含 S-121)。

### D2:看對手魔書選卡(Ex-072 / E-050 / PR-013)

- `OpponentBookCards` 加篩選:`names`(卡名完全相符,Ex-072)、`same_name_as_discard`(E-050)、`after_current`(今のページより後ろ:翻開頁之後的頁,PR-013)。
- E-050 的同名判斷 `card_name_key`:去掉全形 / 半形括號內的文字比較;名稱含「＆」或「VS」的(W / VS 魔物)須完全相符。目前資料中沒有 W / VS 魔物。
- Ex-072「2枚まで」:選第 1 張後可選第 2 張或停止(兩次都可不選,`OrSkip`)。沒有可選的卡時比照 E-017 看完魔書即結束。
- PR-013:`AsOpponent` 由對手看自己的魔書並選(強制,「選び、捨て札にする」);對手棄了(有可選的卡)才換自己看對手的魔書選 1 張(「そうしたなら」)。都不付費。

### D3:E-051、E-054、Ex-073、Ex-100

- E-051「何枚でも」:沿用 P-036 的「選魔書中的搭檔頁 → 選裝備的魔物」,每次選完可再選或停止;一隻魔物 1 張搭檔、場上最多 3 隻,所以最多 3 次(樹展開 3 層)。至少有 1 張可放出的才能使用(比照「選得到對象」的慣例)。
- E-054「『このカードを捨て札にする→』効果を持つ魔物」:頂層的卡有棄掉自己作為費用的效果(啟動效果 `mode="discard"`、干擾 `discard_self`、擲幣改正面);`reg.has_discard_cost_effect` 統一判斷(S-144 也改用)。選擇受 S-121 限制。
- Ex-073:`GainMpPerCount(OwnDiscardMamodoCards())`。Ex-100:`Coin(2, HeadsAtLeast(2), GainMp(5))`。

### D4:Ex-101

- `Game.emit` 在 `mp_changed` 的 delta 為負、且目前是戰鬥階段時,累加到 `PlayerState.battle_phase_mp_lost[turn_no]`(費用、效果的減少都算;只保留本回合)。atwiki 卡頁解說:使用前減少的與這張卡的費用都算。
- 待命 `end_phase_mp` 帶 `half_battle_mp_lost`,解決時才計算增加量 = 減少量 // 2。

## Risks / Trade-offs

- [搭檔限制的判斷點改動多] → 既有測試全跑;新增 Ex-071 對常駐、啟動、干擾的測試。
- [E-051 最多 3 次] → 目前沒有讓 1 隻魔物裝 2 張搭檔的卡;出現時再改成真正的迴圈。
