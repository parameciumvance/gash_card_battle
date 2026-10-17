## Context

第 1、2 批與 `declare-time-resolution` 已建立:限制分類(`spell_block`)、移除(`remove_restrictions`)、宣告時結果存於 `battle.data`、新時效 `DUR_UNTIL_END_OWN_NEXT_TURN`。M-008 的「宣告時詢問可選減費」(`_ask_spell_discount`)是宣告時中途決策的先例。

## Goals / Non-Goals

**Goals:** 27 張依效果文;新機制做成之後可沿用的形式(追加費用、戰鬥結束時生效、MP 紀錄)。

**Non-Goals:** 翻頁中使用卡片的時機(S-638 / PR-045,之後的彈);S-103 只設限制不新增時機。

## Decisions

### D1:宣告時的追加費用
`SpellRider.extra_cost = (step, max, power, damage)`:S-067 `(2, 6, 2000, 1)`、S-097 `(2, 2, 4000, 0)`。宣告時(與 M-008 的減費詢問同一處,先問減費再問追加)建立 `spell_extra_cost` 決策,選項為付得起的 0、step、2·step…;選擇記在宣告資料,開戰付費時一併支付,魔力以 `add_spell_power` 記入明細、傷害寫入 `attack_damage_delta`。防禦宣告同理。

### D2:戰鬥結束時生效
新待命種類 `after_battle`(`expires: "battle"`,`data` 帶要套用的內容):`engine._end_battle` 在清除戰鬥前,若攻擊沒被無效,套用屬於這場戰鬥的 `after_battle` 待命。S-068 的待命帶 `restricts=["spells"]`,所以排定期間 P-034 / E-036 會把它移除。S-062 以同一機制在戰鬥結束時加持續效果 `attr_power`(`data`:屬性「氷」、+2000;時效 `DUR_UNTIL_END_OWN_NEXT_TURN`;已有 S-062 的 `attr_power` 生效時不再加,即「不重複」),魔力明細計入雙方使用的冰屬性戰術。

### D3:MP 紀錄
`PlayerState` 加 `mp_reduced_by_opponent`(本回合被對手效果減少的總量)與 `start_phase_mp_gain`(本回合開始階段增加的 MP),回合結束時歸零。前者在 `reduce_opponent_mp` 與 E-004 的歸零處累加實際減少量(被 P-021 擋下為 0);後者在開始階段翻頁時記錄。

### D4:各卡
- S-061:`SpellRider.counter_damage_from_attack`,反擊傷害取 `_attack_damage_amount`(再加 `own_damage_bonus`)。S-066:`counter=True`。
- M-052:持續效果 `power` 與 `damage_delta` 以 `data["when"] = "attacking"` 標記,只在這隻魔物是攻擊方魔物時計入(`slot_power` 與攻擊傷害)。
- P-033:`no_attack_spell` 旗標帶 `target_slot`(只限那隻魔物的戰術),`spell_block` 依 `target_slot` 判斷;分類同 `no_attack_spell`(spells)。
- S-098:依序詢問,不把兩個效果並列(試玩時發現並列會讓玩家選了重用而錯失回復):有負傷魔物時先問「回復 / 不使用」,回復後再選要重用的戰術(可不使用);不回復或沒有負傷魔物時直接選要重用的戰術。重用的對象在使用時選定(使用者於 2026-10-17 改為使用時指定):`UsedSpellPagesThisTurn` 列出本回合已用過、仍在魔書中的戰術頁(S-098 除外),選項在魔書上選擇(決策種類 `pick_used_spell`);待命 `spell_reuse` 帶 `data["page"]`,只有那一頁在用到上限時可再用一次、費用 0 並消耗。使用條件:有負傷魔物或有已用過的戰術。
- M-037:待命 `spell_any_page` 加 `data`:家族「エシュロス」、頁範圍(使用時的翻開頁之後 4 頁)、`expires: next_battle`;`_spell_any_page_standby` 依家族與範圍判斷。P-023:`ScheduleNextSpellBonus` 加 `expires` 參數,P-023 用 `"turn"`(本回合任一場戰鬥,用一次)。
- P-022:戰鬥開始待命表新增 `redirect_damage`:以フリガロ的戰術攻擊、且指定魔物仍在場時,設定 `injure_instead` 與 `injure_target`(不詢問)。S-064:`injure_instead=True`(宣告時選擇)。
- S-104:`on_win`(攻擊成功、造成傷害前)`PeekOpponentOpenPages`,翻開頁沒有戰術卡時 `IncreaseThisSpellDamage(2)`;使用者確認「相手の魔本を見て」在攻擊成功後才生效,不在宣告時。S-103:`on_win` 對對手加本場戰鬥的限制 `no_book_cards`(目前沒有檢查點,登記供未來的翻頁中使用卡片)。S-106:`on_declare`(防禦)`NegateAttack` 後 `TurnOwnPagesOncePerTurn(1)`。
- M-036:`spell_compat` 同 M-023。M-050:`Choose(自己其他魔物)` → `AddPower(+2000, turn)`。P-035:新節點以 `start_phase_mp_gain × 2` 呼叫 `reduce_opponent_mp`。E-028 / E-035:使用條件為 `mp_reduced_by_opponent > 0`。E-034:兩段可略過的 `Choose`(魔書中的ティオ / 大海恵),搭檔裝到場上的ティオ。

### D5:前端與 NPC
- M-037 的範圍內可能有多張可用的戰術:行動欄每一頁各一個「從魔書使用《…》(第 N 頁)」按鈕,直接開該頁的放大檢視;只有一張時維持 P-015 的做法(開魔書網格)。
選項標籤:`extra_cost`(帶追加量與加成)、`reuse_spell`;作用中效果:`after_battle`、`attr_power`、`spell_reuse`、P-033 的旗標。NPC 以既有的中途決策評估處理新決策。

## Risks / Trade-offs

- [宣告時再多一個決策] → 與 M-008 減費同一流程,依序詢問;測試兩者同時出現的情況。
- [S-098 重用的對象在使用時選定] → 選定的那一頁之後不在翻開的頁時就用不到;依效果文「使用の条件は満たさなければならない」,記錄在 card-effects design(使用者確認)。
