## ADDED Requirements

### Requirement: 戰術卡附加效果的效果樹入口
系統 SHALL 提供下列戰術卡附加效果的效果樹註冊入口,並沿用既有引擎入口與檢查:`reg.spell_rider(number, on_damage=<樹>)`(`rider.on_damage`)、`reg.spell_rider(number, on_declare=<樹>)`(`rider.on_declare`,`ctx` 含 `side`)、`reg.spell_rider(number, on_win=<樹>)`(`rider.on_win`,攻方獲勝時)、`reg.spell_rider(number, on_defense_damaged=<樹>)`(`rider.on_defense_damaged`,`ctx["player"]` 為防禦方、`ctx` 含 `amount`)。重複註冊以 `(卡號, 掛鉤)` 判定。

#### Scenario: 宣告時效果僅防禦方生效
- **WHEN** 以 `When(SideIs("defense"), Coin(…))` 註冊的 `on_declare` 效果,以 `side="attack"` 執行
- **THEN** 不擲幣、無任何效果;以 `side="defense"` 執行時才擲幣(S-021 / S-025 為防禦專用戰術卡,引擎只會以防禦側呼叫)

#### Scenario: 傷害後效果的擁有者
- **WHEN** S-004 以 `rider.on_damage` 註冊並造成傷害
- **THEN** 效果的 `ctx["player"]` 為造成傷害的一方,禁戰術對象為其對手

#### Scenario: 防禦方被造成傷害時取得傷害量
- **WHEN** 防禦方以 S-056 防禦,魔力勝負落敗且魔書受到 N 點傷害
- **THEN** `on_defense_damaged` 效果的 `ctx["player"]` 為防禦方、`ctx["amount"]` 為 N,防禦方 MP 增加 2×N

### Requirement: 事件卡與非戰鬥戰術的效果樹入口
系統 SHALL 提供 `reg.event(number, effect=…, when=…)`(事件卡)與 `reg.spell_nonbattle(number, effect=<樹>)`(非戰鬥戰術)兩個效果樹註冊入口,並沿用既有引擎入口與檢查。經 `spell_nonbattle` 註冊的卡 MUST 仍受非戰鬥戰術的費用、時機與使用次數檢查。

#### Scenario: 非戰鬥戰術經引擎入口使用
- **WHEN** 玩家透過 `use_book_card` 使用以 `reg.spell_nonbattle("S-026", …)` 註冊的 S-026
- **THEN** 費用、時機與使用次數檢查與遷移前一致,不會得到 `spell.not_implemented`

### Requirement: 魔物與搭檔卡的效果樹入口
魔物 / 搭檔卡 SHALL 有下列效果樹入口:`reg.activated(number, mode=…, mp_cost=…, timing=…, per_game=…, condition=…, effect=<樹>)`(費用、時機、次數限制與使用條件照舊由引擎檢查)、`reg.on_play` / `reg.on_discard` / `reg.start_phase(number, effect=<樹>)`、`reg.trigger(number, event_type, effect=<樹>)`;這些入口的 `ctx` MUST 含該卡所在魔物的 UID `self_slot`,觸發器另含觸發事件 `event`。

#### Scenario: 啟動型效果以效果樹註冊
- **WHEN** M-001 以 `reg.activated("M-001", mode="mp", mp_cost=1, timing="battle", condition=SelfInBattleAs("attack"), effect=AddPower(…, target=Ref("self_slot")))` 註冊,玩家在攻擊的戰鬥中使用
- **THEN** 引擎照舊檢查時機、MP、使用條件並扣費,效果樹以 `self_slot` 找到 M-001 所在魔物並加魔力;在防守的戰鬥中使用時以 `ability.condition` 拒絕

#### Scenario: 啟動型效果註冊參數錯誤不留痕跡
- **WHEN** `reg.activated` 傳入不存在的參數名並附效果樹
- **THEN** 註冊時拋出錯誤,`ACTIVATED`、`TREE_HOOKS`、`EFFECTS` 皆不變

### Requirement: 回傳值的登記不經效果樹
`SpellRider` 中要回傳數值的欄位(如 `damage_bonus(game, battle) -> int`)不是效果,MUST NOT 以效果樹註冊;其值 SHALL 以不可變、可呼叫的規格物件提供,不寫 lambda 於註冊檔。只回傳值的查詢(`static_power(value=…)`、`damage_immunity(check=…)`、`spell_compat(check=…)`、`spell_use_limit(value=…)`、`activated(condition=…)`)SHALL 以不可變、可呼叫的規格物件登記,不經效果樹;純資料(`stack_on`、`max_copies`、`mamodo_attack`、`jammer`)以對應的登記函式登記;同卡重複登記 MUST 被拒絕。

#### Scenario: 不支援的 rider 欄位不能傳效果樹
- **WHEN** 嘗試以效果樹註冊 `damage_bonus` 等非效果欄位
- **THEN** 註冊時拋出錯誤,且不留下 `TREE_HOOKS` / `EFFECTS` 記錄

## REMOVED Requirements

### Requirement: 效果樹掛鉤入口
**Reason**: 一條需求混了戰術卡附加效果、事件卡與非戰鬥戰術的入口、魔物與搭檔卡的入口、回傳值與純資料的登記,依行為拆分。
**Migration**: 內容與情境移至「戰術卡附加效果的效果樹入口」「事件卡與非戰鬥戰術的效果樹入口」「魔物與搭檔卡的效果樹入口」「回傳值的登記不經效果樹」,行為不變。
