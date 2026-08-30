## ADDED Requirements

### Requirement: 金手指端點僅限本機模式
API SHALL 提供 `GET`/`POST /api/rooms/{code}/debug-state`,僅 `room.mode == "local"` 開放;`online` 房請求 MUST 回 403。`GET` SHALL 回傳雙方的 `book`(32 頁卡號陣列)與 `mp`。`POST` SHALL 接受同構的 `{players: [{book, mp}, {book, mp}]}` JSON:`book` 長度 MUST 為 32,每個卡號 MUST 存在於卡片資料庫,否則回 4xx 且不套用;驗證通過後取代對應玩家的 `book`/`mp`。

#### Scenario: 本機房可讀取 book/mp
- **WHEN** 本機房間的 client 請求 `GET /api/rooms/{code}/debug-state`
- **THEN** 回應含雙方完整 `book`(全 32 頁卡號)與 `mp`

#### Scenario: 線上房請求被拒
- **WHEN** `online` 房間的 client(任一身分)請求 `GET` 或 `POST /api/rooms/{code}/debug-state`
- **THEN** 回應 403,對局狀態不變

#### Scenario: 套用編輯後的 book/mp
- **WHEN** 本機房 client 對 `POST /api/rooms/{code}/debug-state` 送出修改過某頁卡號與 MP 的 JSON
- **THEN** 該玩家的 `book` 對應頁與 `mp` 更新為送出的值,後續查詢反映新狀態

#### Scenario: 不存在的卡號被拒
- **WHEN** `POST` 的 `book` 中含有不存在於卡片資料庫的卡號
- **THEN** 回應 4xx 與原因碼,對局狀態不變

#### Scenario: book 長度不符被拒
- **WHEN** `POST` 的某玩家 `book` 陣列長度不是 32
- **THEN** 回應 4xx 與原因碼,對局狀態不變

### Requirement: 金手指變更留痕與同步
`POST /api/rooms/{code}/debug-state` 成功套用後,SHALL 於事件流插入一筆 `cheat_applied` 標記事件(不含變更前後的欄位級差異),並沿用既有的房間廣播機制,將套用後的完整狀態快照推送給該房間所有連線(雙方玩家與觀戰者)。

#### Scenario: 行動記錄可見金手指介入
- **WHEN** 金手指套用成功
- **THEN** 事件流中出現一筆 `cheat_applied` 事件,序號遞增,與其他事件走同一份記錄

#### Scenario: 連線者即時看到套用後狀態
- **WHEN** 金手指套用成功且該房間有另一個 WebSocket 連線(如觀戰者)
- **THEN** 該連線收到推播,內容反映套用後的最新狀態,無需手動重新整理
