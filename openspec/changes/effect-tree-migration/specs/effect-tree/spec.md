## MODIFIED Requirements

### Requirement: 效果樹與既有註冊方式並存
系統 SHALL 同時支援以效果樹註冊與既有 `@reg.xxx` 裝飾器 / `CHOICE_RESOLVERS` 字串 key 註冊;同一張卡 MUST NOT 同時以兩種方式註冊同一個掛鉤。遷移為內部重構,遊戲可觀察行為(事件、pending、結算結果)MUST 與遷移前一致。

#### Scenario: 已遷移與未遷移的卡並存
- **WHEN** E-001 以效果樹註冊、E-002 仍以裝飾器註冊,雙方各使用一次
- **THEN** 兩者都正常解決,既有測試全數通過

#### Scenario: 重複註冊被拒絕
- **WHEN** 同一張卡的同一掛鉤先後以效果樹與裝飾器各註冊一次
- **THEN** 註冊時拋出錯誤,不靜默覆蓋

#### Scenario: 逐批遷移過程中整體卡池行為不變
- **WHEN** 效果樹遷移(`effect-tree-migration`)跨多次工作階段逐批進行,任一時間點都同時存在已遷移與未遷移的卡
- **THEN** 每一批遷移前後,`card-effects` spec 涵蓋的全部卡片既有測試(含該批遷移前補上的特徵測試)皆全數通過;遷移未完成不影響尚未遷移的卡正常運作

### Requirement: 註冊檔逐卡一個呼叫
以效果樹註冊的卡片,註冊檔 SHALL 每張卡恰好一個 `reg.xxx(...)` 呼叫並依卡號排序;效果邏輯(含事件卡的使用前置條件)MUST 位於 `tree.py` 的節點、條件函式與 primitives,不在註冊檔內以 lambda 或具名函式定義。單一呼叫 MAY 跨多行排版:有子節點的容器節點(`Choose` / `Coin` / `When` / `Standby`)換行並縮排一層,使巢狀層次可直接由縮排辨識。

#### Scenario: 註冊行不含邏輯
- **WHEN** 檢視 E-001 的註冊
- **THEN** 為單一 `reg.event("E-001", when=has_own_mamodo, effect=…)` 呼叫,`when` 引用 `tree.py` 中的具名條件函式,註冊檔內無 lambda 或 handler 函式定義

#### Scenario: 巢狀層次由縮排辨識
- **WHEN** 檢視含兩層以上容器節點的註冊(如 S-021 的 `When` → `Coin` → `NegateAttack`)
- **THEN** 每個容器節點的子節點比該容器多縮排一層,容器的收尾括號獨立成行並與開頭對齊

## RENAMED Requirements

- FROM: `### Requirement: 註冊檔逐卡一行`
- TO: `### Requirement: 註冊檔逐卡一個呼叫`
