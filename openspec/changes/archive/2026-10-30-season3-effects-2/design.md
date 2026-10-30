## Context

範圍與動機見 proposal.md。以下只記錄需要擴充引擎的地方,以及效果文沒有寫清楚、需要解讀的部分。

既有機制的對應:

| 卡 | 沿用 |
|---|---|
| E-047 | `LockChosenOpponentMamodo`,旗標只封鎖戰術(同 P-033 的作法,P-033 只封鎖戰術攻擊) |
| Ex-015 | `spell_rider` 的獲勝結算 + `RestrictOpponent(NO_EFFECTS_AND_SPELLS, DUR_UNTIL_END_NEXT_TURN)` |
| Ex-044 | `spell_nonbattle` + 逐隻 `Coin` + `LockChosenOpponentMamodo`(時效到下一回合結束階段) |
| PR-005 的限制 | `RestrictBothPlayers(NO_EFFECTS_AND_SPELLS, DUR_TURN)` |
| M-057 | `activated(timing="battle")` + `Coin` + `NegateAttack`(同 M-043,條件改為「對手攻擊的戰鬥」) |
| P-040 | 同 P-009 的 `NegateOpponentSpell` |
| PR-008 | `activated(mode="mp")` + `Coin` + `HealSlot`,條件 `has_own_injured_mamodo` |
| M-066 | `partner_discard_guard`(同 M-049) |
| Ex-024 | `event(when=...)` + 選對手魔物 + 一般傷害管線(可保護) |
| M-054 | `Coin` + `MakeNextAttackUndefendable`,加上「限這隻魔物的戰術」 |
| M-059 / M-061 | `activated(mode="discard")`(魔物卡棄掉自己,同 M-033) |
| Ex-021 / M-061 的結束階段 | 結束階段待命,加入 `end_phase_order` 的定序清單(同 E-042) |
| P-038 的棄掉 | `action_discard`(同 P-020) |

## Goals / Non-Goals

**Goals:**
- 22 張全部依效果文實作並開放,每張非香草卡至少一個依效果文寫的行為測試。
- 新增的機制一般化,供第 4、5 批使用(攻擊時的待命決策、戰術屬性紀錄、MP 設為定值)。

**Non-Goals:**
- 第 4 批以後的卡;M-065 / Ex-025 對「MPをへらす / ふやす」效果的回應(第 5 批),這批只把 Ex-048 的分類記錄好。
- 改變既有卡的行為。

## Decisions

### D1 強制保護(Ex-047)

- 新增 modifier 種類 `forced_protector`(owner = 使用者,target_player = 對手,target_slot = 選定的魔物,`DUR_TURN`)。
- `_protect_choice`:受方有生效中的 `forced_protector`,且該魔物在 `_eligible_protectors` 的結果中(依既有的限制判斷)時,不建立保護決策,直接以它保護並發出事件(`protect_forced`)。不在候選中時照一般流程。
- 不建立只有一個選項的決策:「可能な限り」沒有選擇的餘地,詢問只會多一步。
- P-027 的對手魔物是 `_eligible_protectors` 的額外候選,強制保護時直接被略過(FAQ Q2)。
- 防禦不受影響(FAQ Q1):只改保護流程,不碰防禦宣告。

### D2 戰術屬性紀錄(Ex-043)

- `PlayerState.spell_attrs_by_turn: dict[int, set[str]]`:宣告戰術(攻擊、防禦、非戰鬥)時記錄 `attr_name`;只保留本回合與前一回合(同 `opp_mp_reduced_turns`)。
- 以宣告為準,之後被無效也算「使った」。
- Ex-043 在宣告時(`on_declare`)查對手 `turn_no - 1` 的紀錄,成立時加上這個戰術的魔力 +4000 與傷害 +2(同 S-108 的宣告時加成)。

### D3 戰鬥階段一開始(PR-005)

- `GameState.battle_phase_acted: bool`:進入戰鬥階段時設為 False;戰鬥階段中任一方成功執行行動類指令(使用卡片或效果、宣告戰鬥、放卡到場上、以行動棄卡)時設為 True。單純的 pass 不算行動。
- PR-005 的使用條件:自己的回合、戰鬥階段、`battle_phase_acted` 為 False。事件卡 `ad == "A"` 已限制在自己的回合。
- 「すきな順で」:三個效果由使用者選順序(使用者 2026-10-30:效果文寫了「すきな順」就提供選擇)。以 `Choose(EffectOptions)` 先選第一個、再選第二個,剩下的自動使用;沿用 E-021 的效果選擇決策種類 `pick_effect`。
- 沒有負傷魔物時省略回復的選項(使用者 2026-10-30),只在 MP +2 與限制之間選第一個,另一個自動使用。

