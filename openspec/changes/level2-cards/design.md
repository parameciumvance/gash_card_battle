## Context

第一彈架構就緒:效果原語(primitives.py:modifier 四種時效、restriction 旗標、standby、擲幣管線、choose_or_auto)、逐卡 handler 註冊(registry.py:mamodo/partner/event 裝飾器 + SPELL_RIDERS)、香草術資料驅動、`consumed_pages` 頁位空缺追蹤、pending choice 選項視角過濾。xlsx 抽取管線(extract_cards.py)支援 sets 標籤與卡圖超連結。

Level 2 共 67 張新卡(去 e/j 後),其中 4 張 e/j 效果不同(E-018/E-021/E-022/P-012),依既定決策取 j。無官方預組。約半數術卡是香草(資料驅動零 handler),真正要寫的 handler 集中在五類新機制。

## Goals / Non-Goals

**Goals:**
- 67 張全數可用、行為與 j 版效果文一致、每張至少一個效果測試。
- 引擎擴充以「可組合原語+觸發器」落地,不為單卡寫特例流程。
- 既有 115 測試全綠(回歸保護網)。

**Non-Goals:**
- Level 2 預組(補充包無官方套牌;構築器產品過濾已涵蓋)。
- 構築器互動改版、動畫新增(飛卡/翻頁等既有動畫自動適用新事件)。
- Level 3+ 的機制預留(到時再擴)。

## Decisions

### D1. 資料抽取:Level 2 納入範圍

- 過濾條件:Sets 含 "Level 2" **或 "Series 1 Level 2"**(1 張資料例外)。
- e/j 同號取 j、基礎卡號入庫(沿用既有規則);與 Level 1 已收錄的卡號重疊時以聯集 sets 合併(不重複入庫)。
- 卡圖:非 read_only 模式讀 cell.hyperlink.target(既有做法)。
- 中譯:`cards.zh-TW.json` 新增 67 筆(卡名/屬性/效果文)。

### D2. 被動觸發器:[IN PLAY] 事件 hook

- registry 新增 `TRIGGERS: dict[event_type, list[TriggerReg]]`;TriggerReg = (卡號, 條件, handler)。
- 引擎在 `emit()` 後檢查:場上(in-play、健康或依卡而定)有註冊該事件型別的卡 → 執行 handler(可再 emit)。
- 防遞迴:觸發深度上限 4,超出丟棄並記 debug;觸發器產生的事件仍走同一 emit(動畫/記錄自動獲得)。
- 適用:P-013(mamodo_discarded 對手)、P-019(pages_turned 對手回翻)、M-028(裝甲層入墓)。
- 免疫/相容類不走事件 hook,而是查詢式 hook:`QUERY_HOOKS`(如 M-031 傷害免疫判定、M-023/M-029 spell 相容性、M-024 Biraitsu 次數上限)在對應驗證/結算點查詢場上卡。

### D3. 無術攻擊(M-027)

- `declare_attack` 指令支援 `mode: "mamodo"`(帶 slot_uid、不帶 page):驗證=該魔物 handler 註冊了 `mamodo_attack`(M-027 裝甲層,費用 1 MP、合計魔力固定 5000、傷害 2)。
- BattleState `attack_spell=None`、`attack_fixed_power=5000`;魔力勝負以固定值計(不加魔物 power、不吃術 modifier;傷害加減 modifier 仍適用)。
- 防禦方流程不變(可宣告防禦術);戰鬥開始確認(battle_in)同樣觸發。
- 事件:`battle_started` 帶 `spell=None, attacker_mamodo=M-027`;前端對決舞台顯示魔物名代替術名。

### D4. 書內/墓地搜卡原語

- `search_book(player, filter) -> pending choice`:選項=符合條件的頁(頁碼+卡號);解決時自該頁取卡(頁加入 `consumed_pages`)上場/裝備/展示。自己選自己書=決策者可見全部(視角過濾既有規則)。
- `search_opponent_book`(E-016/17):決策者=使用者,選項含對手全書(頁碼+卡號)→ 對「使用者」單獨推 `book_revealed`;選定後棄置+`reduce_mp` 懲罰(不足歸零)。
- `return_to_book(player, card, page)`(M-025):目標頁必須 ∈ `consumed_pages`;`book[page-1]=卡`、移除 consumed 標記。事件 `card_returned_to_book`。
- E-022「本回合入墓」:PlayerState 新增 `discarded_this_turn: list[card]`,回合結束清空。
- 每回合一次翻頁效果(P-010/P-018 條款):GameState 回合旗標 `page_turn_effect_used: set[player]` 與 `page_turnback_effect_used: set[player]`,翻頁/回翻「效果」原語進入點檢查(受傷翻頁與開始階段翻頁不受限)。

