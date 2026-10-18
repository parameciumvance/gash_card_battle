## Context

延續第 1〜3 批與 `declare-time-resolution` 建立的機制:限制分類與 `mamodo_effect_block`、`reg.JAMMER` + 快照還原(M-026)、擲幣確認鏈(M-012 / M-019)、`reg.STACK_ON` / `SPELL_ONLY_STACK` / `DETACH_KEEP_UNDER`(M-027 / S-048)、`reg.MAMODO_ATTACK`(M-027 無戰術攻擊)、`mp_guard`(P-021)、`spell_any_page` 待命(P-015 / M-037)、`power_zero`(P-011)。家族判定目前散在各處的 `game.db[slot.top].related_mamodo`。

效果文解讀於 2026-10-18 explore 中與使用者確認(見下方 D10)。

## Goals / Non-Goals

**Goals:** 23 張依效果文;把「魔力設為某值」、ジャマー的觸發動作、疊放的前身與離場方式、1 行動效果做成可沿用的形式。

**Non-Goals:** 第 5 批(S-088〜S-090、E-029 / E-037 / E-039 / E-041 / E-042);其他彈「視為○○」的卡只做 M-047 需要的範圍。

## Decisions

### D1:魔力設為某值(M-035、P-011)
`power_zero` 改為通用的 `power_set` 修正(`data` 帶 `value`(固定值)或 `copy_slot`(對象的 player、uid)),依 `st.modifiers` 中的建立順序取**最後一個**仍有效者。`power_breakdown` 有設定時:計算 X 後輸出一項 `{"kind": "power_set", "source", "amount": X - raw}`,其餘加減項照列但加總後被抵銷——明細加總仍等於 X。`copy_slot` 以遞迴呼叫 `power_breakdown` 取對象當下的魔力,帶「已走過的 slot」集合;繞回時改用那隻不計設定的 raw 值。對象離場時跳過這個設定(取下一個較早的設定或不設定)。
- 不採「P-011 永遠優先」:使用者確認兩者同為「變為 X」,後發者勝出。
- 不採 M-035 使用時快照:使用者確認要跟著對象變動。

### D2:家族名稱判定
新增 `family(game, slot)`(`effects/primitives.py` 或 `engine.py`):回傳 `reg.TREATED_AS.get(slot.top) or game.db[slot.top].related_mamodo`;M-047 登記 `treated_as("M-047", "ガッシュ・ベル")`。所有以 `related_mamodo` 判斷「這隻魔物是誰」的地方(戰術使用者、搭檔對應、P-001 家族攻擊、同名限制、條件節點)改用 `family`。同名限制 `same_name_copies`:M-047 當作名為「ガッシュ・ベル」的魔物計數。

### D3:疊放的擴充
- `reg.stack_on` 的 `base` 接受 `family="ガッシュ・ベル"`(以 D2 的 `family` 比對最上層)。
- 離場方式拆成兩種:`DETACH_KEEP_UNDER`(任何離場都只分離上層,M-027)與新的 `_detach_top(game, batch, player, slot, reason)`(只在指定時機分離上層,M-046 的 1 行動、M-047 的定時離場)。`_detach_top` 從現有 `_discard_slot` 的分離分支抽出。
- M-047:`reg.on_play` 的節點 `ScheduleDetachSelf` 建立 `scheduled_detach` 修正(`target_slot`、`data.turn` = 放出後下一個「自己的回合」的回合號:自己的回合放出 → `turn_no + 2`,對手的回合 → `turn_no + 1`;時效 `until_detach`)。`_end_phase` 一開始(魔物消失處理與強制翻頁之前)處理到期的 `scheduled_detach`,只要 slot 頂層仍是該卡就以 `_detach_top` 離場(不經「不會被棄掉」的檢查)。
- M-047 的不受傷害:`ImmuneWhileEffective`(「魔物の効果を使えない」時不生效,見 D11)。

### D4:1 行動效果
新增非戰鬥指令 `use_action_effect`(`zone`: `mamodo` / `partner`、`slot_uid`),登記表 `reg.ACTION_DISCARD`(`"M-046": "top"`、`"P-020": "partner"`)。驗證:戰鬥階段、非戰鬥中、持有者有行動權、卡仍在場上。執行後與其他行動一樣交出行動權。這不是「魔物 / 搭檔的效果」的啟動,因此不受「不能使用效果」限制,也不觸發ジャマー。

