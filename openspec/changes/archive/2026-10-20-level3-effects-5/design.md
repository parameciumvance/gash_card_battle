## Context

延續第 1〜4 批的機制:待命 `next_battle`(戰鬥開始時綁到這場戰鬥、結束時移除)、宣告時的中途決策(`_ask_injure_target`、`battle.data`)、`spell_cost_zero` 與 `_base_spell_cost_by`(P-005「本来のコスト」)、`PlayablePartnerInDiscard` / `AttachPartnerFromDiscard`(E-011)、`own_page_turn_effect`(P-010「合計1回」)、`SwapBookPages`(M-016)、`RevealOpponentBook` / `AwaitBookReviewEnd`(M-011)、結束階段的 `_scheduled_detach`(M-047)。事件卡上限目前是 `PlayerState.used_event_this_turn` 布林值。

game-engine「結束階段」需求本來就寫「解決結束階段效果與待命(多項由回合玩家定序)」,但引擎還沒實作定序;這批第一次出現同一結束階段可能有多個效果的情況。

## Goals / Non-Goals

**Goals:** 8 張依效果文;結束階段效果的定序做成之後可沿用的流程。

**Non-Goals:** E-038(結束階段 MP +4)的時機修正(目前在強制翻頁之後,依規則應在之前),另記 todo;既有常駐效果的「使えない」檢查(todo)。

## Decisions

### D1:下一場戰鬥的待命(S-088 / S-089)
- S-088:`Coin(count=2, on=HeadsAtLeast(2))` → 待命 `spell_base_cost_zero`(`expires: next_battle`)。`_base_spell_cost_by` 在擁有者有這個待命時把本来のコスト設為 0(在 P-005 / 最後一頁之後套用,減費與追加費用照常計算)。宣告時驗證費用就看得到待命;戰鬥開始時待命綁到這場戰鬥(`battle`),結束時移除,不消耗,所以這場戰鬥中的每次宣告都適用。只限戰術(無戰術攻擊本來就是固定 MP,不是「術」)。
- S-089:`Coin` → 待命 `attack_power_from_mamodo`(`expires: next_battle`)。攻擊宣告時(`_start_battle`,在 `_ask_injure_target` 之後、`on_declare` 之前)若有這個待命且自己有攻擊魔物以外的魔物,由攻擊方選擇(`pick_own_mamodo`,只有 1 隻時自動),存 `battle.data["attack_power_from"] = {"slot", "source"}`;`side_breakdown` 攻擊方加一項 `mamodo_bonus`(來源 S-089,數值為那隻魔物當下的 `slot_power`,已離場為 0 不列)。無戰術攻擊同樣適用。決策種類為引擎的 `attack_power_from`(不用效果樹的 `pick_own_mamodo`,因為這是戰鬥宣告流程中的決策)。以 S-087 攻擊時合計魔力固定 8000,不加 S-089(S-087「合計魔力は8000になる」)。
- 兩張比照 S-026:擲出正面就生效,不提供「是否使用」(AGENTS 規定的 S-026 類情況,使用者 2026-10-20 確認)。

### D2:S-090 暫時放出搭檔
`spell_nonbattle("S-090", when=HasOptions(PlayablePartnerInDiscard()))`:`Coin` → `Choose(PlayablePartnerInDiscard)` → 放出(沿用 `AttachPartnerFromDiscard`)→ 持續效果 `discard_partner_at_turn_end`(`target_slot`、`data["card"]`,時效 `turn`)。結束階段的時效到期處理前(強制翻頁之後、換回合之前),若那隻魔物的搭檔仍是那張卡就棄掉(`card_discarded` reason `turn_end`)。

### D3:事件卡上限(E-029)
`PlayerState.events_used_this_turn: int` 取代 `used_event_this_turn`(views / NPC 等讀取處一併改;回合結束歸零)。上限 = 1,本回合有自己的 `event_limit` 持續效果時取其 `amount`(E-029:3)。E-029 本身受原本的上限檢查,所以只能是本回合第一張。

