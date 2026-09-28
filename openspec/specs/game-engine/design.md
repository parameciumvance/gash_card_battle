# game-engine — 設計

## 架構

- 純 Python、無 IO:`engine.submit(game, command)` 收指令、回傳事件列表。前端、API、測試都只透過指令與事件互動。
- 狀態(`engine/state.py`)維持純資料:不存閉包或函式,將來的 history / 重播才可行。
- 卡片效果經 `engine/effects/registry.py` 的掛鉤表接入:引擎在規則的各個時點查表呼叫,效果本身由 `card-effects` / `effect-tree` 持有。
- `engine/awaiting.py` 提供對狀態的純查詢:`awaited_player`(目前等誰輸入)與 `default_command`(安全預設指令)。規則不依賴它們;房間層的計時器、逾時代打與 NPC 共用(見 `online-room/design.md`)。

## 中途決策(pending)

- 等待玩家決策時建立 `PendingChoice`,期間只接受該玩家的 `choose` 指令。
- resolver 驗證失敗(拋出 `IllegalCommand`)時保留 pending 讓玩家重選,所以 resolver 必須先驗證、再改狀態。
- 引擎內建的決策種類保留給引擎使用,卡片效果不可重用(`tree.RESERVED_KINDS` 與 `reg.CHOICE_RESOLVERS` 的 key):`protect`、`damage_order`、`deploy_page`、`injure_instead_target`、`coin_confirm`、`opp_coin_redo`、`jammer_negate`、`spell_discount`。
- 由效果樹建立的決策如何分派回樹,見 `effect-tree/design.md`。
- `PendingChoice.data` 是私有的(續體、傷害佇列等內部資料),不送出;`PendingChoice.info` 是公開的決策脈絡,快照對所有視角附上。目前擲幣相關的詢問(M-012 `coin_confirm`、M-019 `opp_coin_redo`、E-011 `paid_reflip`)在 `info.results` 放目前各枚的結果(`primitives.coin_info`)。

## 魔力勝負明細

- 合計魔力由逐項明細推得,只有一份計算:`power_breakdown`(魔物魔力)與 `side_breakdown`(一方合計)回傳 `(total, items)`,`slot_power` / `_side_total` 只取 total。所以明細與合計不可能對不上。
- 每一項為 `{"kind", "source", "amount"}`,各項 amount 加總恆等於 total。「視為 0」(P-011)、「不低於 0」、「無效化」都寫成明確的調整項,數值為被補上或扣掉的量:

```text
mamodo / static / modifier / partnered / power_zero / mamodo_floor   ← 魔物魔力
spell / defense_self / spell_bonus / spell_floor                      ← 術魔力
fixed                                                                  ← 無術攻擊(M-027)
negated                                                                ← 無效化(合計歸 0)
```

- 戰鬥中術魔力的加減一律經 `primitives.add_spell_power` 記進 `battle.data["<side>_spell_power"]`(每筆含來源卡);無效化的來源記在 `battle.data["<side>_negated_by"]`;無術攻擊的魔物記在 `attack_fixed_source`。新增會改變術魔力的效果時,也要經這個函式,明細才會有來源。
- `showdown` 事件附 `attacker`、`attacker_breakdown`、`defender_breakdown`;快照的 `battle` 附同樣的即時明細。
