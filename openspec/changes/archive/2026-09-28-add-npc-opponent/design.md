## Context

- 對局目前只有兩種:線上房(兩位真人)與本機測試模式(一人操作雙方、全視角)。
- 房間層已經有一個「零智慧的代打」:`rooms.awaited_player(game)` 判斷等誰輸入,`rooms.default_command(game)` 給出安全預設,逾時時經正常的 `submit` 路徑送出(`app._fire_due_timeouts`)。NPC 就是把「逾時才代打」換成「輪到 NPC 就代打」,再換上會評估局面的決策。
- 引擎沒有「列出合法指令」的函式;前端的 `spellUsable` 等只是猜測,合法性以伺服器拒絕為準。
- 探索時的實測(dev 機):複製一份 `GameState` 約 0.04 ms;一個決策點的候選指令約 10 個,在副本上逐一試送約 0.6 ms。候選少,是因為能用的頁只有目前那一對頁(`PlayerState.open_pages()`),加上最多 3 隻魔物與 pass。
- 對手的隱藏資訊只有:翻開頁的卡、魔本未公開頁的順序、對局 RNG(未來的擲幣)。這個遊戲沒有手牌。
- 已確認的決定(專案負責人):
  - 先做 L2(一步前瞻)。
  - NPC 看不到隱藏資訊。
  - NPC 牌組可用預組或自訂牌組,可指定或隨機;隨機時對局結束才公開。
  - NPC 房開放金手指,並提供木人樁難度。

## Goals / Non-Goals

**Goals:**

- 伺服器驅動的 NPC 對手,玩家以一般視角對戰。
- NPC 的決定在結構上不可能讀到隱藏資訊,並有測試證明。
- NPC 只送出引擎接受的指令,不會卡住對局;引擎規則不改。
- 同 seed、同玩家指令可重現整局(之後的 history / 重播可用)。
- 單次決策的思考量有固定上限,不影響同一台伺服器的其他房間。

**Non-Goals:**

- 深度搜尋(L3:MCTS / 多步 rollout)。
- NPC 記住戰鬥中宣告過的對手術頁:戰鬥事件不帶頁碼,戰鬥結束後這些頁會重新抽樣(只會比玩家知道得少)。事件記錄中帶頁碼的公開資訊與只給 NPC 看的頁則會保留(見 D3)。
- NPC 插入行動打斷對手的攻擊(戰鬥開始確認時插入行動):候選會列出,但模擬裡的對手回應規則不會這樣做。
- 評估權重的系統化調校:v1 手調,調校工具另案。
- 線上房中以 NPC 代替離線玩家。

## Decisions

### D1:NPC 在伺服器的房間層驅動

NPC 是房間的一個座位:輪到它時,由伺服器呼叫決策、經 `submit` 送出、廣播事件,和逾時代打走同一條路。

- 替代方案「前端 JS 當 NPC」:前端必須握有 NPC 的 token 並看得到 NPC 的隱藏資訊,也要在 JS 重寫規則判斷。不採用。
- 替代方案「獨立程序以 API 連線當玩家」:隔離最好,但單機發行版要多管一個程序,也要處理重連。不採用。

### D2:合法指令用「在副本上試送」判斷,不在引擎新增合法指令產生器

候選指令依指令型別與參數列舉:
- `pass`、`flip_pages` 0~3
- 對目前翻開頁的 `play_card` / `use_book_card` / `declare_attack`(每隻魔物各一)/ `declare_defense`
- 每隻魔物的 `use_field_ability`(mamodo / partner)與無術攻擊
- `battle_in_response` 與插入行動
- pending 的每個選項(與 `default_command` 相同的取值方式)

逐一在副本上 `submit`,被拒的剔除。引擎維持唯一的規則權威,不會出現第二份規則。

- 替代方案「引擎提供 `legal_commands()`」:等於把每個 `IllegalCommand` 分支再寫一次,新卡的條件容易漏,而且兩份規則會分歧。不採用。

