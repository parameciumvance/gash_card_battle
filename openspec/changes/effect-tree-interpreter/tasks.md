## 1. 續體資料與直譯器骨架

- [ ] 1.1 新增 `effects/tree.py`(或等效模組):`Effect` 基底、`Sequence` 節點、`Ref`、`EFFECTS` 註冊表與 `effect_id`(`"<卡號>:<掛鉤>"`)產生規則;節點皆為 frozen dataclass。**驗收:** 節點可建構、雜湊、不可變(嘗試賦值拋 `FrozenInstanceError`)。
- [ ] 1.2 實作 `run(game, batch, effect_id, ctx, path=())` 與 `resume(game, batch, value, data)`:依 `effect_id` 與 `path` 找回節點,找不到時拋出明確錯誤;續體只存 `(effect_id, path, ctx)`,`ctx` 僅含 JSON 可序列化值。**驗收:** 單元測試以 `json.dumps` 序列化續體成功;path 無效時拋錯。
- [ ] 1.3 註冊通用 resolver `CHOICE_RESOLVERS["effect_tree_resume"]`,對應 `resume`。**驗收:** 以假 Standby 的 callback 呼叫可從指定 path 繼續。
- [ ] 1.4 `registry.py` 新增以效果樹註冊的入口(`reg.event(number, effect=…, when=…)` 直接呼叫形式、`reg.spell_rider(..., on_damage=<樹>)`),註冊時注入 `ctx["source"]`,並把薄包裝寫入既有表;同一卡同一掛鉤重複註冊(樹與裝飾器)拋錯。**驗收:** 既有裝飾器用法不變;重複註冊測試通過。
- [ ] 1.5 確認骨架落地後 `python -m pytest` 既有 248 個測試全數通過,尚未遷移任何卡。

## 2. Choose / Standby 節點與 E-001

- [ ] 2.1 實作選項規格 `OwnMamodo()`(`options(game, ctx)` 與驗證)及 `Choose(target, bind, prompt, then)` 節點:單一選項自動解決、多選項建立 `PendingChoice` 並在 `data["cont"]` 存續體、無效值拋 `IllegalCommand("choose.invalid", …)` 且不改狀態。**驗收:** 對應 spec 的三個 Choose 情境有單元測試。
- [ ] 2.2 `engine.py` 的 `choose` 指令處理(`CHOICE_RESOLVERS.get(pending.kind)` 之前)加入:`pending.data` 含 `cont` 時改呼叫 `resume`,並維持「resolver 拋出時保留 pending」的既有行為。**驗收:** 無效選擇後 pending 仍在、可重選。
- [ ] 2.3 實作 `Standby(at, expires, then)` 節點與 `NextStartPhase()` 時機:建立 `Standby(kind="start_phase", data={"callback": "effect_tree_resume", "cont": …, "expires": …})`;`AddPower` 葉節點包裝 `add_power`。**驗收:** `expires="next_start"` 的待命不因建立當回合結束而被移除,`expires="turn"` 則會。
- [ ] 2.4 將 E-001 改為 `reg.event("E-001", when=…, effect=Choose(OwnMamodo(), bind="slot", prompt="e001_pick", then=Standby(NextStartPhase(), expires="next_start", then=AddPower(amount=3000, duration=DUR_TURN))))`,移除舊的 `e001` / `e001_pick` / `e001_fire`。`prompt` 暫沿用 `"e001_pick"` 以維持前端 i18n。**驗收:** E-001 相關既有測試全數通過(含單魔物自動解決、多魔物選擇、下回合開始階段 +3000)。

## 3. Coin 節點與擲幣類卡片

- [ ] 3.1 實作 `Coin(count, on, then, otherwise)` 節點:呼叫 `flip_coins(..., callback="effect_tree_resume", data={"cont": …})`,結果寫入 `ctx["results"]`,確認鏈結束後才依條件分支;resume 不重新擲幣。**驗收:** 固定 seed 下擲幣序列與遷移前相同;M-012 / M-019 確認鏈期間 pending 正確。
- [ ] 3.2 新增所需葉節點:`Restrict`(包裝 `add_restriction`)、`NegateAttack`、`MakeUndefendable`(包裝 `schedule_standby(kind="attack_undefendable")`)。**驗收:** 各葉節點的事件與遷移前的 primitives 呼叫一致。
- [ ] 3.3 遷移 S-004、S-014(傷害後擲幣 → 禁術)為 `reg.spell_rider("S-004", on_damage=Coin(1, on=Heads(), then=Restrict(NO_SPELLS, …)))` 等單行註冊,移除 `_coin_lock_spells` 與 `lock_spells_coin`。**驗收:** 對應既有測試通過。
- [ ] 3.4 遷移 S-021、S-025(擲幣無效攻擊)與 S-026(非戰鬥術:擲幣 → 待命不可防禦),移除 `_coin_negate` / `coin_negate_resolve` / `s026` / `s026_resolve`。**驗收:** 對應既有測試通過(含 S-021 兩枚至少一正、S-025 一枚)。
- [ ] 3.5 對已遷移的卡確認註冊檔逐卡一行、依卡號排序,且註冊行內無具名 handler 函式定義。

## 4. 整合與收尾

- [ ] 4.1 新增並存測試:E-001 走效果樹、同局另一張舊寫法的事件卡照常運作;同卡同掛鉤重複註冊拋錯。
- [ ] 4.2 完整跑 `python -m pytest`,248 個既有測試加上新增測試全數通過。
- [ ] 4.3 在 README(專案結構或效果系統段落)補一小段說明:新卡片一律以效果樹註冊、節點清單位置、舊寫法為遷移期保留;並在 `openspec/changes/todo.md` 記錄後續 change(其餘卡片遷移、前端 `choice.title.*` 依節點種類改名)。
