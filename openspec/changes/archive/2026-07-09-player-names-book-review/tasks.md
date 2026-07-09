## 1. 後端 — 玩家暱稱

- [x] 1.1 `Room` 加 `names: [None, None]`;`RoomStore.create`/`join` 接受 name 參數並設對應 index
- [x] 1.2 `_clean_name()`:strip、移除控制字元、限長 16、空→None;於 API 邊界套用
- [x] 1.3 `CreateRoom` 加 `name`(建房者)與本機房 `names:[n0,n1]`、`JoinBody` 加 `name`;接線到 store
- [x] 1.4 `_room_meta` 送 `names: [names[0], names[1]]`

## 2. 後端 — 己方全魔本進快照

- [x] 2.1 `_player_view`:`can_see_player(viewer,p)` 時附 `book: list(ps.book)`;否則不含
- [x] 2.2 雙視角測試:自己有 book、對手無、觀戰雙方皆無;既有資訊隱藏測試回歸

## 3. 前端 — 暱稱

- [x] 3.1 開局面板加暱稱 `<input maxlength=16>`(本機兩格/建房一格/加入一格),送出併入 body
- [x] 3.2 `pname(p)` 改寫:優先 `R.names[p]`,否則預設;localStorage `gash-nick` 記憶與預填
- [x] 3.3 i18n 新增暱稱欄位標籤/placeholder 鍵

## 4. 前端 — 查閱己方魔本

- [x] 4.1 己方 `pz-head` 加「查閱魔本」按鈕(僅 `iControl(p)` 且該視角有 `book` 時顯示)
- [x] 4.2 overlay 對頁網格(16 spread)渲染全 32 頁;標示當前翻開/已離場/已用術頁;純唯讀可開關
- [x] 4.3 樣式(index.html overlay 容器 + style.css)、i18n 按鈕/標題鍵

## 5. 驗證

- [x] 5.1 後端:暱稱清理(截斷/控制字元/空→預設)、meta 含 names、全量 pytest 綠
- [x] 5.2 前端 E2E:自訂暱稱端到端顯示於盤面/記錄、查閱魔本開啟顯示 32 頁且標示正確、對手/觀戰無查閱入口且快照不含他方 book、無 JS 錯誤、截圖抽查
