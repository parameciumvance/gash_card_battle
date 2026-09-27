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

### Requirement: 效果樹掛鉤入口
系統 SHALL 提供下列效果樹註冊入口,並沿用既有引擎入口與檢查:`reg.event(number, effect=…, when=…)`(事件卡)、`reg.spell_rider(number, on_damage=<樹>)`(`rider.on_damage`)、`reg.spell_rider(number, on_declare=<樹>)`(`rider.on_declare`,`ctx` 含 `side`)、`reg.spell_rider(number, on_win=<樹>)`(`rider.on_win`,攻方獲勝時)、`reg.spell_rider(number, on_defense_damaged=<樹>)`(`rider.on_defense_damaged`,`ctx["player"]` 為防禦方、`ctx` 含 `amount`)、`reg.spell_nonbattle(number, effect=<樹>)`(非戰鬥術)。重複註冊以 `(卡號, 掛鉤)` 判定。經 `spell_nonbattle` 註冊的卡 MUST 仍受非戰鬥術的費用、時機與使用次數檢查。`SpellRider` 中要回傳數值的欄位(如 `damage_bonus(game, battle) -> int`)不是效果,MUST NOT 以效果樹註冊;其值 SHALL 以不可變、可呼叫的規格物件提供,不寫 lambda 於註冊檔。

#### Scenario: 宣告時效果僅防禦方生效
- **WHEN** 以 `When(SideIs("defense"), Coin(…))` 註冊的 `on_declare` 效果,以 `side="attack"` 執行
- **THEN** 不擲幣、無任何效果;以 `side="defense"` 執行時才擲幣(S-021 / S-025 為防禦專用術卡,引擎只會以防禦側呼叫)

#### Scenario: 傷害後效果的擁有者
- **WHEN** S-004 以 `rider.on_damage` 註冊並造成傷害
- **THEN** 效果的 `ctx["player"]` 為造成傷害的一方,禁術對象為其對手

#### Scenario: 非戰鬥術經引擎入口使用
- **WHEN** 玩家透過 `use_book_card` 使用以 `reg.spell_nonbattle("S-026", …)` 註冊的 S-026
- **THEN** 費用、時機與使用次數檢查與遷移前一致,不會得到 `spell.not_implemented`

#### Scenario: 防禦方被造成傷害時取得傷害量
- **WHEN** 防禦方以 S-056 防禦,魔力勝負落敗且魔本受到 N 點傷害
- **THEN** `on_defense_damaged` 效果的 `ctx["player"]` 為防禦方、`ctx["amount"]` 為 N,防禦方 MP 增加 2×N

#### Scenario: 不支援的 rider 欄位不能傳效果樹
- **WHEN** 嘗試以效果樹註冊 `damage_bonus` 等非效果欄位
- **THEN** 註冊時拋出錯誤,且不留下 `TREE_HOOKS` / `EFFECTS` 記錄

## RENAMED Requirements

- FROM: `### Requirement: 註冊檔逐卡一行`
- TO: `### Requirement: 註冊檔逐卡一個呼叫`
