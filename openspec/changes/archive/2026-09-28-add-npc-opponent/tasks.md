## 1. 準備與 spike

- [x] 1.1 把 `awaited_player` / `default_command` 從 `api/rooms.py` 移到 `engine/awaiting.py`,`rooms.py` 改由該處匯入;`tests/test_timer.py` 全過(行為不變)
- [x] 1.2 Spike:以最小可行的 `decide`(候選列舉 + determinize + settle + 評估)跑 NPC 自我對戰,量測單次決策耗時分佈;選定 K、settle 步數上限,使 dev 機 p99 ≤ 200 ms,數字記錄到 design.md D6

## 2. NPC 決策(`src/gash/npc/`)

- [x] 2.1 `candidates.py`:依 design D2 列舉各決策點的候選指令,在副本上試送過濾
- [x] 2.2 `determinize.py`:依 design D3 建立副本(對手隱藏頁抽樣、換 RNG、清空事件、jammer 快照、`_trigger_depth`),抽樣先驗依對手場上魔物加權
- [x] 2.3 測試「NPC 只依自己看得到的資訊決策」:由自我對戰收集決策點,換對手隱藏頁 / 魔本順序、換 `game.rng`,先確認 NPC 視角快照與過濾事件相同,再斷言決定相同;另寫兩個 spec 情境的固定局面測試
- [x] 2.4 `settle.py`:依 design D4 模擬到停點與對手回應規則
- [x] 2.5 `evaluate.py`:依 design D5 的特徵與初始權重
- [x] 2.6 `__init__.py` 的 `decide`:`dummy` 回傳 `default_command`;`normal` 依 D4 回傳排序好的候選清單;思考量依 1.2 的上限
- [x] 2.7 測試「一般難度的基本判斷」三個情境(致命傷害會保護、不防禦會落敗時會防禦、有機會致勝時攻擊),先確認測試走到目標決策點
- [x] 2.8 測試「NPC 不會卡住對局」:各決策點都能出手;首選被拒時改送下一個候選與安全預設;NPC 對 NPC(dummy / normal 各組合 × 各預組 × 多個 seed)每局都以勝負結束、無拒絕指令以外的例外
- [x] 2.9 測試「NPC 難度」:木人樁行為與 `default_command` 一致;一般 vs 木人樁勝多於敗
- [x] 2.10 測試「NPC 決策可重現」:同 seed、同玩家指令 → 事件序列相同

## 3. 房間與 API

- [x] 3.1 `CreateRoom` 新增 `npc_level` / `npc_deck` / `npc_decks`;`Room.npc`(`NpcSeat`);驗證(難度、牌組、候選上限、指定與候選互斥);隨機抽選;NPC 房立即開局、只回傳一個 token、無計時器、`join` 回 409;`_effective_viewer` 為 0;meta 的 `npc`(`deck` 對局結束後才公開)
- [x] 3.2 NPC 驅動:依 design D10 的 `kick` / `drive`、每房單一 task、延遲常數(測試設 0)、sleep 後比對事件數重新決定、候選依序改送、`_timeout_loop` 保險 kick;觸發點含開局、`post_command`、金手指套用
- [x] 3.3 `debug-state` 開放 `npc` 模式;本機房與 NPC 房的觀戰 token 回 403(design D11,已確認)
- [x] 3.4 API 測試:`online-room`「建立房間」「NPC 房」「NPC 座位的驅動」與 `local-test-mode` 的新情境

## 4. 前端

- [x] 4.1 首頁 NPC 對戰面板:我的牌組、NPC 牌組(含「隨機」,缺省)、難度(缺省一般)、暱稱;隨機時送出所有預組與本機儲存的合法牌組為候選;i18n 文字
- [x] 4.2 NPC 房 session(`mode: "npc"`, viewer 0)沿用線上房的呈現與 WS;不顯示計時;NPC 名稱依難度的 i18n 文字
- [x] 4.3 `canCheat()` 開放 NPC 房
- [x] 4.4 對局結束顯示 NPC 牌組名稱(預組名稱 / 本機儲存牌組名稱 / 「自訂牌組」)
- [x] 4.5 瀏覽器測試:開始 NPC 對戰(指定與隨機)、NPC 行動後盤面更新、NPC 房的金手指入口、結束時顯示 NPC 牌組

## 5. 文件

- [x] 5.1 README:NPC 對戰的使用方式;專案結構加入 `src/gash/npc/`

## 6. Reconciliation 與歸檔(指南 §13)

- [x] 6.1 同步 delta spec 回主 spec:新增 `npc-opponent/spec.md`(寫入 Purpose 與 scope);`online-room`、`battle-ui` 的 MODIFIED / ADDED;`local-test-mode` 的 RENAMED + MODIFIED,並更新其 Purpose(不再只限本機房)
- [x] 6.2 Reconcile affected capability design and rationale:
  - 新增 `npc-opponent/design.md`:架構、determinize 關卡、一般難度的流程、評估特徵、思考量上限與同步執行的理由。
  - 新增 `online-room/design.md`:NPC 座位與驅動、逾時代打共用 `engine/awaiting.py`。
  - `game-engine/design.md` 註記 `awaiting.py` 的查詢。
- [x] 6.3 Update capability map:新增 `npc-opponent`(遊戲核心或對戰服務子系統,覆蓋程度)、`online-room` 的 design 覆蓋、系統概觀與對戰指令 flow 加入 NPC 座位
- [x] 6.4 從 `openspec/changes/todo.md` 移除「NPC對戰」
- [x] 6.5 `openspec validate --all --strict`、`python -m pytest` 全過後歸檔
