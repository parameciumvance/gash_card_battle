# battle-api — 差分:視角化與推送

指令身分改由 token 判定;快照/事件依觀看者過濾;新增 WebSocket 推送。引擎介面不變。

## MODIFIED Requirements

### Requirement: 建立對局
對局 SHALL 經由房間流程建立(見 `online-room`):線上房於雙方到齊時、本機房於建房時,載入預組魔本(雙方共用 level1.json)、初始化引擎(可選指定 RNG seed)、執行準備階段。直接建立無主對局的舊端點 MUST 移除。

#### Scenario: 開局初始狀態
- **WHEN** 房間雙方到齊而建立對局
- **THEN** 狀態為先攻玩家的開始階段,雙方 MP 2、首頁魔物已在場

### Requirement: 指令提交
API SHALL 提供指令提交端點:以 token 鑑別玩家(payload 的 `player` 欄位 MUST 被忽略,由伺服器填入),轉交引擎;回傳引擎結果(成功=新狀態摘要+本次事件列表,均經提交者視角過濾;失敗=原因碼)。指令 MUST 逐一循序處理,同一對局不併發。

#### Scenario: 提交合法指令
- **WHEN** 回合玩家以自己的 token 提交翻頁指令
- **THEN** 回應含 PagesFlipped/MPChanged 事件與更新後(自己視角的)狀態

#### Scenario: 提交非法指令
- **WHEN** 玩家提交時機不符的指令
- **THEN** 回應 4xx 與引擎原因碼,對局狀態不變

### Requirement: 狀態快照與資訊隱藏
狀態快照 SHALL 依觀看者(player0/player1/觀戰)產生:包含渲染所需完整公開狀態(階段、行動權、雙方 MP、場面、魔本進度、戰鬥子狀態、pending 的 kind 與決策者、事件序號)。**未翻開頁面的內容 MUST NOT 出現在任何回應中**;**翻開頁的卡片內容 MUST 只對持有者可見**,對手與觀戰者僅見頁碼;**pending 的選項細節 MUST 只對決策者可見**。本機模式的 client 持有雙方 token,視為全視角。

#### Scenario: 未翻頁內容不外洩
- **WHEN** 任一玩家魔本尚有未翻開頁
- **THEN** 任何視角的回應中未翻開頁僅以頁碼/張數表示,不含卡片內容

#### Scenario: 對手翻開頁不可見
- **WHEN** 玩家 A 查詢狀態
- **THEN** 玩家 B 的 open_pages 僅含頁碼,無卡號與費用;A 自己的 open_pages 完整

#### Scenario: 決策選項只送決策者
- **WHEN** M-011 效果等待玩家 A 從 B 的魔本挑選魔物
- **THEN** 只有 A 的視角含選項(頁碼與卡號);B 與觀戰者僅見「A 決策中」

#### Scenario: 快照可完整重繪
- **WHEN** 前端重新整理後以 token 查詢狀態
- **THEN** 回應足以完整重建該視角畫面(含行動 log),無需重放指令

### Requirement: 事件記錄
對局 SHALL 累積自開局以來的全部事件(含序號);API MUST 支援自指定序號起增量取得事件,且回放內容 MUST 與即時推送同樣經視角過濾:帶 viewer 標記的事件(檢視魔本/偷看頁面)只對該玩家可見,choice_required 對非決策者去除選項細節。

#### Scenario: 增量取得事件
- **WHEN** 客戶端以上次已知序號查詢事件
- **THEN** 僅回傳其後發生、且該視角可見的事件,序號遞增

#### Scenario: 檢視類事件不外洩
- **WHEN** 玩家 A 以 M-011 檢視了 B 的魔本
- **THEN** book_revealed 的卡片清單只出現在 A 的事件流;B 與觀戰者僅知檢視發生

## ADDED Requirements

### Requirement: WebSocket 事件推送
API SHALL 提供房間 WebSocket 端點:以 token 鑑別視角;連線即送 welcome(該視角完整快照+下一事件序號);此後每次指令產生的事件 MUST 即時推送給所有連線,內容經各自視角過濾。WS 斷線 MUST NOT 影響 HTTP 指令提交。

#### Scenario: 對手行動即時可見
- **WHEN** 玩家 A 提交指令產生事件
- **THEN** 玩家 B 與觀戰者的 WS 各自收到過濾後的事件批次,無需輪詢

#### Scenario: 重連對齊序號
- **WHEN** 玩家重建 WS 連線
- **THEN** welcome 含 next_seq,前端以序號去重,不重複顯示既有記錄
