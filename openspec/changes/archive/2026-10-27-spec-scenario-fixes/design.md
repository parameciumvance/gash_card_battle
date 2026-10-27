# Design

## Context

規則出處:atwiki 規則頁(https://w.atwiki.jp/zatchbell/pages/94.html)「かわりばんこのルール」:「1つのバトルが終了し、非バトルに戻るとまずターンプレイヤーがアクションすることができます」。使用者已對照規則確認。引擎 `_end_battle` 已設定行動權為回合玩家並歸零連續 pass,`tests/test_engine.py` 的戰鬥測試已斷言。

## Decisions

### card-data 的情境改名直接改主規格

OpenSpec 的 MODIFIED 必須帶上主規格既有的所有情境名稱(validate 與 archive 都會拒絕刪除),所以情境改名、刪除無法以 delta 表達。這兩個情境只是說明,需求本文不變,在 reconciliation 時直接改 `openspec/specs/card-data/spec.md`;delta 只放 `game-engine`。

- 替代方案:REMOVED 整條「卡片資料轉換」再以新名稱 ADDED。需求名稱是其他文件引用的錨點(README、design、測試的模組說明),為了改情境名稱而改需求名稱得不償失。

### 不新增測試

行為已有 `tests/test_engine.py` 斷言(戰鬥結束後 `action_player == turn_player`);本 change 只把既有行為寫進規格。
