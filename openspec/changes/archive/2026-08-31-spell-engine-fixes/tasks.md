## 1. 非戰鬥術使用機制

- [x] 1.1 `PlayerState` 新增 `used_nonbattle_spells: set[str]`,`turn_ended` 時與 `used_abilities`/`used_event_this_turn` 一起清空。
      **驗收條件**:新增測試——玩家於自己回合用完某張非戰鬥術後同回合再次使用被拒;結束回合、經過對手一輪、輪到自己時可再次使用。
      實際結果:`test_used_nonbattle_spell_blocks_same_turn_reuse` 涵蓋兩段情境。
- [x] 1.2 `registry.py` 新增 `reg.SPELL_NONBATTLE` 註冊表與 `reg.spell_nonbattle(number)` 裝飾器,handler 簽名 `(game, batch, player)`。
      **驗收條件**:任一張遷移後的卡(如 S-041)可透過 `reg.SPELL_NONBATTLE["S-041"]` 取得 handler。
- [x] 1.3 把 `_validate_spell_declaration` 裡判斷「玩家場上是否存在對應魔物」的邏輯(`related_mamodo` 匹配或 `SPELL_COMPAT`)抽成共用函式。
      **驗收條件**:抽出後,既有 `declare_attack`/`declare_defense` 相關測試全數維持通過,行為不變。
      實際結果:抽出 `_spell_usable_by(game, player, slot, card)`,既有測試無異動全數通過。
- [x] 1.4 補完 `_use_book_card` 的 `elif card.type == SPELL:` 分支:依序檢查 `effect_icon=="nonbattle"`、`ad` 回合時機、對應魔物在場(指示術除外)、`used_nonbattle_spells`、MP 支付,呼叫 `reg.SPELL_NONBATTLE` handler。
      **驗收條件**:對每一種拒絕情境各寫一個測試(非非戰鬥術嘗試走此指令被拒、回合時機錯誤被拒、無對應魔物被拒、同回合重複使用被拒、MP 不足被拒);合法情境下效果正確觸發。
      實際結果:另外發現 `CardDef.can_attack()`/`can_defend()` 沒有排除 `effect_icon=="nonbattle"`,遷移後這 5 張卡仍可被 `declare_attack` 宣告——已一併修正這兩個方法,並以「暫時還原修正→確認測試失敗→改回」的方式驗證新測試真的會抓到迴歸。

## 2. 遷移 S-026/S-041/S-043/S-048/S-057

- [x] 2.1 S-026:改註冊到 `reg.spell_nonbattle`,handler 簽名調整,原有擲幣+`schedule_standby` 邏輯不變。
      **驗收條件**:既有涵蓋 S-026 的測試(若有)改為透過 `use_book_card` 觸發後仍通過;若原本測試是透過 `declare_attack` 觸發,一併更新觸發方式。
      實際結果:`test_s026_set_then_undefendable` 改用 `use_book_card` 觸發,新增 `test_s026_cannot_declare_attack`。
- [x] 2.2 S-041/S-043/S-048/S-057:改註冊到 `reg.spell_nonbattle`,刪除各自的 `b.attack_undefendable = True` 與相關 `game.state.battle` 判斷區塊。
      **驗收條件**:全文搜尋這 4 張卡的 handler 內容不再出現 `game.state.battle`;每張至少 1 個測試透過 `use_book_card` 觸發並驗證效果正確生效(S-041 擲幣正→自身免疫、S-043 羅布諾斯轉換、S-048 疊裝甲、S-057 擲幣正→設置 injure_instead 待命)。
      實際結果:新增 `test_s041_self_immune`、`test_s043_fuse_two_doubles_into_complete`、`test_s057_sets_injure_instead_standby`;S-048 沿用既有 `test_mamodo_attack_full_battle`/`test_mamodo_attack_deals_book_damage`(改為透過 `use_book_card` 觸發)。
- [x] 2.3 確認遷移後 `declare_attack` 對這 5 張卡的宣告 MUST 被拒絕(不再是合法的戰鬥宣告,因為它們不再帶戰鬥圖示的攻擊用途)。
      **驗收條件**:對這 5 張卡各測試一次 `declare_attack`,確認回傳 `IllegalCommand`(不可攻擊宣告的錯誤碼,如 `spell.no_attack_icon` 或等價)。
      實際結果:`test_nonbattle_spell_cannot_declare_attack`(parametrize 涵蓋全部 5 張)。

## 3. S-036 傷害管線修正

- [x] 3.1 `_s036_on_win` 改為組 `items` 清單呼叫 `_start_damage`,刪除 `injure_or_discard` 函式。
      **驗收條件**:`grep -rn injure_or_discard src/` 無結果。
      實際結果:另外發現原本 `no_book_damage=True` 會讓 `_resolve_showdown` 主流程在 `on_win` 之後誤判「沒有傷害」而提前呼叫 `_finish_battle_damage` 結束戰鬥,導致 `_start_damage` 還在等待 `damage_order`/`protect` 選擇時戰鬥就被錯誤結束。新增 `SpellRider.on_win_owns_damage` 旗標(S-036 專用),`on_win` 呼叫後若此旗標為真則直接 return,不再執行預設分支;S-019/S-020(既有的 `on_win`+`no_book_damage` 用法,效果本身不涉及傷害系統)不受影響。以「暫時還原→確認測試失敗→改回」驗證此修正確實必要。
- [x] 3.2 新增測試驗證 S-036 造成的魔物傷害可被保護。
      **驗收條件**:S-036 獲勝後,防方場上有其他健康魔物時引擎詢問保護,選擇保護後原目標不進入負傷狀態。
      實際結果:`test_s036_damage_can_be_protected`。
