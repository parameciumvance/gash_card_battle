## Context

`engine.py:_use_book_card` 已經是「從魔本開啟頁直接使用卡片、不經戰鬥流程」的既有指令,對 `EVENT` 卡有完整實作(回合限制、條件檢查、MP 支付),對 `SPELL` 只留了一句「保留擴充點」就 raise。`openspec/specs/game-engine/spec.md` 的「使用場上與魔本中卡片的效果」需求也早就寫著「非戰鬥術使用後 SHALL 至下回合前不可再用」並有對應 Scenario——資料(`effect_icon`)、引擎擴充點、規格文字三者都已就緒,只是從未被實際串起來。S-026(第一彈)、S-041/S-043/S-048/S-057(Level 2)這 5 張「非バトル」術卡因此被迫借用 `declare_attack` 流程觸發,其中 4 張還誤植 `attack_undefendable = True` 來讓流程「跑得完」。

另外,S-036 的傷害結算用一個專屬旁路函式 `injure_or_discard`,跳過了「庇護」「P-006 待命無效」「M-013/M-015 戰鬥中免疫」三種既有規格已保證的防護機制。S-042/S-045/S-046 三張則完全沒有 handler。

## Goals / Non-Goals

**Goals:**
- 補完 `_use_book_card` 的 SPELL 分支,讓 5 張「非バトル」術卡改走正確通道,移除誤植的 `attack_undefendable`。
- 「非戰鬥術下回合前不可再用」比照 `used_abilities`/`used_event_this_turn` 的既有重置模式(`turn_ended` 時對雙方玩家清空),不另外設計新的跨回合追蹤機制。
- S-036 改走正規 `_start_damage`,刪除 `injure_or_discard`。
- 新增 S-042(魔力門檻加傷害)、S-045/S-046(條件式不可防禦,這裡的 `attack_undefendable` 是正確用法,因為這兩張是真正透過戰鬥流程觸發的一般攻擊術,不是非戰鬥術)。

**Non-Goals:**
- 不處理 `effect_icon_ja` 為「ジャマー」的卡(如 M-026)——這類卡目前用 `timing="any"` 的既有機制(魔物/夥伴卡啟動效果),跟這次「非戰鬥術」是不同的既有機制,行為已經正確,不在此次範圍。
- 不重新設計「對手回合可用的非戰鬥術(`ad=="D"`)」這個分支的完整測試——目前 5 張要遷移的卡 `ad` 全是 `"A"`,`ad=="D"` 分支複用 EVENT 卡已驗證過的邏輯,但沒有一張現有卡會真正走到這個分支,留待未來有對應卡片時再補測試。
- 不處理「效果 icon」為空字串、但效果文字仍隱含某種特殊時機限制的邊界情況(目前掃描過的候選卡都有明確的 `ad`/`effect_icon` 標記可用)。

## Decisions

- **新增獨立的非戰鬥術 handler 註冊表 `reg.SPELL_NONBATTLE`(裝飾器 `reg.spell_nonbattle(number)`),不與 `SPELL_RIDERS.on_declare` 共用**:`on_declare` 的語意是「戰鬥宣告時觸發,side 為 attack/defense」,非戰鬥術完全不進入戰鬥流程,混用同一個 hook 容易在未來重構 `on_declare` 呼叫點時被誤波及。
- **`_use_book_card` 的 SPELL 分支邏輯**(依序檢查,任一不符合即 `IllegalCommand`):
  1. `card.effect_icon == "nonbattle"`,否則沿用現況錯誤訊息(這張術沒有非戰鬥圖示)。
  2. 依 `card.ad` 判斷回合時機:`"A"` 僅能在 `player == turn_player` 使用,`"D"` 僅能在 `player != turn_player` 使用(邏輯與 EVENT 卡一致)。
  3. 除指示術(`card.is_command_spell`,即 `related_mamodo == COMMAND_ALL`)外,MUST 檢查玩家場上存在至少一隻 `usable_by` 該卡的魔物(沿用 `_validate_spell_declaration` 的 `related_mamodo` 匹配或 `SPELL_COMPAT` 判斷邏輯,抽成共用函式)。
  4. `key = f"nonbattle:{number}"`,若已在 `used_nonbattle_spells` 中則拒絕(每回合限 1 次)。
  5. 支付 `spell_cost()` 費用。
  6. 呼叫 `reg.SPELL_NONBATTLE[number]` handler。
- **`used_nonbattle_spells: set[str]` 新增到 `PlayerState`,在 `turn_ended` 時與 `used_abilities`/`used_event_this_turn` 一起對雙方玩家清空**:交替回合制下,這個清空時機天然等價於「下一次輪到自己的回合才解禁」,不需要額外記錄「哪一回合用的」。
- **S-026/S-041/S-043/S-048/S-057 遷移**:各卡原有的效果邏輯本體(擲幣判斷函式、`choose_resolver`、`schedule_standby` 呼叫)不變,只是:
  - 從 `reg.spell_rider(number, on_declare=..., no_book_damage=True)` 改為 `reg.spell_nonbattle(number)` 註冊。
  - handler 簽名從 `(game, batch, player, side)` 改為 `(game, batch, player)`(不再需要 `side` 參數,永遠是非戰鬥觸發)。
  - 刪除 S-041/S-043/S-048/S-057 內的 `b.attack_undefendable = True` 那幾行(`b = game.state.battle` 這個區域整段移除,因為非戰鬥術根本不會有 `game.state.battle`)。
  - `no_book_damage=True` 這個 `SpellRider` 欄位不再需要(非戰鬥術不會進入戰鬥傷害結算),遷移後這幾張卡不再出現在 `SPELL_RIDERS` 裡。
