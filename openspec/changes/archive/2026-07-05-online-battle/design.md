## Context

v1 架構:純 Python 引擎(指令進/事件出、事件帶全域 seq)← FastAPI 薄殼(記憶體對局表)← 無框架前端。指令帶 `player` 欄位且伺服器照單全收;快照對雙方等同(全知)。已歸檔規格見 `openspec/specs/`。

線上化的探索結論(已與需求方確認):翻開頁依原規則對對手隱藏;範圍含觀戰與回合計時;無帳號。

## Goals / Non-Goals

**Goals:**
- 兩位玩家各自瀏覽器約戰:建房 → 分享連結 → 對戰;斷線可重連續打。
- 資訊視角正確:對手翻開頁不可知(直到使用展示)、決策選項不外洩、觀戰者純公開視角;所有過濾收斂在 API 層,引擎零改動。
- 對局不因掛機卡死(計時器逾時代打安全動作)。
- 本機 hotseat 模式保留,與線上共用同一前端與後端路徑。

**Non-Goals:**
- 帳號、配對、排名、聊天、對局持久化、多伺服器擴展、TLS 部署自動化。
- 防作弊超出「資訊不外洩+指令驗證」的範圍(如流量分析、計時側信道)。

## Decisions

### D1. 房間模型:Room 包裹 Game,token 即身分

```
Room {
  code: 6碼英數(分享用)
  mode: "online" | "local"
  tokens: { token₀→player0, token₁→player1, spectator_token→觀戰 }
  timer_seconds: None|30|60|120
  game: Game(既有引擎物件,雙方到齊才建立)
  sockets: {player|spectator → set[WebSocket]}
  deadline: 目前等待輸入方的逾時時刻
}
```

- `POST /api/rooms {mode, timer}` → `{code, player_token, join_url, spectate_url}`;`POST /api/rooms/{code}/join` → `{player_token}`,到齊即 `new_game` 並廣播開局。
- 指令 `POST /api/rooms/{code}/commands`,token 放 header(`X-Player-Token`);伺服器由 token 查出 player 填入指令,payload 的 `player` 欄位忽略。引擎介面不變。
- 本機模式:建房即回傳兩個 token,同一 client 輪流帶不同 token 送指令——前端維持現行 hotseat 畫面,後端只有一條代碼路徑。
- **替代方案**:cookie session(否決:分享連結+無帳號下 token 更直觀);把身分塞進引擎(否決:引擎不該知道鑑別)。

### D2. 視角過濾:單一函式族,viewer ∈ {player0, player1, spectator}

- `snapshot(game, viewer)`:基於既有 `snapshot()` 增加 viewer 參數。
  - `players[p].open_pages`:p == viewer 時含卡號/費用;否則只給 `{page}`(頁碼公開,內容保密)。
  - `pending`:`kind/player` 公開(誰在想、想多久是公開資訊);`options` 僅 viewer == pending.player 時附上。
  - 其餘欄位(場面、MP、棄牌區、已宣告攻防、合計魔力)本就是展示過的公開資訊,不過濾。
- 事件過濾 `visible(ev, viewer)`:按事件型別的慣例——`book_revealed`/`pages_peeked` 已帶 `viewer` 欄位,只推給該玩家;`choice_required` 對非當事者去除 `options`/`item` 細節。其餘事件公開。
- 觀戰者 = viewer="spectator",兩邊私密皆不可見;同一套函式,無特例分支。
- **關鍵不變量**:任何回應/推送在產生前都經過 viewer 過濾;不存在「先送全量再由前端隱藏」的路徑。
- 風險備忘:`GET /events?since` 回放同樣要過濾;本機模式 viewer 視為雙重身分(全視角,維持 v1 行為)。

### D3. 推送:WebSocket 下行推事件,指令仍走 HTTP POST

