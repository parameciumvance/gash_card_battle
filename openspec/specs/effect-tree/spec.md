# effect-tree — 效果樹與直譯器

## Purpose

卡片效果以不可變節點組成的「效果樹」描述(`src/gash/engine/effects/tree.py`),由直譯器逐層解決。效果在停點(等玩家選擇、擲幣確認、待命)停下時,只把續體 `(effect_id, path, ctx)` 存為純資料,醒來時依 path 找回節點繼續。卡片以 `effects/tree_cards.py` 逐卡一行註冊,與既有裝飾器寫法並存,逐卡遷移。
## Requirements
### Requirement: 效果以不可變節點樹描述
系統 SHALL 提供效果樹:效果由不可變(frozen)節點組合而成,節點命名 MUST 以語意為主、不含卡號;卡號 MUST 僅出現在註冊處。效果樹 SHALL 在註冊時建立並存入 `EFFECTS[effect_id]`,對局期間不得被修改。

#### Scenario: 節點與函式名不含卡號
- **WHEN** 檢視效果樹節點類別與其建構函式名稱
- **THEN** 名稱皆為語意命名(如 `Choose`、`Standby`、`AddPower`),不含 `e001` 這類卡號

#### Scenario: source 由註冊層注入
- **WHEN** 以 `reg.event("E-001", effect=<樹>)` 註冊並使用該卡
- **THEN** 直譯器的 `ctx["source"]` 為 `"E-001"`,樹內節點不需自行寫入卡號

### Requirement: 停點續體為純資料
效果解決過程中遇到停點(等待玩家選擇、擲幣確認、待命)時,系統 SHALL 只在遊戲狀態中儲存純資料的續體(可識別效果、停點位置與 `ctx`),MUST NOT 儲存閉包或函式物件。續體 MUST 可 JSON 序列化。

#### Scenario: 停點時狀態可序列化
- **WHEN** 效果因 `Choose` 進入 pending
- **THEN** pending 中的續體只含字串、數字、布林、null、list 與 dict,可直接 `json.dumps`

#### Scenario: 從停點之後繼續
- **WHEN** 玩家回應 `Choose` 的 pending
- **THEN** 直譯器依續體找回該節點,把選擇值寫入 `ctx` 後,只解決該節點之後的節點,不重跑之前的節點

#### Scenario: 續體經序列化往返後仍可恢復
- **WHEN** 停點的續體經 `json.dumps` 再 `json.loads` 後交給 `resume`
- **THEN** 效果照常繼續,結果與未經序列化相同

### Requirement: 停點完成後上溯續行外層節點
停點節點完成後,直譯器 SHALL 沿 `path` 由深往淺上溯:父節點為 `Sequence` 時,依序解決該節點之後尚未執行的兄弟節點,再繼續上溯;上溯途中再次遇到停點時,MUST 存入新續體並停止。每個節點的副作用 MUST 恰好執行一次,不得漏做或重做。擲幣的同步 callback(無 M-012 / M-019 時立即回呼)MUST NOT 造成外層 `Sequence` 重複續行。

#### Scenario: Choose 之後的兄弟節點仍會執行
- **WHEN** `Sequence(A, Choose(…, then=B), C)` 在 `Choose` 停下,玩家回應
- **THEN** 依序執行 B、C,A 不會重做

#### Scenario: 連續兩次 Choose
- **WHEN** 一個效果依序包含兩個 `Choose`
- **THEN** 第一次回應後進入第二個 pending,第二次回應後才完成,兩次選擇值分別綁定於各自的名稱

#### Scenario: 巢狀 Sequence
- **WHEN** 內層 `Sequence` 中的 `Choose` 停下,外層 `Sequence` 在內層之後還有節點
- **THEN** 回應後內層剩餘節點與外層剩餘節點皆依序執行各一次

#### Scenario: Coin 同步完成時外層節點只執行一次
- **WHEN** `Sequence(A, Coin(…), B)` 執行時雙方場上皆無 M-012 / M-019
- **THEN** A、Coin 分支、B 各執行一次

#### Scenario: Coin 進入確認鏈時外層節點只執行一次
- **WHEN** `Sequence(A, Coin(…), B)` 執行時自己場上有可用 M-012,玩家於確認 pending 選擇保留
- **THEN** A 只在停點之前執行一次,Coin 分支與 B 在確認結束後各執行一次