### D5:ジャマー的觸發動作
`reg.jammer(number, mp_cost=0, discard_self=False, on="mamodo_effect" | "event")`。`_jammer_holder(game, player, on)` 依動作種類過濾。事件卡使用入口(`_use_event`)與魔物效果相同:先存快照(費用已付、`used_event` 已記)→ 解決 → `_queue_jammer`。M-032 的使用:費用改為 `discard_self` 時把 M-032 那個 slot 以 `_discard_slot(reason="effect_cost")` 處理(在還原之後執行,避免被還原回場上)。連鎖:被無效的一方的ジャマー依原本動作種類判斷——無效化本身是「魔物的效果」,所以對手可用 M-026 回應 M-032;M-032 只回應事件卡。

### D6:M-034 改正面
`reg.coin_set_heads("M-034")`。`_coin_confirm_chain` 為擲幣者準備確認選項時,除了 M-012 的 `reflip` 外,也加入 `{"value": "heads:i", "label": "set_heads", "coin": i}`(僅反面的硬幣;欄位不用 `index`,因為 NPC 與逾時代打以 `index` 當選項值);只要有 M-012 或 M-034 可用就停下詢問。選擇後棄掉 M-034 的 slot,`results[i] = True`,發出 `coin_set` 事件,之後回到確認鏈繼續(可能再詢問 M-012 / 另一張 M-034)。

### D7:MP 保護(P-020)
- `mp_guarded(game, player)` 加入:`phase == BATTLE` 且持有者場上有 P-020(搭檔效果未被封鎖)。
- `gain_mp` 加參數 `by`(效果擁有者;預設 `None` 表示非效果,例如規則的翻頁)。`by == player`、戰鬥階段、場上有 P-020 時不增加,發出 `mp_gain_prevented`。效果造成的 MP 增加都改為傳 `by`;開始階段翻頁與結束階段強制翻頁不經 `gain_mp` 或傳 `None`。

### D8:魔物效果防禦與固定合計魔力
- `reg.mamodo_defense("M-039", mp_cost=1, power=6500)`,M-039 同時登記 `mamodo_attack(mp_cost=1, power=6500, damage=1)`。`declare_defense` 支援 `slot_uid` 而不帶 `page` 的入口,依 `MAMODO_DEFENSE` 驗證費用與魔物效果限制,合計魔力為固定值(與 M-027 無戰術攻擊的 `fixed_power` 處理相同)。
- S-087:`SpellRider.fixed_total = {"attack": 8000, "defense": 11000}`,合計魔力計算時以固定值取代(明細一項 `fixed_total`)。

### D9:各卡
- M-045:`activated(mode="mp", mp_cost=1, timing="nonbattle", own_turn=True)`,`PeekOpponentOpenPages` → `Choose(OpponentOpenPageCards(card_type="partner"), prompt="pick_opponent_book_card")` → `DiscardFromOpponentBook`;「あれば…選んで、捨て札にする」不是「できる」,有搭檔卡就必須選;沒有時只檢視。
- M-048:待命 `attack_undefendable`(`expires: next_battle`)加 `data.slot_uid` 與 `min_total=10000`;攻擊宣告時(合計魔力於宣告時確定)符合才生效。
- M-049:`reg.partner_discard_guard("M-049")`;對手效果棄搭檔的節點(`DiscardChosenPartner`、`DiscardOtherPartners`、M-022 等)過濾選項與執行時檢查,只看「由對手效果」造成;`_discard_slot` 整疊離場不受影響。
- P-025:`ScheduleSpellFromAnyPage(spell="ジオルク")`;非戰鬥戰術的使用入口(`_use_book_card` 的非戰鬥分支)也檢查 `_spell_any_page_standby` 並消耗。
- P-031:常駐檢查(不是限制修正,因此 E-036 / P-034 移除不了):`mamodo_effect_block` 加「對手場上有 P-031 且這隻是ウマゴン(D2 的 `family`)」;事件卡使用驗證加「對手場上有 P-031 且卡名為『ウマゴン』」(`event.restricted`)。作用中效果以 `type: "static"` 列出。
- P-032:`RestrictOpponent(NO_PARTNER_EFFECTS, DUR_NEXT_TURN)`(既有時效,E-001 的「僅下一回合中」)。「パートナーカードを使えない」不屬於 E-036 / P-034 的分類(「術を使えない」「かばうことができない」「魔物の効果を使えない」),所以移除不了(見 D10 第 6 點的更正)。
- S-060:`Coin` 宣告時,正面 → `CANNOT_PROTECT`(同 S-081)。S-092:同 S-017。S-086:同 S-048(`StackFromBookOnto(base family ウマゴン)`、條件 `HasOptions(OwnBookCopiesOf("M-046"))` 且場上有ウマゴン)。
- S-093:非戰鬥 `Coin`,正面 → 減少對手 MP 3(`reduce_opponent_mp`,受 P-021 / P-020 保護)。
- S-094:非戰鬥 `Coin`,正面 → 新節點 `DamageOpponentBookOutsideBattle`:以 `_start_damage` 新的 `cause="effect"` 對對手魔書造成此戰術的傷害(含 M-033 等自己戰術傷害加成),走一般的保護流程。目前沒有戰鬥外的魔書傷害,這是新路徑;保護決策的傷害資訊(`_damage_info`)要支援沒有戰鬥的情況。
- S-095:防禦 `on_declare` 擲幣(宣告時確定),正面記在 `battle.data`;魔力勝負結算時(不論勝敗,防禦沒被無效)加本回合的 `no_damage` 修正給自己場上所有キャンチョメ(D2 的 `family`)。
- S-072:`spell_nonbattle`,`HealSlot` 對自己的ダニー;沒有負傷的ダニー仍可使用(比照 E-040,沒有使用條件)。

