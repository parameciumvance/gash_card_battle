# game-engine — 設計

## 架構

- 純 Python、無 IO:`engine.submit(game, command)` 收指令、回傳事件列表。前端、API、測試都只透過指令與事件互動。
- 狀態(`engine/state.py`)維持純資料:不存閉包或函式,將來的 history / 重播才可行。
- 卡片效果經 `engine/effects/registry.py` 的掛鉤表接入:引擎在規則的各個時點查表呼叫,效果本身由 `card-effects` / `effect-tree` 持有。

## 中途決策(pending)

- 等待玩家決策時建立 `PendingChoice`,期間只接受該玩家的 `choose` 指令。
- resolver 驗證失敗(拋出 `IllegalCommand`)時保留 pending 讓玩家重選,所以 resolver 必須先驗證、再改狀態。
- 引擎內建的決策種類保留給引擎使用,卡片效果不可重用(`tree.RESERVED_KINDS` 與 `reg.CHOICE_RESOLVERS` 的 key):`protect`、`damage_order`、`deploy_page`、`injure_instead_target`、`coin_confirm`、`opp_coin_redo`、`jammer_negate`、`spell_discount`。
- 由效果樹建立的決策如何分派回樹,見 `effect-tree/design.md`。