### D3:公平性集中在 `determinize`,所有模擬都經過它

`npc.determinize(game, npc_player, rng) -> Game` 產生 NPC 可以使用的副本,是 NPC 取得盤面的唯一入口:

- 對手魔本:
  - 已放出或已消耗的頁(`consumed_pages`)保留;這些卡已經公開。
  - 宣告中的術頁(同 views 的 `_in_use_pages`)保留;宣告即公開。
  - 事件記錄中 NPC 看得到的頁保留:`book_card_used`(對手使用魔本中的事件卡或非戰鬥術,事件帶卡號與頁碼)、`book_revealed` / `pages_peeked` 中 `viewer` 為 NPC 者(E-014 / E-016 / E-017 讓 NPC 看的頁)。E-016 / E-017 的選擇選項本身就是這些頁,因此選項與副本一致。
  - 其他頁重新抽樣。
- `rng`:換成由 NPC 隨機來源產生的新 `Random`。
- `events`:清空。
- `jammer`:其中的 `snapshot`(一整份 `GameState`)同樣替換對手的隱藏頁。
- `_trigger_depth` 歸零。
- `state` 用 `copy.deepcopy`,卡片資料庫 `db` 共用(唯讀)。

合法性試送也在 determinize 後的副本上進行。極少數合法性取決於對手隱藏資訊的情況下,真正送出時可能被拒,所以決策輸出排序好的候選清單,驅動依序改送,最後退回 `default_command`(spec「NPC 不會卡住對局」)。

抽樣的先驗:從卡片資料庫中的卡抽。對應魔物在對手場上的術卡提高權重,因為術要有對應魔物在場才能用(`engine._spell_usable_by`)。權重是常數,集中在一處。

驗證用「換掉隱藏資訊、決定不變」的測試:
- 由自我對戰收集大量決策點。
- 每個點做一份變體:換對手的隱藏頁與魔本順序、換 `game.rng` 狀態。
- 先確認變體的 `snapshot(g, npc)` 與 `filter_events(g.events, npc)` 相同,再斷言 NPC 的決定相同。

「看得到什麼」沿用 views.py 的定義,不維護第二份。

- 替代方案「評估函式只讀 `snapshot(sim, npc)`」:能擋住評估時讀到隱藏資訊,但模擬本身(對手在模擬裡的回應)仍會用到真實的隱藏頁。不採用,改為在來源就換掉。

### D4:一般難度 =「一步 + 模擬到塵埃落定」

單純試走一步在戰鬥中看不出結果:宣告攻擊後只到「等對手回應」,勝負還沒出來。所以一般難度這樣做:

```text
對每個合法候選 c:
  做 K 次:
    sim = determinize(game, npc, npc_rng)
    submit(sim, c)
    settle(sim):依序處理等待者,直到停點
      對手 → 回應規則(見下)
      NPC  → default_command
      停點:對局結束 / 戰鬥結束 / 回合交替 / 又輪到 NPC 做非戰鬥決定 / 步數上限
    score(c) += evaluate(sim, npc)
依平均分排序;同分依候選列舉順序(可重現)
```

模擬中對手的回應規則,刻意保持簡單、便宜:
- 戰鬥開始確認:迎戰。
- 防禦:在合法的防禦中,選能擋下攻擊(防方合計 ≥ 攻方合計)且費用最低的;沒有就不防禦。擋不擋得下,由在副本上試送後比較 `_side_total` 判斷。
- 戰鬥中效果:pass。
- 保護:魔本受傷時,若有健康的魔物就以魔力最低者保護;魔物受傷不保護。
- 其他中途決策:`default_command`。

NPC 自己的中途決策(例如效果的選擇對象)是獨立的決策點,用同一套流程決定,不寫專屬規則。效果樹的新卡因此不需要教 NPC。

- 替代方案「模擬中對手也用 L2」:算力約乘 5,會卡住 event loop。不採用。

### D5:評估函式