### D10:解讀(Confirmed,使用者 2026-10-18)
1. M-047「場に出した、次の自分のターンのエンドフェイズ」:自己回合放出 → 下一個自己回合;對手回合放出 → 接下來的自己回合。
2. M-035:隨時跟著選定魔物的當下魔力;「魔力設為 X」覆蓋所有加減;與 P-011 後發者勝出(改變 P-011 原本「優先於一切加成」的行為)。
3. P-032「パートナーカードを使えない」:只禁搭檔的效果,仍可放到場上。
4. 1 行動棄卡(M-046 / P-020)不算「使用效果」:不受「不能使用效果」限制、不觸發ジャマー。
5. M-032 的無效化本身是魔物的效果,對手可用 M-026 回應;M-032 只回應事件卡。
6. P-031 是常駐效果(不能移除)。P-032 原先寫「是限制,可被 E-036 / P-034 移除」;實作時對照效果文,E-036 只移除「術を使えない」「かばうことができない」「魔物の効果を使えない」,P-034 只移除「術を使えなくなる効果」,都不含「パートナーカードを使えない」,所以 P-032 移除不了(已告知使用者)。
7. S-094 新增戰鬥外的魔書傷害路徑,可保護。
8. M-034 用掉後場上沒有魔物時,依規則在結束階段處理。
9. 其餘(M-032 / M-034 / M-039 / M-045 / M-046 / M-048 / M-049 / P-020 / P-025 / P-031 / S-072 / S-086 / S-087 / S-093〜S-095)依 explore 的建議採納,見 card-effects delta。

### D11:「このカードが場にある→」的常駐效果與「使えない」(Confirmed,使用者 2026-10-18)
出處:官方規則書(https://ul.h3z.jp/7UgUhNx9.pdf)第 42 頁「『無効にする』と『使えない』」:「『このカードが場にある→』効果を使えなくすることができます」「『このカードが場にある→』効果は無効にできません」;「使えない」是事先使用、不能無效已使用的效果。使用者確認以此為準,寫入 game-engine「『無効にする』與『使えない』」。本批的常駐效果都在對應的禁止下失效:M-047《輝く体》與 M-049 受「魔物の効果を使えない」,P-020 與 P-031 受「パートナーの効果を使えない」。既有的常駐效果(M-003 / M-004 / M-023 / M-031 / M-036 / M-040 / M-051 / M-053 / P-013 / P-019 / P-024 / P-030 等)尚未逐張檢查,另開 change 處理(todo.md)。

## Risks / Trade-offs

- [家族判定改用 `family` 影響面廣] → 先 grep 所有 `related_mamodo` 呼叫點逐一替換;全測試回歸。
- [`power_set` 改變 P-011 明細與行為] → 既有 P-011 測試改寫成「後發者勝出」的兩個方向;golden 與 showdown 明細測試更新。
- [ジャマー快照涵蓋事件卡] → 事件卡可能開始 / 結束戰鬥時沿用 `_queue_jammer` 的保護(不提供無效化)。
- [M-034 在確認鏈內棄掉魔物] → 棄掉後若場上沒有魔物,依規則在結束階段處理,不在確認鏈中處理。
- [P-020 的 `gain_mp(by=)` 需要改所有呼叫點] → 未傳 `by` 的呼叫一律視為非效果;測試覆蓋 E-032 / M-044 / P-030 三種增加來源。
