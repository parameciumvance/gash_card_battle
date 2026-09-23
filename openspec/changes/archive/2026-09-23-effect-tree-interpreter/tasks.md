## 1. 遷移前特徵測試(先固定現行行為)

遷移前後這些測試都必須通過。既有測試無法證明等價:`tests/` 沒有 M-019 / `opp_coin_redo` 案例,腳本 RNG 用完後固定回傳反面而抓不到額外消耗。

- [x] 1.1 新增「嚴格 RNG」測試輔助:依腳本序列回傳,序列用完再呼叫即拋錯;並提供呼叫計數。**驗收:** 超額呼叫時測試失敗。
- [x] 1.2 新增 M-019 特徵測試(透過 `submit(..., type="choose")`):對手保留、對手付費令整組重擲;逐步斷言每個 pending 的 `kind`、決策者、能力消耗標記、重擲事件與最終效果。**驗收:** 現行實作通過。
- [x] 1.3 新增 M-019 → M-012 串接特徵測試,同樣透過 `submit`。**驗收:** 現行實作通過。
- [x] 1.4 補三種擲幣入口的特徵測試,各含「無確認 pending」與「有 M-012 確認 pending」兩種路徑:傷害後(S-004 / S-014)、宣告時(S-021 / S-025,)、非戰鬥(S-026);另含兩枚硬幣的結果分支(S-021)。斷言事件序列、公開 pending 快照與 RNG 消耗次數。**驗收:** 現行實作通過。
- [x] 1.5 補 E-001 特徵測試:多魔物選擇(含無效選擇後保留 pending 並重選)、選定後目標於下回合開始階段前離場(不建立 modifier、無事件)、兩次使用(事件卡每回合限 1 張,無法同回合建立兩筆)各指定不同 UID。**驗收:** 現行實作通過。

## 2. 續體資料與直譯器骨架

- [x] 2.1 新增 `effects/tree.py`(或等效模組):`Effect` 基底、`Sequence`、`When`、`Ref`、`EFFECTS` 註冊表與 `effect_id`(`"<卡號>:<掛鉤>"`)規則;節點皆為 frozen dataclass,固定子節點索引順序,宣告 `may_suspend`。**驗收:** 節點不可變;`may_suspend` 依子節點正確推導。
- [x] 2.2 實作 `run` / `resume` 與「上溯續行」規則:停點 `path` 指向停點節點本身,完成後由深往淺上溯,`Sequence` 依序解決之後的兄弟節點,途中再次停下則存新續體;找不到節點時拋出明確錯誤。**驗收:** 單元測試涵蓋:巢狀 `Sequence`、連續兩次 `Choose`、`Choose` 後仍有兄弟節點;續體經 `json.dumps` → `json.loads` 後仍能恢復(不只驗證能輸出 JSON);每個副作用恰好一次。
- [x] 2.2b 實作 `Coin` 的 in-flight 記號(行程內暫存、不進 state):同步 callback 只回填結果、不上溯,`Coin.run` 返回後就地續行;非同步恢復才上溯。**驗收:** `Sequence(A, Coin(...), B)` 在「無確認 pending」與「有 M-012 確認 pending」下,A、B 各執行一次。
- [x] 2.3 註冊通用 resolver `CHOICE_RESOLVERS["effect_tree_resume"]`;續體鍵分開:`Choose` 用 `tree_choice`,`Coin` / `Standby` 的 callback payload 用 `tree_cont`。**驗收:** 兩種鍵不會互相被誤判。
- [x] 2.4 `registry.py` 新增四個掛鉤入口:`reg.event(effect=…)`、`reg.spell_rider(on_damage=<樹>)`、`reg.spell_rider(on_declare=<樹>)`(包裝簽名含 `side`,寫入 `ctx["side"]`)、`reg.spell_nonbattle(number, effect=…)`;註冊時注入 `ctx["source"]`,以 `(卡號, 掛鉤)` 檢查重複(與裝飾器註冊衝突也拒絕);註冊時拒絕 `Choose.prompt` 與保留 kind 相同,拒絕 `Standby.then` 含會停下的節點。**驗收:** 既有裝飾器用法不變;三類非法註冊各有測試。
- [x] 2.5 確認骨架落地後既有測試與 1 組特徵測試全數通過,尚未遷移任何卡。

## 3. Choose / Standby 節點與 E-001

