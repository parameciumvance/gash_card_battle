# online-room — 設計

目前只整理了等待者推導與 NPC 座位;其餘房間設計(token、計時器、重連、觀戰)尚未文件化,以 `src/gash/api/rooms.py`、`app.py` 與測試為準。

## 等待者與安全預設

`engine/awaiting.py` 提供兩個對引擎狀態的純查詢:
- `awaited_player`:目前等待哪位玩家輸入。
- `default_command`:安全預設指令。

房間層用它們做兩件事:計時器期限(`Room.reset_deadline`)與逾時代打(`app._fire_due_timeouts`)。NPC 也共用這兩個查詢:木人樁就是送安全預設,NPC 的候選全部被拒時也退回安全預設。

## NPC 座位

- `Room.npc` 為 `NpcSeat`:
  - `seat`:固定為 1。
  - `level`。
  - `rng`。
  - `deck`:實際使用的牌組,`{preset}` 或 `{pages}`。
  - `task`:目前的驅動 task。
- `rng` 由房間 seed 衍生(`Random(f"npc:{seed}")`;seed 為 None 時隨機),隨機牌組抽選與 NPC 決策共用,所以同 seed 可重現整局。
- 建房時先驗證 NPC 難度與所有候選牌組,全部通過才抽選並建房。
- 房間 meta 的 `npc` 為 `{seat, level, deck}`,`deck` 在對局結束前為 `None`。
- NPC 房的玩家視角為 0(`_effective_viewer` 只有本機房給全視角)。

## NPC 驅動

```text
_kick_npc(room):輪到 NPC、且沒有執行中的驅動 task 時才建立 task

_drive_npc(room):
  while 輪到 NPC:
      version = 事件數
      ranked = decide(...)           # 同步;例外時記錄並改用安全預設
      await 稍候(依首選指令型別)
      async with 房間鎖:
          事件數變了或已不是 NPC → continue(重新決定)
          submit_ranked;全被拒時記錄並結束
      broadcast
```

- 觸發點:NPC 房開局、玩家指令被接受後、金手指套用後。`_timeout_loop` 每秒對所有房間 kick 一次作為保險。
- 先決定再稍候,才能依指令型別決定等多久:pass、迎戰、不防禦、不翻頁為 `NPC_QUIET_DELAY`(0.7 秒),其他為 `NPC_ACTION_DELAY`(1.3 秒)。兩者略長於前端標準速度的聚焦展示(pass 0.5 秒、其他 1 秒),畫面才跟得上 NPC;跟不上時前端會自動加快(見 `battle-ui/design.md`)。
- 稍候後在鎖內比對事件數,局面變了(例如套用金手指)就依新局面重新決定。
- 每房只有一個驅動 task,加上鎖內的事件數比對,確保同一決策點只送出一次。

## 行為決定與理由

### 隨機 NPC 牌組在對局結束後才公開

**相關規格:** `online-room` › 需求「NPC 房」 › 情境「對局中不公開 NPC 牌組」「對局結束後公開 NPC 牌組」

**決定:** NPC 使用的牌組只在對局結束後出現在房間 meta(指定與隨機都一樣,規則只有一條)。

**理由:** 對局中公開就失去「隨機」的意義;指定的情況玩家本來就知道內容。

**依據:** 專案負責人於規劃 NPC 對戰時採納。

**確認狀態:** `Project Decision`

### NPC 房不計時

**相關規格:** `online-room` › 需求「NPC 房」

**決定:** NPC 房一律不使用計時器,建房請求的計時選項不採用。

**理由:** 對手是 NPC,玩家不需要被催促;NPC 自己不會逾時。

**依據:** 專案負責人於規劃 NPC 對戰時採納。

**確認狀態:** `Project Decision`