- [x] 3.3 新增測試驗證 S-036 造成的傷害會被 P-006 待命無效。
      **驗收條件**:防方預先設置 P-006 對指定魔物的待命無效,S-036 命中該魔物時傷害被無效化,不進入負傷狀態。
      實際結果:`test_s036_damage_negated_by_p006`。
- [x] 3.4 新增測試驗證 S-036 造成的傷害受 M-013/M-015 戰鬥中免疫 modifier 保護。
      **驗收條件**:目標魔物有作用中的 `no_damage` modifier 時,S-036 對其造成的傷害被阻擋。
      實際結果:`test_s036_damage_blocked_by_no_damage_modifier`。另加 `test_s036_damages_book_and_all_mamodo` 驗證基本正確性(魔本+全部魔物皆受傷害)。
- [x] 3.5 前端「選擇先承受哪一項傷害(`damage_order`)」對話框補上可讀標籤。
      **驗收條件**:實際啟動伺服器、以 Playwright 連進本機測試房間重現 S-036 多目標傷害情境,確認對話框顯示「玩家N魔本」或對應卡片(而非索引數字),點擊後能正確送出並繼續流程(截圖存證)。
      實際結果:`_start_damage` 全專案原本只有 `spells.py` 的 S-036 handler 會傳入超過 1 個 item,`damage_order` 這個 pending choice 分支在此變更之前從未在正常對局中真正被觸發過,是一段沒被用過的既有機制——`frontend/app.js:renderPendingDialog` 對它只有 `#${opt.index}` 的陽春 fallback,從未被人發現。使用者實際玩測後發現「只顯示 0/1/2」。修正:`opt.item.kind==="book"` 時顯示「{玩家}魔本」(複用既有 `ui.book` 詞條),`opt.item.kind==="slot"` 時用 `cardEl` 顯示對應卡片(比照其他帶 `card` 欄位的選項)。用 Playwright 實際跑一次 S-036 攻擊、對手 1 隻魔物+魔本受傷的完整流程驗證,截圖確認畫面正確、點擊後能正確進入下一步(保護詢問)。
- [x] 3.6 多項傷害中,若某一項的目標魔物在處理前已消失(被其他項目的保護頂替致入墓),該份傷害 MUST 直接作廢,不得再詢問保護。
      **驗收條件**:對手 A(健康)、B(已負傷)兩隻魔物,S-036 命中魔本+A+B;受方選擇用 B 頂替 A 的傷害,B 因已負傷而入墓;B 自己原本那份傷害不得再觸發任何 `protect`/`damage_order` 詢問,應直接以 `damage_prevented`(`reason="no_target"`)略過。
      實際結果:此為 3.1-3.4 完成後由使用者實際遊玩發現的邊角案例——`_process_damage` 迴圈原本只在damage_order/protect 詢問前檢查「是否有保護者」,沒檢查「該傷害項目自身的目標是否還存在」,導致場上其他健康魔物被誤列為「B 那份已不存在的傷害」的候選保護者。修正:`_process_damage` 迴圈開頭新增一輪過濾,把目標已不在場上的 `slot` 類項目直接從 `ctx["items"]` 移除並各自發出 `damage_prevented(reason="no_target")`,才繼續原本的 `damage_order`/`protect` 判斷。新增 `test_s036_protector_discarded_own_damage_item_skipped`,以「暫時還原修正→確認測試失敗→改回」驗證。

## 4. 新增 S-042/S-045/S-046

- [x] 4.1 `SpellRider` 新增 `damage_bonus` 可選欄位,`_attack_damage_amount` 消費它。
      **驗收條件**:未註冊 `damage_bonus` 的既有卡(如 S-001)行為完全不變,既有測試全數通過。
- [x] 4.2 S-042 註冊 `damage_bonus`,依 `battle.data["attack_total"]` 是否 ≥8000 決定 +2。
      **驗收條件**:兩個測試——合計魔力達 8000 時傷害為基礎值 +2;未達 8000 時傷害維持基礎值。
      實際結果:`test_s042_damage_bonus_at_8000_power`(用 `add_power` 手動補足魔力門檻)、`test_s042_no_bonus_below_8000_power`。以「暫時停用消費邏輯→確認測試失敗→改回」驗證。
- [x] 4.3 S-045/S-046 新增 `on_declare` handler,依擲幣結果設置 `battle.attack_undefendable = True`。
      **驗收條件**:S-045 兩枚皆正面時對手宣告防禦被拒(`defense.undefendable`),未皆正面時可正常防禦;S-046 一枚正面時同樣被拒,反面時可正常防禦。
      實際結果:`test_s045_two_heads_undefendable`/`test_s045_not_both_heads_still_defendable`/`test_s046_one_head_undefendable`/`test_s046_tails_still_defendable`。

## 5. 規格與收尾

- [x] 5.1 確認 `openspec/specs/card-data` 的 `effect_icon` 欄位資料已就緒(依賴 `cards-json-schema-fixes`)。
      **驗收條件**:`data/cards.json` 每張術卡的 `effect_icon` 值可正確讀出,S-041/S-043/S-048/S-057/S-026 為 `"nonbattle"`。
- [x] 5.2 執行完整測試套件。
      **驗收條件**:`pytest` 全數通過。
      實際結果:223 個測試全數通過。
- [x] 5.3 `openspec validate spell-engine-fixes` 確認格式正確。
      **驗收條件**:指令回報 valid,無錯誤。