`evaluate(game, npc)` 回傳分數(對 NPC 越高越好),特徵與初始權重集中在 `npc/evaluate.py` 的常數:

- 勝負:NPC 勝為 +∞、敗為 −∞。
- 生命:雙方剩餘頁數(`PlayerState.pages_remaining()`),越接近 0 扣分越重(非線性)。
- MP:邊際遞減,超過「目前可用的最貴術費用」的部分價值很低。
- 場面:
  - 魔物魔力合計(`slot_power`)。
  - 健康 / 負傷(負傷再中一次會被棄)。
  - 有沒有夥伴。
  - 場上魔物數;0 隻特別扣分,因為有「全滅且無法再放出」的敗北條件。
- 潛力:目前翻開頁上「NPC 的魔物能用、MP 付得起」的最強攻擊術魔力。

開始階段翻 0~3 張的取捨(生命、MP、落在哪一對頁),由生命、MP、潛力三項決定。對手的同樣特徵(對手的潛力不可見,不計)以負權重計入。

### D6:思考量以次數計,不以時間計

上限是固定的:候選數、K(抽樣次數)、settle 步數。不用牆鐘時間截斷,否則結果會因機器快慢而不同,破壞可重現性。

實作前先做 spike:
- 以 NPC 自我對戰收集決策點,量測單次決策的耗時分佈。
- 選定 K 與步數上限,使 dev 機的 p99 ≤ 200 ms。

Spike 結果(dev 機,level1 / level2 各組合,每組 24 局):

```text
K=6,  步數上限 60:一般 vs 一般 p99 6.8 ms,最長 17 ms
K=16, 步數上限 60:一般 vs 一般 p99 15.6 ms,最長 45 ms
                   一般 vs 木人樁 48 局全勝;一般 vs 一般 先後攻 12:12
```

遠低於預估(候選少、settle 多半幾步就到停點),所以採用 K=16(`npc.SAMPLES`)、步數上限 60(`settle.MAX_STEPS`)。

### D7:NPC 在 event loop 中同步思考

- 決策是純 CPU 計算;受 GIL 限制,丟到執行緒不會變快,只會讓 event loop 在思考期間仍能切換。
- `effects/tree.py` 的 `_next_token += 1` 不是執行緒安全的。
- 所以 v1 在持有房間鎖時同步執行,用 D6 的上限控制耗時。將來要移出 event loop 時,需先讓 `tree._next_token` 改用執行緒安全的計數。

### D8:`awaited_player` / `default_command` 移到引擎

NPC 套件不應依賴 api 層。這兩個函式都是對引擎狀態的純查詢(誰該輸入、安全預設),所以移到新模組 `src/gash/engine/awaiting.py`,`api/rooms.py` 改由該處匯入。規則與行為不變。

### D9:房間與 API

- `Room` 新增 `npc: NpcSeat | None`,欄位:
  - `seat`:固定為 1。
  - `level`。
  - `rng`:由房間 seed 衍生;seed 為 None 時隨機。
  - `deck`:實際使用的牌組,`{preset}` 或 `{pages}`。
  - `task`:目前的驅動 task。
- `CreateRoom` 新增:
  - `npc_level`(缺省 `normal`)。
  - `npc_deck`:單一牌組。
  - `npc_decks`:隨機候選,上限 64 副,避免濫用。
- 隨機抽選用 `NpcSeat.rng`,在開局前抽,所以同 seed 抽到同一副。
- 房間 meta 新增 `npc: {"seat", "level", "deck"}`;`deck` 在對局結束前為 `None`。
- `join` 對 NPC 房回 409(沿用 `room.not_joinable`)。
- NPC 房的 `timer_seconds` 一律為 None。
- `_effective_viewer`:NPC 房的玩家為 0(不是 `"all"`)。

### D10:NPC 驅動

