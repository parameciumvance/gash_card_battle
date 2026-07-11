# battle-api — 後端對局 API

## Purpose

FastAPI 薄殼:房間內對局的指令轉發、視角化狀態快照與事件、WebSocket 推送。引擎為唯一規則權威;所有回應經觀看者視角過濾。
## Requirements
### Requirement: 建立對局
對局 SHALL 經由房間流程建立(見 `online-room`):線上房於雙方到齊時、本機房於建房時,載入預組魔本、初始化引擎(可選指定 RNG seed)、執行準備階段。牌組欄位 SHALL 解析為下列之一:`{preset: id}` 依 id 自掃描集合載入對應預組(id MUST 限縮在掃描到的集合,絕不轉為任意檔案路徑;未知 id 回 4xx);`{pages:[...]}` 自訂牌組以構築規則驗證(違規回 422);缺省(無牌組欄位或 `{preset:"level1"}`)為預設預組 level1。直接建立無主對局的舊端點 MUST 移除。

#### Scenario: 開局初始狀態
- **WHEN** 房間雙方到齊而建立對局
- **THEN** 狀態為先攻玩家的開始階段,雙方 MP 2、首頁魔物已在場

#### Scenario: 指定具名預組開局
- **WHEN** 建房或加入請求帶 `{preset: "<掃描到的預組 id>"}`
- **THEN** 開局後該方魔本為對應預組內容

#### Scenario: 未知預組被拒
- **WHEN** 請求帶 `{preset: "../../etc/passwd"}` 或任何不在掃描集合中的 id
- **THEN** 回應 4xx 與原因碼,不讀取任何非預組檔案,對局不建立

#### Scenario: 自訂牌組仍驗證
- **WHEN** 請求帶 `{pages:[...]}` 且違反構築規則
- **THEN** 回應 422 與構築規則原因碼

### Requirement: 指令提交
API SHALL 提供指令提交端點:以 token 鑑別玩家(payload 的 `player` 欄位 MUST 被忽略,由伺服器填入),轉交引擎;回傳引擎結果(成功=新狀態摘要+本次事件列表,均經提交者視角過濾;失敗=原因碼)。指令 MUST 逐一循序處理,同一對局不併發。

#### Scenario: 提交合法指令
- **WHEN** 回合玩家以自己的 token 提交翻頁指令
- **THEN** 回應含 PagesFlipped/MPChanged 事件與更新後(自己視角的)狀態

#### Scenario: 提交非法指令
- **WHEN** 玩家提交時機不符的指令
- **THEN** 回應 4xx 與引擎原因碼,對局狀態不變

### Requirement: 狀態快照與資訊隱藏
狀態快照 SHALL 依觀看者(player0/player1/觀戰)產生:包含渲染所需完整公開狀態(階段、行動權、雙方 MP、場面、魔本進度、戰鬥子狀態、pending 的 kind 與決策者、事件序號、雙方玩家暱稱)。對手與觀戰者的回應中,任一玩家未翻開頁的內容 MUST NOT 出現(僅頁碼/張數);翻開頁的卡片內容 MUST 只對持有者可見,對手與觀戰者僅見頁碼——**唯一例外:已宣告攻防術的「使用中頁」(攻擊宣告 `battle_in` 的攻方頁、戰鬥中 `battle` 的攻方 `attack_page` 與防方 `defense_page`)SHALL 對所有視角含卡片內容並標記 `in_use`(宣告即公開);戰鬥結束後 MUST 恢復僅頁碼**;持有者本人的視角 MAY 含自己完整魔本內容(`book`,全 32 頁順序)——此為己方隱藏資訊,規則上持有者本就已知,MUST NOT 出現在對手或觀戰者的回應中;pending 的選項細節 MUST 只對決策者可見。本機模式的 client 持有雙方 token,視為全視角(雙方 book 皆含)。

#### Scenario: 對手未翻頁內容不外洩
- **WHEN** 玩家 A 查詢狀態
- **THEN** 玩家 B 的未翻開頁僅以頁碼/張數表示,B 的 `book` 完整內容 MUST NOT 出現在 A 的回應中

#### Scenario: 己方全魔本對本人可見
- **WHEN** 玩家 A 查詢狀態
- **THEN** A 自己的 player_view 含 `book`(全 32 頁卡號),搭配 consumed_pages/pos 足以標示每頁狀態

#### Scenario: 觀戰者看不到任一方魔本內容
- **WHEN** 觀戰者查詢狀態
- **THEN** 雙方的未翻開頁與 `book` 完整內容皆不出現,僅見頁碼與公開場面

#### Scenario: 對手翻開頁不可見
- **WHEN** 玩家 A 查詢狀態且 B 無宣告中的攻防術
- **THEN** 玩家 B 的 open_pages 僅含頁碼,無卡號與費用;A 自己的 open_pages 完整

#### Scenario: 宣告中的攻擊術對對手可見
- **WHEN** 玩家 B 以第 9 頁的術宣告攻擊(battle_in 或 battle 進行中),玩家 A 查詢狀態
- **THEN** A 看到 B 的第 9 頁含卡號並標記 `in_use`;B 其餘翻開頁仍僅頁碼