### Requirement: 決策回應依建立來源分派
系統 SHALL 只把由效果樹節點建立的決策(`Choose`、`CoinWithPaidReflip` 的詢問)的玩家回應交回效果樹,由建立該決策的節點續行。擲幣確認鏈的內部決策(`coin_confirm`、`opp_coin_redo`)MUST 依決策種類交給原本的 M-012 / M-019 處理,確認鏈全部結束後才回到效果樹;擲幣確認結束與待命觸發時的續行 MUST NOT 被當成玩家對樹內決策的回應。任何節點的 `prompt` MUST NOT 與引擎保留的決策種類或既有 resolver key 相同,註冊時檢查並拒絕。

#### Scenario: 確認 pending 不被誤送進樹
- **WHEN** 效果樹的 `Coin` 造成 `coin_confirm` pending,玩家回應保留(`None`)或重擲第幾枚(整數)
- **THEN** 由既有 M-012 resolver 處理(含能力消耗與重擲事件),確認鏈結束後才回到樹

#### Scenario: M-019 串接 M-012
- **WHEN** 對手場上有可用 M-019、玩家場上有可用 M-012,效果樹擲幣
- **THEN** 依序出現 `opp_coin_redo`(決策者為對手)與 `coin_confirm`(決策者為玩家)兩個 pending,各自依原流程解決,最後才進入樹的分支

#### Scenario: 保留 kind 被拒絕
- **WHEN** 註冊一個 `Choose(prompt="coin_confirm")` 或 `CoinWithPaidReflip(prompt="coin_confirm")`
- **THEN** 註冊時拋出錯誤

### Requirement: Choose 節點自動驗證與自動解決
`Choose` 節點 SHALL 依選項規格自動產生選項與驗證:僅有一個選項時 MUST 自動解決、不進入 pending;有多個選項時進入 pending;玩家回應的值不在選項內時 MUST 拒絕並保留 pending,不得修改遊戲狀態。

#### Scenario: 單一選項自動解決
- **WHEN** 玩家使用 E-001,場上僅有 1 隻魔物
- **THEN** 不產生 pending,直接以該魔物繼續解決後續節點

#### Scenario: 多個選項進入 pending
- **WHEN** 玩家使用 E-001,場上有 2 隻魔物
- **THEN** 產生 pending,選項為該 2 隻魔物

#### Scenario: 無效選擇保留 pending
- **WHEN** 玩家對 E-001 的 pending 回應不在選項內的值
- **THEN** 指令被拒絕,pending 保留,可重新選擇,遊戲狀態不變

### Requirement: Standby 節點跨回合續體與時效
`Standby` 節點 SHALL 排程待命效果,於指定觸發時機從其 `then` 節點繼續解決。`expires` 為 `"turn"` 時,待命 MUST 於建立當回合結束時移除;為 `"next_start"` 時,MUST 保留到觸發為止。

#### Scenario: E-001 於下回合開始階段觸發
- **WHEN** 玩家使用 E-001 選定魔物,直到下回合開始階段
- **THEN** 該魔物於下回合開始階段獲得 +3000 魔力(持續 `DUR_TURN`),行為與遷移前一致

#### Scenario: 待命不因建立當回合結束而消失
- **WHEN** E-001 的待命(`expires="next_start"`)建立後當回合結束
- **THEN** 待命仍保留,直到下回合開始階段觸發

#### Scenario: 排程後外層節點照常續行
- **WHEN** `Sequence(Standby(…), B)` 執行
- **THEN** 排程完成後立即執行 B,不等待待命觸發;待命觸發時只解決 `Standby.then`,不再重跑 B

### Requirement: Standby.then 限定同步完成
本次 `Standby.then` 子樹 MUST 只含不會停下的節點(不含 `Choose`、`Coin`)。註冊時 SHALL 檢查並拒絕違反者,不得在開始階段執行時才發現。

#### Scenario: 含 Choose 的待命子樹被拒絕
- **WHEN** 註冊 `Standby(…, then=Choose(…))`
- **THEN** 註冊時拋出明確錯誤

### Requirement: 延遲效果重新檢查目標
`Choose` 綁定的目標 SHALL 為穩定的 slot UID。延遲節點(如待命觸發的 `AddPower`)MUST 於執行當下依 UID 重新查找目標;目標已不存在時 MUST 無效果、不建立 modifier、不發出任何事件,且不得改選其他魔物。