- `WS /api/rooms/{code}/ws?token=...`:連上即推 `{type:"welcome", state: snapshot(viewer), next_seq}`,之後每次任何指令產生事件,對每個連線推送過濾後的事件批次+輕量狀態摘要。
- 指令走 POST 不走 WS:沿用既有驗證/錯誤語意(4xx+原因碼),重試語意簡單;WS 純下行,斷了不影響出招(POST 仍可用)。
- 斷線重連 = 重開 WS(welcome 帶全量狀態);前端以 `next_seq` 對齊 log,不重放已顯示事件。
- **替代方案**:全雙工 WS 指令(否決:錯誤處理/重送要自建協議);SSE(可行,但 FastAPI 原生 WS 更順手且未來可上行擴展)。

### D4. 回合計時器:API 層代打,引擎無感

- 房間建立時選 `timer_seconds ∈ {None,30,60,120}`。每當「等待輸入的玩家」改變,重置 deadline;asyncio 背景任務逾時觸發。
- 「等待誰」由既有狀態推導:pending → pending.player;戰鬥防禦步 → 防方;battle_in → 防方;效果步 → effect_turn;開始階段 → 回合玩家;非戰鬥 → action_player。
- 逾時代送安全預設指令:開始階段 `flip 0`、非戰鬥/效果步 `pass`、battle_in `讓過`、防禦步 `不防禦`、pending 依 kind(protect→不庇護、coin_confirm→保留、e011_retry→放棄、各類 pick→第一個選項)。
- 代打即正常指令,走同一條提交路徑並廣播;不判負、不特殊事件(log 標記 `timeout: true`)。
- **替代方案**:超時判負(否決:斷線=瞬敗太苛);棋鐘制總時間(延後,規則複雜)。

### D5. 前端:入口分流 + 線上視角

- 首頁三動作:本機對戰(即現行為)/建立房間(選計時)/輸入房號加入;join_url 直接帶房號開加入流程。
- 線上模式:自己永遠渲染在下方(以 token 對應的 player 翻轉視角);只有自己的行動按鈕啟用;對手翻開頁渲染為卡背+頁碼。觀戰視角雙方皆卡背。
- 連線狀態列(WS 連線中/重連中)、對手回合的等待指示、計時倒數(以伺服器 deadline 推算,純顯示,裁決在伺服器)。
- 本機模式重用現行渲染(全視角、雙方按鈕),差異只在「client 持有幾個 token」。

### D6. 測試策略

- 視角過濾單元測試為重點:對同一局面產出 viewer=0/1/spectator 三份快照與事件流,斷言對手翻開頁無卡號、options 只在當事者、M-011 檢視事件不外洩。
- 房間流程整合測試(TestClient + WS):建房→join→開局→出招→雙端收到各自過濾的推送→斷線重連對齊 seq。
- 計時器測試:注入極短 timer,驗證逾時代打與 deadline 重置;pending 各 kind 的預設動作各一測。
- 既有 93 個測試維持綠燈(引擎不動;API 測試隨新介面改寫)。

## Risks / Trade-offs

- [視角過濾漏網:新增事件/欄位時忘記過濾即洩露] → 過濾採「白名單公開」原則寫成單點函式 + 針對性測試;code review 檢查新事件必須聲明可見性。
- [計時代打選 pick 類「第一個選項」可能非最優(如 E-009 加力目標)] → 接受;逾時是玩家自己的風險,規則上任何合法選擇皆有效。
- [WS 與 POST 競態(推送先於 POST 回應到達)] → 前端以 seq 去重,兩通道冪等。
- [記憶體對局,伺服器重啟全失] → v1 範圍明確接受並寫入 README;Room 結構已為未來序列化預留(引擎狀態本為 dataclass)。
- [BREAKING 舊 `/api/games` 介面] → 全部呼叫端(前端+測試)在同一變更內遷移,不留相容層。

## Migration Plan

單一變更內完成:後端房間層 → 視角過濾 → WS → 前端入口/視角 → 計時器。舊 `/api/games` 端點移除,README 更新啟動與約戰說明。無資料遷移。

## Open Questions

- 房號碰撞與生命週期:6 碼隨機 + 閒置(如 2 小時無事件)回收——實作時定數值即可,不影響介面。
- 本機模式是否也要能被觀戰?(直覺:不需要,先不做。)
