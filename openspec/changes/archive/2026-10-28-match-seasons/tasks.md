# Tasks

## 1. 賽季定義與構築驗證(card-data)

- [x] 1.1 先寫測試(`tests/test_seasons.py`):卡片賽季(M-015 → 1、M-016 → 2、S-106 → 3、Ex-010 → 2、Ex-000 → 4、不在任何範圍的卡號沒有賽季);魔書賽季(四副預組依序 1、2、3、3);`validate_deck` 以第 1 賽季驗證含 M-030 的魔書回 `deck.season`、以第 3 賽季驗證 level2 通過、未指定賽季不檢查。確認在實作前失敗
- [x] 1.2 新增 `data/seasons.json`(design 決定 1 的格式與使用者給的上限)與 `gash.engine.seasons`;`validate_deck` 加可選的 `season`;1.1 通過,`tests/test_deck.py`、`tests/test_preset_decks.py` 照舊通過

## 2. 房間、NPC 與預組清單(online-room、battle-api)

- [x] 2.1 先寫 API 測試:建房指定賽季後 meta 含賽季、未指定為 3、`season=4` 回 422 `room.bad_season`;第 1 賽季建房選 level2 回 422 `deck.season`(detail 含 `season`);第 1 賽季線上房的加入者用 zeon 回 422 `deck.season` 且房間仍等待中;本機房任一方超出賽季被拒;第 2 賽季 NPC 房的候選含 zeon 回 422、候選為 level1 / level2 時建房成功;第 1 賽季未指定魔書時以 level1 建房成功;`GET /api/decks` 每項含 `season`(level1 1、level2 2、zeon 3)。確認在實作前失敗
- [x] 2.2 `CreateRoom.season`、`Room.season`、房間 meta;`_resolve_deck` 依賽季驗證(含預組);`_npc_seat` 與加入端點傳入房間賽季;`preset_list` 附 `season`;2.1 通過,`tests/test_npc_room.py`、`tests/test_custom_decks.py` 照舊通過

## 3. 牌桌(game-tables)

- [x] 3.1 先寫測試(`tests/test_tables.py`):以第 1 賽季開桌後列表含賽季 1;第 1 賽季等待中的桌子以 level2 入座回 422 `deck.season` 且桌子仍等待中;`table.taken` 含賽季;非法賽季回 422 `room.bad_season`;雙方再戰後新房賽季沿用。確認在實作前失敗
- [x] 3.2 `SitBody.season`、`_new_table_room` 帶賽季、`TableStore.view` / `table.taken` 帶出賽季;3.1 通過
- [x] 3.3 `python -m pytest tests -m "not slow and not browser" -q` 通過

## 4. 設定頁與牌桌頁(battle-ui)

- [x] 4.1 前端載入 `/data/seasons.json`,`decks.js` 提供 `cardSeason` / `deckSeason`
- [x] 4.2 與朋友對戰建立模式、NPC、本機設定頁與牌桌頁開桌設定加入賽季選單(缺省 3,記在瀏覽器;加入模式不顯示),建房 / 開桌請求帶 `season`;四語字串
- [x] 4.3 牌組選單依賽季禁用並標示「第 N 賽季起」;NPC「隨機」候選只含賽季內的牌組;切換賽季使選中的牌組不可用時回到 level1;記住的牌組超出賽季時回到缺省
- [x] 4.4 牌桌頁顯示各桌賽季、所選牌組不符等待中牌桌時禁用「對戰」並說明、衝突確認顯示賽季;`deck.season` 錯誤以房間賽季組成訊息(加入模式與牌桌頁),停留原頁且保留已填內容
- [x] 4.5 瀏覽器測試:NPC 設定頁選第 1 賽季時 level2 / gash-nakama / zeon 禁用且標示正確、隨機候選只含賽季內牌組(檢查送出的請求)、切換賽季回到 level1、賽季在重新整理後被記住;以房號用 zeon 加入第 1 賽季房間時顯示賽季訊息並留在加入模式;牌桌頁的賽季顯示、「對戰」禁用與衝突確認的賽季。既有的設定頁與牌桌頁測試(`test_landing_ui.py`、`test_tables_ui.py` 等)照舊通過

## 5. 構築器(deck-builder)

- [x] 5.1 卡池篩選列加入賽季按鈕與網格(全部、第 1~3 賽季,單選、累計語意,與其他篩選取交集,構築器與金手指共用);魔書名稱旁的「第 N 賽季起」標示(空魔書不顯示、不影響合法性提示);四語字串
- [x] 5.2 瀏覽器測試(`tests/test_pool_filters_ui.py` 等):選第 2 賽季時卡池含 M-001 與 M-030、不含 M-040,按鈕顯示所選賽季;類型「魔」+ 第 1 賽季只剩 M-001~M-015;同時只展開一組仍成立;放入 M-030 後標示由第 1 變第 2 賽季起且沒有新的違規;窄螢幕篩選列沒有頁面水平捲動
- [x] 5.3 `python -m pytest tests -m "not slow" -q` 通過

## 6. Reconciliation(指南 §13)

- [x] 6.1 同步 delta spec 到主 spec(`card-data`、`online-room`、`game-tables`、`battle-api`、`battle-ui`、`deck-builder`);`openspec validate --all --strict` 通過(既有 7 個說明過長的警告不變,沒有新增)
- [x] 6.2 更新 capability design:`card-data/design.md`(賽季定義檔與理由)、`online-room/design.md`(房間賽季、預組也依賽季驗證、NPC 候選不默默剔除)、`game-tables/design.md`(開桌選賽季、再戰沿用)、`battle-ui/design.md`(賽季選單、以房號加入用錯誤訊息告知賽季)、`deck-builder/design.md`(賽季篩選的累計語意,使用者確認);`openspec/capability-map.md` 的 `card-data`、`online-room` 責任描述補上賽季
- [x] 6.3 README 的對戰說明補上賽季;`todo.md` 移除「賽季選擇」(不提交 `todo.md`)
- [x] 6.4 全套 `python -m pytest tests -q` 通過

## Workflow follow-up

- 依使用者指示歸檔、提交並合併
- 後續 change:第三賽季其餘 95 張卡的資料(屆時決定 Ex 卡號寫法並同步 `data/seasons.json`),再分批實作效果