#### Scenario: 目標於待命期間離場
- **WHEN** 玩家用 E-001 選定魔物 X,X 於下回合開始階段前離場
- **THEN** 開始階段待命觸發時不建立加魔力 modifier,也不發出 `modifier_added` 事件

#### Scenario: 兩筆待命各指定不同魔物
- **WHEN** 兩筆 E-001 待命分別指定魔物 X 與 Y,下回合開始階段一併觸發
- **THEN** X 與 Y 各自獲得 +3000,互不影響

### Requirement: Coin 節點包住重擲確認鏈
`Coin` 節點 SHALL 由指定的擲幣者(`flipper`,預設為效果擁有者,可指定為對手)擲指定數量硬幣並沿用既有互動式確認鏈(擲幣者的對手以 M-019 令整組重擲、擲幣者以 M-012 重擲確認),確認鏈全部結束後才依結果分支繼續。無論擲幣者是誰,`ctx["player"]` MUST 維持為效果擁有者。`Coin` MUST 僅在第一次執行該節點時消耗 `game.rng` 做初始擲幣;效果樹的 resume 不得再次初始擲幣。玩家依規則要求的 M-012 / M-019 重擲仍照原流程消耗 RNG。

#### Scenario: 擲幣結果決定分支
- **WHEN** 防守方宣告 S-025,擲 1 枚硬幣為正面
- **THEN** 攻擊被無效化,事件與遷移前一致

#### Scenario: 確認鏈期間停下
- **WHEN** 玩家場上有可用的 M-012,其效果樹擲幣後進入重擲確認
- **THEN** 進入 pending 等待玩家決定,決定後才繼續解決 `Coin` 之後的節點

#### Scenario: RNG 消耗次數與遷移前相同
- **WHEN** 以會在超額呼叫時失敗的 RNG 重跑各擲幣入口(傷害後、宣告時、非戰鬥)
- **THEN** 遷移前後 RNG 呼叫次數與結果相同;有重擲時,額外消耗僅來自玩家合法的重擲

#### Scenario: 由對手擲幣
- **WHEN** 玩家使用 E-020,由對手擲 1 枚硬幣為正面
- **THEN** `coin_flipped` 事件的擲幣者為對手;使用者 MP +3、對手 MP +3;對手場上的 M-012 由對手決定是否重擲,使用者場上的 M-019 由使用者決定是否令對手重擲

### Requirement: 效果樹與既有註冊方式並存
所有卡片 SHALL 以效果樹註冊,`tree_cards.py` 為唯一的逐卡註冊檔。系統 SHALL 仍接受既有 `@reg.xxx` 裝飾器 / `CHOICE_RESOLVERS` 字串 key 註冊(裝飾器只剩測試使用,引擎內部的決策 resolver 仍以字串 key 登記);同一張卡 MUST NOT 同時以兩種方式註冊同一個掛鉤。遷移本身為內部重構;遷移過程中依日文效果文修正的行為記錄於 `card-effects` spec,其餘可觀察行為(事件、pending、結算結果)MUST 與遷移前一致。

#### Scenario: 效果樹卡與裝飾器登記並存
- **WHEN** 以效果樹註冊的事件卡與測試用裝飾器註冊的事件卡在同一局各使用一次
- **THEN** 兩者都正常解決

#### Scenario: 重複註冊被拒絕
- **WHEN** 同一張卡的同一掛鉤先後以效果樹與裝飾器各註冊一次
- **THEN** 註冊時拋出錯誤,不靜默覆蓋

#### Scenario: 沒有逐卡 handler 檔
- **WHEN** 檢視 `effects` 套件
- **THEN** 只有 `registry.py`、`primitives.py`、`tree.py`、`tree_cards.py`;舊的 `events.py`、`mamodo.py`、`partners.py`、`spells.py` 已刪除

#### Scenario: 遷移前後行為一致或依效果文修正
- **WHEN** 比較遷移前後的卡片行為
- **THEN** 未依效果文修正的卡,既有測試與遷移前補上的特徵測試皆全數通過;依效果文修正的卡,修正前先寫的測試在舊寫法上失敗、修正後通過