### D4:E-037 互換對手魔書
`RevealOpponentBook` → `When(兩側都選得到)`:`Choose(OpponentBookPagesAfterOpen)` → `Choose(OpponentBookPagesBeforeOpen)` → `SwapOpponentBookPages`;否則 `AwaitBookReviewEnd`。「之後」= 頁碼大於目前翻開的第二頁、未離開魔書、不是最後一頁;「之前」= 頁碼小於目前翻開的第一頁、未離開魔書。決策種類沿用 `pick_opponent_book_card`。

### D5:E-039
`own_page_turn_effect(1)`(P-010 的「合計1回」:自己算 1 次,之後的翻自己魔書效果不發生)→ 有翻頁才 `GainMp(3)` → 限制 `no_attack`(本回合)。`no_attack` 不放進 `RESTRICTION_CATEGORIES`,所以 E-036 / P-034 移除不了;`_declare_attack` 對戰術與無戰術攻擊都檢查(`attack.restricted`)。

### D6:E-041 的傷害紀錄
`PlayerState.dealt_damage_this_turn: bool`,在 `_apply_damage_item` 實際造成傷害時(魔書前進、魔物負傷或入墓;保護者承受的也算)設定給 `ctx["source_player"]`,只在受方是對手時;被免疫、`no_damage`、`full_immune`、`negate_damage` 擋下的不算。回合結束歸零。E-041 使用條件查它;效果為待命 `end_phase_turn_opponent`(翻對手 1 頁,`turn_pages`)。

### D7:E-042
`Choose(OwnMamodo, bind="keep", prompt="pick_mamodo_to_keep")` → `AsOpponent(Choose(OwnMamodo, bind="keep_opponent", ...))` → `ScheduleEndPhaseDiscard`:使用時計算雙方被選定的魔物(各自留下的以外),存成待命 `end_phase_discard`(`data["slots"]`:[(玩家, uid)])。只有 0 或 1 隻時不詢問(1 隻自動留下)。新決策種類 `pick_mamodo_to_keep`(補 `choice.title`)。

### D8:結束階段效果的定序
`_end_phase` 一開始收集本回合結束階段要解決的效果:到期的 `scheduled_detach`(M-047)、`end_phase_turn_opponent`(E-041)、`end_phase_discard`(E-042)。2 個以上時建立決策 `end_phase_order`(回合玩家;選項 `{"value": i, "label": "end_phase_effect", "card": 來源, "kind": 種類}`),選一個解決後再問剩下的;只剩 1 個時直接解決。全部解決後才進入既有流程(魔物消失處理 → 強制翻頁 → E-038 → S-090 的搭檔 → 時效到期)。翻頁可能讓對手輸掉,遊戲結束時停止。E-038 維持現狀(todo)。

### D9:解讀(Confirmed,使用者 2026-10-20)
1. S-088 / S-089 / S-090 擲出正面就生效,不詢問是否使用;S-088 的費用 0 自動套用。
2. S-089 宣告時選對象,魔力勝負時取對象當下的魔力。
3. 結束階段多個效果由回合玩家選擇順序。
4. E-029 含自己 3 張;E-037 找不到可互換的一對時仍可使用;E-039 不能攻擊含無戰術攻擊、不能移除,沒翻頁就不加 MP;E-041 的「造成過傷害」定義如 D6;E-042 使用時選定、結束階段在魔物消失處理前棄掉;S-090 需要可放出的搭檔、回合結束時棄掉;S-088 只限戰術。

## Risks / Trade-offs

- [`used_event_this_turn` 改名影響快照與前端] → 搜尋所有讀取處一併改,前端以快照的剩餘可用數判斷。
- [結束階段改成可中斷] → 沿用 `_continue_end_phase(stage)` 的中斷續行方式;決策 resolver 解決後回到收集剩餘效果。
- [S-089 宣告時再多一個決策] → 與 `_ask_injure_target` 依序詢問,測試兩者同時出現。