#### Scenario: 防禦術同樣揭露且歸屬正確
- **WHEN** 戰鬥中防方 A 以第 5 頁宣告防禦,觀戰者查詢狀態
- **THEN** A 的第 5 頁與攻方的攻擊頁皆含卡號;攻方頁不會誤掛在防方(反之亦然)

#### Scenario: 戰鬥結束恢復保密
- **WHEN** 該場戰鬥結算完畢(battle 清空)後對手查詢狀態
- **THEN** 原使用中頁恢復僅頁碼(無卡號、無 `in_use`)

#### Scenario: 決策選項只送決策者
- **WHEN** M-011 效果等待玩家 A 從 B 的魔本挑選魔物
- **THEN** 只有 A 的視角含選項(頁碼與卡號);B 與觀戰者僅見「A 決策中」

#### Scenario: 快照可完整重繪
- **WHEN** 前端重新整理後以 token 查詢狀態
- **THEN** 回應足以完整重建該視角畫面(含行動 log 與暱稱),無需重放指令

### Requirement: 事件記錄
對局 SHALL 累積自開局以來的全部事件(含序號);API MUST 支援自指定序號起增量取得事件,且回放內容 MUST 與即時推送同樣經視角過濾:帶 viewer 標記的事件(檢視魔本/偷看頁面)只對該玩家可見,choice_required 對非決策者去除選項細節。

#### Scenario: 增量取得事件
- **WHEN** 客戶端以上次已知序號查詢事件
- **THEN** 僅回傳其後發生、且該視角可見的事件,序號遞增

#### Scenario: 檢視類事件不外洩
- **WHEN** 玩家 A 以 M-011 檢視了 B 的魔本
- **THEN** book_revealed 的卡片清單只出現在 A 的事件流;B 與觀戰者僅知檢視發生

### Requirement: WebSocket 事件推送
API SHALL 提供房間 WebSocket 端點:以 token 鑑別視角;連線即送 welcome(該視角完整快照+下一事件序號);此後每次指令產生的事件 MUST 即時推送給所有連線,內容經各自視角過濾。WS 斷線 MUST NOT 影響 HTTP 指令提交。

#### Scenario: 對手行動即時可見
- **WHEN** 玩家 A 提交指令產生事件
- **THEN** 玩家 B 與觀戰者的 WS 各自收到過濾後的事件批次,無需輪詢

#### Scenario: 重連對齊序號
- **WHEN** 玩家重建 WS 連線
- **THEN** welcome 含 next_seq,前端以序號去重,不重複顯示既有記錄

### Requirement: 預組魔本探索
API SHALL 提供 `GET /api/decks` 端點,回傳伺服器 `data/decks/` 目錄下所有預組魔本的清單(每項含 `id` 與顯示名 `name`)。顯示名 SHALL 依牌組 JSON 解析:有 `name_key` 則經 i18n 字典解析,否則用內嵌 `name`,再無則退回 `id`。清單 SHALL 於啟動時掃描並可快取;無法解析為合法牌組的檔案 MUST 被排除而不使端點失敗。

#### Scenario: 列出預組
- **WHEN** 前端請求 `GET /api/decks`
- **THEN** 回應含至少 level1 一項,每項有 `id` 與可顯示的 `name`

#### Scenario: 丟檔即現
- **WHEN** 開發者於 `data/decks/` 放入一個合法的新預組 JSON 並重啟伺服器
- **THEN** 該預組出現在 `GET /api/decks` 回應中,無需其他程式碼改動

### Requirement: 執行環境中繼資訊
API SHALL 提供 `GET /api/meta` 回傳執行環境資訊:`tunnel_url`(公開通道網址,無通道時為 null)與 `assets`(卡圖安裝狀態:`installed`、既有張數 `count`、應有張數 `expected`、建議安裝路徑 `install_dir`)。

#### Scenario: 有通道時回報網址
- **WHEN** launcher 已建立公開通道後前端請求 `GET /api/meta`
- **THEN** 回應含 `tunnel_url` 為該 https 網址

#### Scenario: 卡圖未安裝時回報狀態
- **WHEN** 卡圖目錄不存在時請求 `GET /api/meta`
- **THEN** `assets.installed` 為 false 且 `install_dir` 為建議安裝路徑

### Requirement: 卡圖靜態資源外部化
卡圖靜態路由(`/static/assets/`)SHALL 掛載自資源解析模組決定的卡圖目錄,而非寫死於前端目錄之下;開發模式下(卡圖目錄即 repo `frontend/assets/`)對外行為 SHALL 與現況等價。

#### Scenario: 外部卡圖目錄生效
- **WHEN** 卡圖解析至使用者資料夾且前端請求 `/static/assets/cards/S-001.jpg`
- **THEN** 回應該使用者資料夾中的對應圖檔

#### Scenario: 開發模式等價
- **WHEN** 開發模式下請求任一既有卡圖 URL
- **THEN** 回應與本變更前完全一致