### Requirement: 效果樹掛鉤入口
系統 SHALL 提供下列效果樹註冊入口,並沿用既有引擎入口與檢查:`reg.event(number, effect=…, when=…)`(事件卡)、`reg.spell_rider(number, on_damage=<樹>)`(`rider.on_damage`)、`reg.spell_rider(number, on_declare=<樹>)`(`rider.on_declare`,`ctx` 含 `side`)、`reg.spell_rider(number, on_win=<樹>)`(`rider.on_win`,攻方獲勝時)、`reg.spell_rider(number, on_defense_damaged=<樹>)`(`rider.on_defense_damaged`,`ctx["player"]` 為防禦方、`ctx` 含 `amount`)、`reg.spell_nonbattle(number, effect=<樹>)`(非戰鬥術)。重複註冊以 `(卡號, 掛鉤)` 判定。經 `spell_nonbattle` 註冊的卡 MUST 仍受非戰鬥術的費用、時機與使用次數檢查。`SpellRider` 中要回傳數值的欄位(如 `damage_bonus(game, battle) -> int`)不是效果,MUST NOT 以效果樹註冊;其值 SHALL 以不可變、可呼叫的規格物件提供,不寫 lambda 於註冊檔。魔物 / 夥伴卡 SHALL 另有下列效果樹入口:`reg.activated(number, mode=…, mp_cost=…, timing=…, per_game=…, condition=…, effect=<樹>)`(費用、時機、次數限制與使用條件照舊由引擎檢查)、`reg.on_play` / `reg.on_discard` / `reg.start_phase(number, effect=<樹>)`、`reg.trigger(number, event_type, effect=<樹>)`;這些入口的 `ctx` MUST 含該卡所在魔物的 UID `self_slot`,觸發器另含觸發事件 `event`。只回傳值的查詢(`static_power(value=…)`、`damage_immunity(check=…)`、`spell_compat(check=…)`、`spell_use_limit(value=…)`、`activated(condition=…)`)SHALL 以不可變、可呼叫的規格物件登記,不經效果樹;純資料(`stack_on`、`max_copies`、`mamodo_attack`、`jammer`)以對應的登記函式登記;同卡重複登記 MUST 被拒絕。

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

#### Scenario: 啟動型效果以效果樹註冊
- **WHEN** M-001 以 `reg.activated("M-001", mode="mp", mp_cost=1, timing="battle", condition=SelfInBattleAs("attack"), effect=AddPower(…, target=Ref("self_slot")))` 註冊,玩家在攻擊的戰鬥中使用
- **THEN** 引擎照舊檢查時機、MP、使用條件並扣費,效果樹以 `self_slot` 找到 M-001 所在魔物並加魔力;在防守的戰鬥中使用時以 `ability.condition` 拒絕

#### Scenario: 啟動型效果註冊參數錯誤不留痕跡
- **WHEN** `reg.activated` 傳入不存在的參數名並附效果樹
- **THEN** 註冊時拋出錯誤,`ACTIVATED`、`TREE_HOOKS`、`EFFECTS` 皆不變

#### Scenario: 不支援的 rider 欄位不能傳效果樹
- **WHEN** 嘗試以效果樹註冊 `damage_bonus` 等非效果欄位
- **THEN** 註冊時拋出錯誤,且不留下 `TREE_HOOKS` / `EFFECTS` 記錄

### Requirement: 註冊為原子操作且術卡附加效果每卡只註冊一次
`reg.spell_rider` SHALL 對每張卡只接受一次呼叫;同一張卡再次呼叫(不論掛鉤或旗標,也不論新舊寫法)MUST 被拒絕。任何註冊在檢查失敗時 MUST NOT 留下部分寫入:`TREE_HOOKS`、`EFFECTS`、`SPELL_RIDERS` 等註冊表 MUST 保持呼叫前的內容。

#### Scenario: 再次註冊同一張術卡被拒絕且不影響既有效果
- **WHEN** 已以 `reg.spell_rider("X", on_damage=<樹>, counter=True)` 註冊,再呼叫 `reg.spell_rider("X", on_declare=<樹>)` 或 `reg.spell_rider("X", counter=True)`
- **THEN** 拒絕並拋出錯誤,`X` 的 `on_damage` 效果與 `counter` 旗標仍在,註冊表內容不變