### D4 MP 設為定值(Ex-048)

- 新節點 `SetBothMp(value=4)`:依玩家 0、1 逐一處理。
  - MP > 4:減少。對手的部分走 `ReduceOpponentMp` 的保護與紀錄(`mp_guarded` / P-020、`mark_opp_mp_reduced`、`mp_reduced_by_opponent`);自己的部分是自己效果造成的減少,沒有保護。
  - MP < 4:增加。自己的部分走 `gain_mp` 的 P-020 判斷;對手的部分是使用者的效果使對手增加,P-020(「自分の効果で」)不適用。
- 「増減都算」(使用者 2026-10-30):增加的一方記為「MPをふやす」效果、減少的一方記為「MPをへらす」效果,事件附 `reason=Ex-048`;第 5 批的回應效果依此判斷。

### D5 攻擊時的待命與決策(M-054 / M-055 / P-042 / P-043)

- `BATTLE_START_STANDBYS` 的條件改用攻擊資訊判斷:`AttackStart` 已有 `is_spell` 與 `mamodo_name`,另加 `attack_slot`(攻擊的魔物 UID)。
  - M-054:`attack_undefendable` 待命加 `slot_uid`,條件為以戰術攻擊且攻擊的魔物是該 UID。
  - P-042:新待命 `battle_lock`,條件為攻擊魔物的家族是「ダニー」(戰術或魔物效果攻擊皆可),套用時加本場戰鬥的限制:對手不能使用搭檔效果與事件卡(`DUR_BATTLE`)。
- 需要在攻擊時做決策的待命(M-055 / P-043):新待命種類 `on_attack`,攜帶一棵效果樹與條件;戰鬥開始、套用完上表後,依序執行符合條件的 `on_attack` 效果樹(可建立決策),全部完成後才進入對手的防禦宣告。
  - 不在 `BATTLE_START_STANDBYS` 用 lambda 寫決策:套用表是同步的,不能暫停等玩家選擇;效果樹已經有暫停與續行。
  - M-055:條件為以戰術攻擊、攻擊的魔物是 M-055 的 UID、戰術效果文含「相手の魔本にダメージ」(`effect_ja` 判斷,由登記時計算的集合提供)、對手場上有魔物。效果:可選(`skip`)→ `Coin` → 正面:選對手魔物,設定 `injure_instead` 與目標(同 P-022 的 `redirect_damage` 套用);反面:`NegateAttack`。
  - P-043:使用時選定對手魔物並存在待命;攻擊時由使用者選兩個效果之一,加本場戰鬥的限制:`NO_DEFENSE_SPELL_OF` 或 `PROTECT_FORBIDDEN_FOR`(target_slot 為選定的魔物)。選定的魔物已離場時不詢問。
- 依既有決定,下一場戰鬥不符合時,這些待命在該戰鬥結束時移除(`next_battle` → `battle`)。

### D6 新的限制旗標

- `NO_EVENTS`:不能使用事件卡。P-038 是常駐效果(`reg` 新增 `opponent_event_lock_in_battle_phase`,在 `use_event` 檢查:持有者的戰鬥階段、持有者沒有受「パートナーの効果を使えない」);P-042 是本場戰鬥的限制。
- `NO_DEFENSE_SPELL_SLOT`:不能以 target_slot 的魔物使用防禦戰術(P-043)。屬於「術を使えない」。
- `NO_PROTECT_SLOT`:target_slot 的魔物不能保護(P-043)。屬於「かばうことができない」。
- `NO_NAMED_SPELLS`:不能使用指定家族的戰術(PR-009,`data.mamodo`)。屬於「術を使えない」。
- E-047:`LockChosenOpponentMamodo(flag=NO_SPELLS)` 的魔物限定版(只封鎖該魔物的戰術)。
- 分類表(`card-effects/design.md`)與 P-034 / E-036 的移除範圍一併更新;`NO_EVENTS` 不屬於可移除的分類。

### D7 不屬於傷害的負傷(M-059)

- 新節點 `InjureChosenOpponentMamodo`:直接設定 `injured = True` 並發出 `mamodo_injured` 事件(`reason="effect"`),不經傷害管線,所以不詢問保護、不檢查不受傷害。
- 候選只有健康的魔物(`OpponentMamodo(healthy=True)`);沒有時不能使用(`ability.condition`)。

### D8 戰術攻擊的傷害 -1(Ex-031)