### D5. 變身/合體鏈

- M-024 同名雙隻:handler 註冊 `max_copies=2`,放卡驗證由查表(預設 1)取代硬編。
- S-043 Robnos 雙向:2 隻雙體入墓→自書任意頁選完全體上場;或完全體入墓→自書選至多 2 隻雙體上場。用 search_book + 棄置原語組合。
- S-048/M-027 Baltro 疊裝甲:沿用疊放魔物機制(繼承夥伴/效果、最上層生效);差異=裝甲層單獨入墓時**下層保留**(既有疊放是整疊離場)→ 疊放結構加 `detach_top` 操作;M-028 觸發器在 detach 時翻對手 2 頁。
- M-025 完全體進場觸發([IN PLAY] 進場時):從墓選 Robnos 卡回書空頁+MP+2,用 return_to_book。

### D6. Rider/旗標延伸

- SpellRider 新欄位:`damage_cap: int|None`(S-032=3、S-034=4,結算時 min)、`injure_instead: bool`(S-058;S-057 待命版=下一張攻擊勝利術改負傷,以 modifier 旗標實現)。
- 新 restriction 旗標:`no_attack_spell`(P-014)、`mamodo_locked`(E-024 指定魔物:禁其術+效果)、`no_mamodo_effects`(E-025 全體)、`no_sacrifice_no_protect`(S-035,傷害解決時跳過庇護/犧牲決策)。均掛既有 modifier/restriction 架構與指令驗證檢查點。
- Brago 家族:S-033(STAY 對手全魔物 -2000 至對手下個 END)、S-036(勝利時全負傷)、S-037/38(我方免疫至對手下個 END)=既有 duration `until_end_next_turn` + no_damage/power modifier 組合,無新機制。

### D7. 前端選書對話框

- pending choice kind=`book_page` 時,dialog 改渲染對頁網格(16 spread 縮小版,複用構築器 spread 排版概念):每頁位=頁碼+迷你卡面(或卡背,依選項是否含卡號),可點選=送 choose。
- 對手書檢視(E-016/17)同款 UI,資料來自 pending options(僅決策者收到,無資訊外洩)。
- 對決舞台:attack_spell 為 null 時顯示攻擊魔物名(D3)。

### D8. 驗證策略

- 機制單元測試:觸發器(含遞迴上限)、無術攻擊完整戰鬥、雙向變身、疊裝甲 detach、搜卡/回書、傷害上限、負傷代替、各禁止旗標、每回合一次翻頁。
- 逐卡測試:67 張每張至少一測(香草術以資料驅動共用測試模板覆蓋)。
- 回歸:既有 115 測試全綠;E2E 抽測 level 2 卡上場(構築器組含 Level 2 卡的牌組打一場)。

## Risks / Trade-offs

- [觸發器遞迴/交互失控] → 深度上限 4 + 觸發順序固定(場上位置序);測試覆蓋 P-013×M-025(入墓觸發鏈)。
- [無術攻擊破壞戰鬥流程假設(attack_spell 處處被讀)] → BattleState 讀點盤查(views/log/rider 解析),以 `attack_display` 統一取名;E2E 打含 M-027 的完整戰鬥。
- [搜卡選項洩露資訊] → 選項只進 pending.options,視角過濾既有單點(views.py)保證非決策者看不到;測試加雙視角快照斷言。
- [67 張翻譯量] → 效果文以既有詞彙表(負傷/庇護/待命/魔力勝負…)統一,分批自校。
- [e/j 差異誤取] → 抽取腳本斷言 4 張差異卡取 j 版內容(單元測試)。

## Migration Plan

單一變更內完成:資料抽取+翻譯 → 引擎機制(D2-D6,先原語後機制測試)→ 67 張 handler(香草先行、依魔物家族分組)→ 前端選書對話框+舞台調整 → 全量驗證。資料檔為新增,無既有資料遷移。

## Open Questions

- M-027 無術攻擊是否可被戰鬥開始確認(battle_in)插入行動使之失效?依規則書戰鬥開始確認適用所有攻擊宣告 → 先按適用實作,實測有疑義再對規則書。
- S-041/S-057「cannot be defended」與「Special power」並存時對決舞台顯示=「特殊」,沿用第一彈 S-025 做法。