- **S-036**:`_s036_on_win` 改為組 `items = [{"kind": "book", "player": opp, "amount": amount}] + [{"kind": "slot", "player": opp, "slot_uid": s.uid, "amount": 1} for s in opp_slots]`(`amount` 取 `_attack_damage_amount(game, battle)` 的完整計算結果,而非卡片原始 `damage` 欄位,以涵蓋 modifier/上限等既有調整),呼叫 `_start_damage(game, batch, items, ctx)`;`injure_or_discard` 函式整個刪除(改動後確認全專案無其他呼叫點)。
  - **實作階段更正**:原先設計沿用 S-041 系列的 `no_book_damage=True`,但這會讓 `_resolve_showdown` 在 `on_win` 之後誤判「沒有傷害」而提前呼叫 `_finish_battle_damage` 結束戰鬥——此時 `_start_damage` 可能還在等待 `damage_order`/`protect` 選擇,提前結束戰鬥會讓決策懸空、狀態不一致。新增 `SpellRider.on_win_owns_damage` 旗標(僅 S-036 使用),`_resolve_showdown` 呼叫完 `on_win` 後若此旗標為真則直接 `return`,不再往下執行任何預設分支;S-019/S-020(既有的 `on_win`+`no_book_damage` 用法,效果本身完全不涉及傷害系統)行為不受影響,仍用 `no_book_damage=True`。
- **S-042**:`SpellRider` 新增 `damage_bonus: Callable[[Game, BattleState], int] | None = None` 欄位;`_attack_damage_amount` 在算完 `total` 後,若 `rider.damage_bonus` 存在則 `total += rider.damage_bonus(game, battle)`;S-042 註冊 `damage_bonus=lambda game, battle: 2 if battle.data.get("attack_total", 0) >= 8000 else 0`(讀取 `_resolve_showdown` 已經存好的 `battle.data["attack_total"]`)。
- **S-045/S-046**:比照既有 S-019 的模式,`on_declare` 中依擲幣結果直接 `battle.attack_undefendable = True`(S-045 需 2 次都正面,S-046 需 1 次正面)——這裡是正確用法,因為這兩張透過 `declare_attack` 真正進入戰鬥流程,`attack_undefendable` 影響的是後續 `declare_defense` 是否被允許,語意成立。

## Risks / Trade-offs

- **`used_nonbattle_spells` 的清空時機依賴現有 `turn_ended` 邏輯的正確性**:目前 `used_abilities`/`used_event_this_turn` 都在同一處清空且運作正常,新增一個同模式的欄位風險低,但仍須補一個測試驗證「用過後同回合不可用、下回合(輪到自己時)恢復可用」的完整跨回合案例。
- **S-036 改用 `_start_damage` 後,多目標(對手全部魔物 + 魔本)會觸發 `damage_order` 選擇(受方決定處理順序)**:這是正規管線既有行為(`_process_damage` 對多於 1 筆 item 時的既定邏輯),但 S-036 過去沒有這個互動步驟,遷移後前端/測試都需要多處理一種 `pending choice`。
  - **實作階段更正(使用者遊玩後回報)**:多項傷害的 `_process_damage` 迴圈原本只在每次挑出下一項時檢查「是否有庇護者」,沒檢查「這一項自身的目標是否還在場上」。若前面某項傷害被一隻已負傷的魔物 B 頂替庇護、B 因而入墓,B 自己原本那份傷害的目標已經消失,但迴圈仍會把場上其他健康魔物列為「B 那份傷害」的候選庇護者、詢問要不要庇護一個已經不存在的目標。修正:`_process_damage` 迴圈開頭新增一輪過濾,把目標(`slot_uid`)已不在場上的項目直接從 `items` 移除、各自發出 `damage_prevented(reason="no_target")`,再繼續原本的 `damage_order`/`protect` 判斷。已同步補上 `game-engine` spec 的對應 Requirement 文字與 Scenario。
- **刪除 `injure_or_discard` 是不可逆動作**:已確認全專案唯一呼叫點就是 `_s036_on_win`,遷移完成後刪除風險低。
- **`SPELL_COMPAT`/`related_mamodo` 判斷邏輯要從 `_validate_spell_declaration` 抽成共用函式,供 `_use_book_card` 呼叫**:這是本次唯一牽動既有攻擊宣告路徑的重構,MUST 確認抽出共用函式後,原本 `declare_attack`/`declare_defense` 的行為(含既有測試)完全不變。