- [x] 3.1 實作選項規格 `OwnMamodo()` 與 `Choose(target, bind, prompt, then)`:bind 存 slot UID;單一選項自動解決;多選項建立 `PendingChoice`,續體存於 `data["tree_choice"]`;無效值拋 `IllegalCommand("choose.invalid", …)` 且不改狀態。**驗收:** spec 的 Choose 情境有單元測試。
- [x] 3.2 `engine.py` 的 `choose` 指令處理:**僅**在 `pending.data` 含 `tree_choice` 時呼叫 `resume`,其餘維持依 `pending.kind` 找 resolver,並維持「resolver 拋出時保留 pending」。**驗收:** 透過 `submit(..., type="choose")` 驗證:樹的 `Choose` 能回應、無效選擇後 pending 仍在;`coin_confirm` / `opp_coin_redo` 仍走原 resolver(1.2、1.3 不因此失敗)。
- [x] 3.3 實作 `Standby(at, expires, then)`(脫離式:排程後回傳 `DONE`,觸發時只解決 `then` 且不上溯)與 `NextStartPhase()`;`AddPower(target=Ref("slot"), …)` 於執行時依 UID 重新查找,目標不存在則無效果、不建立 modifier、不發事件。**驗收:** `expires="next_start"` 跨回合保留、`expires="turn"` 於當回合結束移除;`Sequence(Standby(…), B)` 中 B 不等待觸發且不在觸發時重跑。
- [x] 3.4 將 E-001 改為單行 `reg.event("E-001", when=…, effect=Choose(OwnMamodo(), bind="slot", prompt="e001_pick", then=Standby(NextStartPhase(), expires="next_start", then=AddPower(target=Ref("slot"), amount=3000, duration=DUR_TURN))))`,移除舊的 `e001` / `e001_pick` / `e001_fire`。`prompt` 暫沿用 `"e001_pick"` 以維持前端 i18n。**驗收:** 1.5 與既有 E-001 測試全數通過。

## 4. Coin 節點與擲幣類卡片

- [x] 4.1 實作 `Coin(count, on, then, otherwise)`:呼叫 `flip_coins(..., callback="effect_tree_resume", data={"tree_cont": …})`;結果寫入 `ctx["results"]`;確認鏈由既有 resolver 處理,結束後才回到樹;效果樹恢復不再次初始擲幣。**驗收:** 1.2 / 1.3 / 1.4 的確認鏈情境通過;RNG 呼叫次數不超額。
- [x] 4.2 新增葉節點:`RestrictOpponent`(包裝 `add_restriction`)、`NegateAttack`、`MakeNextAttackUndefendable`(包裝 `schedule_standby(kind="attack_undefendable")`),以及條件 `SideIs`、`HeadsAtLeast(n)`。**驗收:** 各節點的事件與遷移前 primitives 呼叫一致。
- [x] 4.3 遷移 S-004、S-014 為 `reg.spell_rider(…, on_damage=Coin(…))` 單行註冊,移除 `_coin_lock_spells` 與 `lock_spells_coin`。**驗收:** 1.4 對應情境與既有測試通過。
- [x] 4.4 遷移 S-021、S-025(`on_declare`,`When(SideIs("defense"), Coin(…))`),移除 `_coin_negate` 與 `coin_negate_resolve`。**驗收:** 1.4 對應情境通過;S-021 / S-025 是防禦專用術卡(`ad=D`),引擎不可能由攻擊方宣告,故「攻擊側不擲幣」以節點單元測試(`ctx["side"]="attack"`)驗證。
- [x] 4.5 遷移 S-026(`reg.spell_nonbattle`),移除 `s026` / `s026_resolve`。**驗收:** 透過 `use_book_card` 走引擎入口,費用、時機、使用次數檢查與遷移前一致,不出現 `spell.not_implemented`。
- [x] 4.6 確認已遷移的卡註冊行逐卡一行、依卡號排序,註冊行內無具名 handler 函式定義。

## 5. 整合與收尾

- [x] 5.1 新增並存測試:E-001 走效果樹、同局另一張舊寫法的事件卡照常運作;同卡同掛鉤重複註冊拋錯。
- [x] 5.2 完整跑 `python -m pytest`,既有測試加上特徵測試與新增測試全數通過。
- [x] 5.3 在 README(專案結構或效果系統段落)補一小段:新卡一律以效果樹註冊、節點位置、舊寫法為遷移期保留、`Standby.then` 限同步;並在 `openspec/changes/todo.md` 記錄後續 change(其餘卡片遷移、前端 `choice.title.*` 依節點種類改名、支援可停下的 `Standby.then`)。