#### Scenario: 驗證失敗不留下部分狀態
- **WHEN** 一次註冊同時傳入合法的 `on_damage` 與不合法的 `on_declare`(如 `Standby.then` 含 `Coin`)
- **THEN** 拒絕並拋出錯誤,`on_damage` 也沒有被寫入或標記為已註冊;修正後可正常註冊

### Requirement: 註冊檔逐卡集中登記
以效果樹註冊的卡片,註冊檔 SHALL 依卡號排序,每張卡的登記集中在一處;同一張卡有多種掛鉤或資料登記(如登場效果加疊放規則、術相容加啟動效果)時,每種一個 `reg.xxx(...)` 呼叫且彼此相鄰。效果邏輯(含使用前置條件與查詢)MUST 位於 `tree.py` 的節點、條件與規格物件及 primitives,不在註冊檔內以 lambda 或具名函式定義。

#### Scenario: 註冊行不含邏輯
- **WHEN** 檢視 E-001 的註冊
- **THEN** 為單一 `reg.event("E-001", when=has_own_mamodo, effect=…)` 呼叫,`when` 引用 `tree.py` 中的具名條件函式,註冊檔內無 lambda 或 handler 函式定義

#### Scenario: 同一張卡的多個登記相鄰
- **WHEN** 檢視 M-027(疊放規則 + 無術攻擊規格)的登記
- **THEN** 為相鄰的 `reg.stack_on("M-027", …)` 與 `reg.mamodo_attack("M-027", …)` 兩個呼叫,前後都是卡號不同的卡

### Requirement: 以對手視角執行子樹
`AsOpponent` 節點 SHALL 以對手的視角解決其子樹:子樹內 `ctx["player"]` 為對手,因此子樹中 `Choose` 的決策者與「自己」相關的選項規格、葉節點都指對手。子樹完成後,外層節點的 `ctx["player"]` MUST 仍為效果擁有者,不論子樹是同步完成或停下後恢復(上溯經過 `AsOpponent` 時換回)。`When` 節點 SHALL 支援 `otherwise` 分支,條件只在進入時判斷一次。

#### Scenario: 對手決策後外層仍是效果擁有者
- **WHEN** `Sequence(AsOpponent(Choose(…, then=A)), B)` 中的 `Choose` 停下
- **THEN** pending 的決策者為對手;對手回應後 A 以對手視角執行,B 以效果擁有者視角執行

#### Scenario: 條件分支只判斷一次
- **WHEN** `When(cond, then=X, otherwise=Y)` 的 X 執行後改變了 cond 的結果
- **THEN** 不會再執行 Y

### Requirement: 付費重擲節點在節點內部迴圈
`CoinWithPaidReflip` 節點 SHALL 擲幣並沿用既有確認鏈;結果符合條件時解決其 `then`,不符合且擁有者 MP 不少於費用時,建立詢問 pending(選項為付費重擲 / 停止),玩家選擇重擲時付費後由同一節點重新擲幣,可重複任意次。迴圈 MUST 只發生在該節點內部:節點只在最終完成(結果符合且 `then` 完成、玩家停止、或 MP 不足)時上溯一次,外層節點的副作用恰好執行一次。玩家回應詢問的值 MUST 為 `True` 或 `False`,否則拒絕並保留 pending;選擇重擲但 MP 不足時同樣拒絕;驗證 MUST 先於任何狀態變更。

#### Scenario: 重擲兩次後外層節點只執行一次
- **WHEN** `Sequence(A, CoinWithPaidReflip(cost=2, then=H), B)` 連續擲出反面、反面、正面,玩家兩次都選擇付費重擲
- **THEN** A、H、B 各執行一次,擁有者 MP 減少 4,RNG 呼叫 3 次

#### Scenario: 停止重擲仍續行外層
- **WHEN** 擲出反面,玩家選擇停止
- **THEN** `then` 不執行,外層後續節點照常執行

#### Scenario: MP 不足時不詢問
- **WHEN** 擲出反面且擁有者 MP 少於費用
- **THEN** 不建立詢問 pending,節點直接完成

#### Scenario: 確認鏈先於重擲詢問
- **WHEN** 擁有者場上有可用 M-012,擲出反面
- **THEN** 先出現 `coin_confirm` pending;玩家保留結果後才出現重擲詢問

#### Scenario: 不合法的回應被拒絕
- **WHEN** 玩家對重擲詢問回應 `True` / `False` 以外的值
- **THEN** 指令被拒絕,pending 與 MP 不變