- 沿用 `AdjustDefenseDamage(amount=-1)`(S-027 的作法):調整本場戰鬥防禦方承受的傷害。
- 使用條件:戰鬥中、對手是攻擊方、以戰術攻擊(`OwnAttackBy` 的對手版)。魔物效果攻擊時不能使用。

### D9 不受傷害的對象(PR-009)

- 新 modifier `named_immune`(owner = 使用者,`data.mamodo="ガッシュ・ベル"`、`data.book=True`,時效到使用者下一個自己回合的結束階段,同 S-075 的時效)。`_apply_damage_item` 在 `full_immune` 之後檢查:魔書傷害且 `book`,或魔物傷害且 `primitives.mamodo_name(slot)` 相符。
- 限制部分另外以 `NO_NAMED_SPELLS` 加上;P-034 / E-036 只移除限制,不移除不受傷害的部分(分開的兩個 modifier)。這是解讀(使用者 2026-10-30 同意):規格「被移除的效果整個移除」指的是複合的封鎖,不受傷害不是限制。

### D10 結束階段棄掉卡片(Ex-021 / M-061)

- 新待命種類 `end_discard_slot`(Ex-021,`slot_uid`)與 `end_discard_partners`(M-061),結束階段時加入 `end_phase_order` 的清單,由回合玩家定序。
- M-061 棄搭檔時依 `partner_discard_guard` 判斷:以對手的效果棄掉時跳過受保護的搭檔(既有的 `_partner_guarded`)。
- Ex-021 的魔物已離場時,待命在解決時沒有效果(以 UID 查不到)。

### D11 解讀一覽

| 卡 | 解讀 | 狀態 |
|---|---|---|
| Ex-047 | 強制保護優先於 P-027;不妨礙防禦 | Confirmed(atwiki FAQ) |
| Ex-024 | 可保護 | Confirmed(atwiki FAQ) |
| P-042 / P-043 | 「『ダニー』の術や『魔物の効果』」= 該家族魔物的戰術與魔物效果攻擊 | Confirmed(使用者 2026-10-30) |
| P-043 | 兩個效果在攻擊時(防禦宣告前)由使用者選 | Confirmed(使用者 2026-10-30) |
| M-055 | 對手沒有魔物時不詢問;攻擊方選要傷害的魔物 | Confirmed(使用者 2026-10-30) |
| Ex-048 | 增加與減少分別算「ふやす」「へらす」效果 | Confirmed(使用者 2026-10-30) |
| PR-005 | 戰鬥階段沒有任何行動時才能用;使用者選順序 | Confirmed(使用者 2026-10-30) |
| PR-005 | 沒有負傷魔物時省略回復的選項 | Confirmed(使用者 2026-10-30) |
| Ex-043 | 「使った」以宣告為準,被無效也算 | Confirmed(使用者 2026-10-30 同意推定) |
| Ex-015 | 攻擊獲勝時才解決(防方獲勝時攻方效果不解決) | Confirmed(推定經使用者 2026-10-30 同意) |
| M-057 / Ex-031 | 在對手攻擊的戰鬥中使用,不要求這隻魔物在戰鬥中(同 M-043) | Confirmed(推定經使用者 2026-10-30 同意) |
| PR-008 | 沒有負傷魔物時不能使用 | Confirmed(推定經使用者 2026-10-30 同意) |
| PR-009 | P-034 / E-036 只移除限制,不受傷害的部分保留 | Confirmed(推定經使用者 2026-10-30 同意) |
| Ex-044 | 依場上順序逐隻擲幣,不讓玩家選順序(結果不受順序影響) | Confirmed(推定經使用者 2026-10-30 同意) |
| M-061 | 使用者自己受 M-049 / M-066 保護的搭檔照常棄掉(「相手の効果」才擋) | Confirmed(推定經使用者 2026-10-30 同意) |

## Risks / Trade-offs

- [戰鬥開始多了一段可暫停的待命決策] → 只在有 `on_attack` 待命時進入;攻擊宣告時的戰術決策(S-058 / S-070)先完成,再執行待命,順序固定並寫測試。
- [`battle_phase_acted` 漏記某種行動,使 PR-005 可在行動後使用] → 在指令分派的共同出口設定(行動類指令成功執行後),不在各指令分別設定;測試涵蓋事件卡、戰術、場上效果、放卡。
- [強制保護自動發生,玩家可能不明白為什麼沒有被詢問] → 發出 `protect_forced` 事件,記錄文字寫明來源卡。

## Migration Plan

無資料遷移。`PlayerState` / `GameState` 的新欄位都有預設值;遊戲狀態只存在記憶體,沒有存檔格式要相容。
