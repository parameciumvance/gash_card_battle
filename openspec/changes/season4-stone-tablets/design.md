# Design

## Context

- 規則頁「※石版魔物」:魔物圖示為石版樣式的卡;「石版魔物には、基本的に通常の魔物と違いはありません。ただし、石版魔物だけに効果のあるカードがいくつかあります」;從魔書放出時是健康狀態。
- 「石版状態」(規則頁「石版状態」)目前沒有卡會造成,不實作,規則頁也不寫。
- 2026-11-10 explore 的決定:Ex-056~058 一併開放;Ex-069 之後放出的也加;M-085 視為選不到對象;前端標籤與規則頁都做。

## Decisions

### D1:石版魔物

- `CardDef.stone_tablet`(`cards.json` 的 `stone_tablet`)。`is_stone_tablet(game, slot)`:最上層的卡是石版魔物。

### D2:Ex-000

- `EffectOptions` 兩個選項,requires 為選項規格 `OpponentMamodoByStone(stone)`:自己場上有「同類」(stone=True 時為石版魔物,False 時為石版魔物以外)的魔物時沒有選項;否則為對手場上該類、可被選擇的魔物(`selectable_opponent_slots`,S-121)。
- 選定後選對手魔物,`DamageChosenOpponentMamodo`(一般保護流程,比照 Ex-024)。兩個選項都沒有時不能使用。

### D3:Ex-049

- 新限制旗標 `NO_STONE_TABLET_EFFECTS`(對手,`DUR_TURN`):`mamodo_effect_block` 對最上層是石版魔物的魔物回傳 `mamodo_restricted`,所以啟動效果、魔物效果攻防與「このカードが場にある→」(`card_effect_blocked`)都被擋。依當下判斷,之後放出的石版魔物也算。
- 限制分類為 `mamodo_effects`(E-036 可移除、E-045 算有限制效果)。啟動效果 `mode="mp"`、`mp_cost=1`、非戰鬥。

### D4:Ex-069

- 玩家層級 modifier `power_stone_tablet`(`DUR_UNTIL_END_OWN_NEXT_TURN`):`power_breakdown` 對最上層是石版魔物的魔物加 amount;之後放出的也加(比照 E-048)。
- 比照 E-048 沒有使用條件。列入 `POWER_UP_MODIFIERS`(Ex-070 可取除)。

### D5:M-085

- `reg.block_discard_return("M-085")`:常駐效果表。`discard_return_blocked(game, player)`:player 的對手場上有未被「使えない」擋下的這類卡。
- 套用處(視為選不到對象):`PlayablePartnerInDiscard`(E-011、S-090)、`PartnerDiscardedThisTurn`(E-022)、`DiscardedMamodoToReturn`(E-033)、`DiscardedCardsToReturn`(M-025)、`OpponentDiscardedPartner`(M-058)、E-052 的 `_return_cost_card`(留在棄牌區,MP 照退)。各卡的使用條件照舊:以選項為條件的(E-011、S-090、E-033、M-058)不能使用;E-022 照常擲幣,沒有可選的搭檔。

### D6:Ex-056 / Ex-057 / Ex-058

- `reg.spell_compat`:Ex-056「マルス」、Ex-057「エシュロス」的戰術(家族),Ex-058 名稱為「ビライツ」的戰術卡(不限家族)。屬「このカードが場にある→」,被「魔物の効果を使えない」(含 Ex-049)擋下時不能使用。

### D7:前端

- 資訊列「石版」標籤(`card.tag.stone_tablet`),樣式比照干擾標籤。
- 規則頁「卡片種類」加一段石版魔物說明。

## Risks / Trade-offs

- [M-085 的套用處以列舉] → 新的「棄牌區放回」效果要一併檢查;game-engine/design.md 記下。
