## Context

- 規則(atwiki 規則頁 pages/94「MJ12」「①魔本からカードを場に出す」「②場にあるカードの効果を使う」):MJ12 在自己或對手的戰鬥階段從魔書放出,1 個行動 1 張、每回合張數不限;同名在自己場上限 1 張;不裝在魔物上,放在 MP 置き場下方;效果在雙方的戰鬥階段可用,每個效果每回合 1 次(「使用を宣言する」「MPを○減らす」「このカードを捨て札にする」皆同)。
- 引擎已有:魔物 / 搭檔的放出(`_play_card`、`play_block`)、場上啟動效果(`_use_field_ability`、`ability_block`、`reg.activated`)、魔書傷害(`DamageOpponentBook`,P-041)、自魔書任一頁放出(`DeployableMamodoInOwnBook` E-012、`AttachablePartnerPagesInOwnBook` P-036)、看對手今のページ(`PeekOpponentOpenPages`,Ex-045)、被對手效果減少 MP 的統計(`reduce_opponent_mp`)。
- 前端已有獨立卡區(讀快照 `field_cards`)。

## Goals / Non-Goals

**Goals:** MJ12 能放出與使用效果;6 張 MJ 與 Ex-074 依效果文運作;快照、前端、NPC 支援。

**Non-Goals:** 獨立バルカン(第 12 賽季);Ex-054(第 4 賽季、尚未實作)的「相手の場のカードすべて」— 實作 Ex-054 時要涵蓋獨立卡區(見 D6)。

## Decisions

### D1 獨立卡區的資料

- `PlayerState.field_cards: list[FieldCard]`,`FieldCard(uid, card)`,依出場順序;uid 與魔物槽共用 `next_uid`。
- 放出:`play_card`(今のページ),`play_block` 對 MJ12 只檢查同名(`same_name`);消耗該頁(同魔物 / 搭檔)。事件 `card_played` 帶 `zone: "field"`、`field_uid`。
- 棄掉:`discard_field_card` 移入棄牌區,事件 `card_discarded` 帶 `zone: "field"`、`field_uid`(棄牌動畫的起點)。

### D2 MJ12 的效果

- 以 `reg.activated` 登記(效果樹,`self_slot` 為 None),使用時 `use_field_ability` 帶 `zone: "field"`、`field_uid`;已使用以 `field:<卡號>` 記錄(與魔物 / 搭檔相同以卡號為 key:同回合棄掉後再放出同卡號的卡,效果仍不能再用,MJ-001 效果文「1ターンに1回」也這樣讀)。
- 時機:MJ 都沒有戰鬥圖示 → `timing="nonbattle"`、不限自己的回合(card-effects design「卡面沒有戰鬥圖示的場上效果是非戰鬥時機」;MJ-001 FAQ「相手ターン中でも使用できる」)。
- 「このカードを捨て札にする→」先棄掉再解決(與搭檔相同)。
- MJ 的效果不是「魔物の効果」也不是「パートナーの効果」,`NO_MAMODO_EFFECTS` / `NO_PARTNER_EFFECTS` 等限制不擋。
- ジャマー:M-026 回應魔物效果、M-032 / Ex-034 回應事件;M-065 回應使持有者 MP 減少的行動,MJ 中只有 MJ-006 會減對手 MP,但它是「このカードが場にある→」,依規則書第 42 頁不能被「無効にする」。所以 MJ 的效果目前不提供ジャマー回應。

### D3 各卡

- MJ-001:`DamageOpponentBook(amount=1)`(走保護管線,可保護)。
- MJ-002 / MJ-005:新 modifier `side_power`(`target_player`、`data.side` attack / defense、本回合),加在合計魔力(戰術、魔物效果攻擊、魔物效果防禦三條路徑都加,FAQ:「防御であれば術や魔物の効果でも」「『魔物の効果』…にも適用」)。明細項 `side_power`。
- MJ-003:先選「魔書中可放出的魔物頁或可裝備的搭檔頁」(兩者合併成一個選擇,`pick_card_in_own_book`),魔物依 E-012 放出(含疊放規則與出場效果)、搭檔依 P-036 選裝備對象。沒有可放出的卡時不能使用(`condition`)。
- MJ-004:`PeekOpponentOpenPages`(只讓使用者看到),MP 1。
- MJ-006:在 `reduce_opponent_mp` 實際減少後,被減的一方場上有 MJ-006 時,對手減少同樣數量(來源 `MJ-006`)。「雙方都有時各適用 1 次」:由 MJ-006 造成的減少,再觸發對方的 MJ-006 一次(來源 `MJ-006:mirror`);`MJ-006:mirror` 造成的減少不再觸發。強制效果。E-004 的「歸零」也算被對手的效果減少(與 E-028 / E-035 的統計一致),同樣觸發。
- Ex-074:事件、自己的回合(卡面圖示),對手場上有 MJ12 時才能使用;選對手 1 張 MJ12 棄掉(選項 `zone: "field"`,在獨立卡區原位置選)。

### D4 快照

- `field_cards`: `[{uid, card, ability_used, ability_block?}]`;`ability_block` 只給持有者(同魔物槽)。翻開頁的 MJ12 附 `play_block`(同魔物 / 搭檔)。

### D5 前端

- 翻開頁的 MJ12:放大檢視提供「放出」(與魔物同一套按鈕與停用原因)。
- 獨立卡區的卡:放大檢視的效果按鈕(`ability_block` 的停用原因);決策目標 `zone: "field"` 在原位置發光、放大檢視「選擇」。
- 動畫:放出時飛入獨立卡區,棄掉時從獨立卡區飛向棄牌區。

### D6 待辦交互

- Ex-054(尚未實作)「相手の場のカードすべてを選ぶ…そのカードの効果を使えない」:實作時要包含對手的獨立卡區,MJ-006 也會被擋(「場にある→」也算使用)。

## Risks / Trade-offs

- [解讀] MJ-003 的魔物與搭檔合併成一個選擇;效果文「魔物カードかパートナーカード1枚を選び」,由使用者選,Inferred。
- [解讀] MJ-006 的鏡像次數依註記「たがいに1回ずつ」:初次觸發 + 對方回應 1 次,Inferred(與 FAQ 的例子相同)。
