## RENAMED Requirements

- FROM: `### Requirement: 金手指端點僅限本機模式`
- TO: `### Requirement: 金手指端點僅限本機房與 NPC 房`

## MODIFIED Requirements

### Requirement: 金手指端點僅限本機房與 NPC 房
API SHALL 提供 `GET`/`POST /api/rooms/{code}/debug-state`,僅 `room.mode` 為 `local` 或 `npc` 時開放;`online` 房請求 MUST 回 403;觀戰 token 的請求 MUST 回 403。`GET` SHALL 回傳雙方的 `book`(32 頁卡號陣列)與 `mp`(NPC 房亦含 NPC 的魔本)。`POST` SHALL 接受同構的 `{players: [{book, mp}, {book, mp}]}` JSON:`book` 長度 MUST 為 32,每個卡號 MUST 存在於卡片資料庫,否則回 4xx 且不套用;驗證通過後取代對應玩家的 `book`/`mp`。

#### Scenario: 本機房可讀取 book/mp
- **WHEN** 本機房間的 client 請求 `GET /api/rooms/{code}/debug-state`
- **THEN** 回應含雙方完整 `book`(全 32 頁卡號)與 `mp`

#### Scenario: NPC 房可讀寫 book/mp
- **WHEN** NPC 房的玩家請求 `GET`,修改 NPC 某頁卡號後 `POST`
- **THEN** `GET` 回應含雙方完整 `book` 與 `mp`;套用後 NPC 的 `book` 對應頁更新

#### Scenario: 線上房請求被拒
- **WHEN** `online` 房間的 client(任一身分)請求 `GET` 或 `POST /api/rooms/{code}/debug-state`
- **THEN** 回應 403,對局狀態不變

#### Scenario: 觀戰者請求被拒
- **WHEN** 本機房或 NPC 房的觀戰 token 請求 `GET` 或 `POST /api/rooms/{code}/debug-state`
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