```text
kick(room):若 room.npc.task 仍在執行則不動作,否則建立 task 執行 drive(room)

drive(room):
  while 對局未結束 且 awaited_player(game) == npc.seat:
      version = len(game.events)
      ranked = decide(game, npc)                     # 同步
      await sleep(delay(ranked[0]))                  # pass 類 0.3s,其他 0.9s
      async with lock:
          if len(game.events) != version 或等待者已改變:
              continue                               # 局面變了(如金手指),重新決定
          依序 submit ranked,全被拒則 submit default_command
          touch;reset_deadline
      broadcast(events)
```

- 觸發點:NPC 房開局後、`post_command` 成功後、金手指套用後。
- `_timeout_loop` 每秒檢查一次作為保險:輪到 NPC 卻沒有執行中的 task 就 kick。
- 延遲是模組常數;測試設為 0。
- 決策在 sleep 之前做,才能依指令型別決定延遲;sleep 後以事件數判斷局面是否變了。

### D11:金手指與觀戰

- `debug-state` 的模式檢查改為 `local` 或 `npc`。
- 同時對兩種房的觀戰 token 回 403。原本 GET 沒有擋觀戰者,會讓觀戰者看到雙方魔本,與 `online-room`「觀戰」只給公開資訊的要求矛盾。此項改變本機房既有(未文件化)的行為,已經專案負責人確認採用。

### D12:前端

- 首頁新增「NPC 對戰」面板:
  - 我的牌組:沿用 `deckOptions`。
  - NPC 牌組:`deckOptions` 加上「隨機」(缺省)。
  - 難度。
  - 暱稱。
- 開始後 `SESSION = {mode: "npc", viewer: 0, tokens: {me}}`,開 WS,呈現與線上房相同。
- `isNpc()`;`canCheat()` 放寬為本機或 NPC 房。
- NPC 名稱依 `room.npc.level` 取 i18n 文字,例如「NPC(一般)」。
- 對局結束後由 `room.npc.deck` 解析牌組名稱:
  - `{preset}`:用預組名稱。
  - `{pages}`:比對本機儲存牌組,找到用其名稱,找不到用「自訂牌組」。

### D13:套件結構

```text
src/gash/npc/
  __init__.py      decide(game, player, level, rng) -> 排序好的候選清單(對外唯一入口)
  candidates.py    候選列舉與試送過濾
  determinize.py   隱藏資訊替換與副本建立
  settle.py        模擬到停點、對手回應規則
  evaluate.py      評估函式與權重
```

## Risks / Trade-offs

- [評估函式太粗,NPC 打得笨] → 權重集中一處;以「一般 vs 木人樁勝多於敗」與基本判斷情境把關;之後可用自我對戰調權重(另案)。
- [抽樣先驗與實際牌組差太多,NPC 高估或低估對手的防禦] → 先驗依對手場上魔物加權;列為之後調整點。
- [隱藏資訊從沒想到的路徑漏進決策(待命資料、jammer 快照、事件)] → 決策只經 `determinize` 取得盤面;「換掉隱藏資訊、決定不變」的測試在大量自我對戰決策點上跑,不只手寫幾個局面。
- [思考卡住 event loop] → D6 的次數上限 + spike 量測;超標時先降 K。
- [模擬裡的 `submit` 碰到共享狀態] → 副本是全新的 `Game`;registry 為唯讀;`tree._INFLIGHT` 以 token 區分且在 `finally` 清除;同步執行,不會交錯。
- [驅動重複執行,同一決策點送兩次] → 每房只有一個 task;送出前在鎖內比對事件數。
- [對局卡在等待 NPC] → 候選依序改送 → `default_command` → `_timeout_loop` 保險 kick。
- [基本判斷情境依賴隨機抽樣而不穩] → 決策可重現,測試固定 seed;情境選的是勝負立即可分的局面。

## Migration Plan

新增功能,沒有資料遷移。`awaited_player` / `default_command` 的搬移沒有行為變化,由既有 `tests/test_timer.py` 驗證。

## Open Questions

- K、settle 步數上限、延遲秒數:由 spike 與實際試玩決定,記錄回本檔。
