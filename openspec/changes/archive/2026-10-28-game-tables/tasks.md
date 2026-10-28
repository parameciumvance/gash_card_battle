# Tasks

## 1. 牌桌後端

- [x] 1.1 先寫 API 測試(`tests/test_tables.py`,以 TestClient):列表內容(5 桌、狀態、暱稱、計時、等待秒數、觀戰連結、不含 token);開桌;加入等待中的桌子並開局;以為空桌但已有人開桌回 409 `table.taken` 與實際設定;不計時 / 非法計時回 422;牌組違規回 422 且桌子不變;對戰中入座回 409 `table.busy`;以房號加入牌桌房回 409 `room.table_only`。確認修正前失敗
- [x] 1.2 牌桌模組:5 張牌桌的狀態、`GET /api/tables`、入座端點、離開端點;`online-room` 的加入端點拒絕牌桌房;1.1 通過
- [x] 1.3 先寫測試再實作:等待中斷線 60 秒釋放(10 秒內重連維持)、主動離開立即釋放;對局結束轉為結束後選擇中;再戰 / 離開的四種結果(雙方再戰、一方離開、雙方離開、2 分鐘未選或斷線 60 秒視為離開);新房間以 `table_moved` 通知相關連線(各自新 token);閒置回收時空出牌桌。時間以可注入的時鐘或直接呼叫檢查函式驗證,不實際等待
- [x] 1.4 `python -m pytest tests -q -m "not slow"` 除既有的卡圖相關失敗外通過

## 2. 前端

- [x] 2.1 首頁「牌桌」入口(位於「與朋友對戰」之前);牌桌頁:5 桌狀態、每 5 秒更新、暱稱 / 牌組 / 開桌計時欄位(記在瀏覽器)、入座、對戰、觀戰、返回首頁;四語字串
- [x] 2.2 入座衝突:收到 `table.taken` 時顯示實際開桌者與計時,確認後以加入方入座;`table.busy` 顯示錯誤並更新列表
- [x] 2.3 等待畫面的「離開」;對局結束畫面的「再戰 / 離開」、對方狀態與剩餘時間;收到 `table_moved` 時以新 token 進入新房間(觀戰者跟著換到新房)
- [x] 2.4 瀏覽器測試(`tests/test_tables_ui.py`):首頁入口順序、牌桌頁狀態顯示、開桌後離開、衝突確認、雙方再戰自動進入新局、對方離開後成為開桌者、觀戰入口;既有首頁測試(`test_landing_ui.py` 等)通過
- [x] 2.5 README 的線上對戰說明補上牌桌

## 3. Reconciliation 與歸檔(指南 §13)

- [x] 3.1 同步 delta spec(新增 `game-tables`,修改 `online-room`、`battle-ui`);`openspec validate --all --strict` 通過且沒有新增說明過長的提示
- [x] 3.2 新增 `openspec/specs/game-tables/design.md`(本 change 的決定 1~6);更新 `online-room/design.md`(牌桌房、`table_moved`)、`battle-ui/design.md`(牌桌頁、結束後選擇);`openspec/capability-map.md` 新增 `game-tables`(責任、覆蓋程度、與 `online-room` 的關係)
- [x] 3.3 `todo.md` 移除「房間自由加入,牌桌」
- [x] 3.4 依使用者指示歸檔並提交
