## Why

目前雙方只能共用 level1 預組魔本 — 構築(這遊戲的核心樂趣之一)完全缺席,且同牌組對戰下「對手魔本內容未知」的資訊設計形同虛設(背牌表即全知)。需要一個貼合本遊戲特性的構築器:魔本構築不是選 32 張卡,而是**排版 32 頁**(頁位、對頁搭配、中級/上級頁數限制、末頁費 0 都是戰術),並讓玩家能儲存、分享、帶進對戰。

## What Changes

- 新增牌組構築器(前端新視圖):卡池瀏覽(67 張,依類型/對應魔物/收錄產品篩選)+ 16 對頁網格編輯;點選放卡、拖拉頁位互換;從 level1 或已存牌組複製起手;即時顯示七條構築規則的違規提示。
- 新增牌組儲存:瀏覽器 localStorage(`{id, name, pages[32], updated_at}` 清單);**伺服器不儲存牌組**(與無帳號架構一致)。非法牌組可存檔(標記不合法),但不能帶進對戰。
- 新增牌組匯出/匯入:單行文字碼(`gash1:` + 32 卡號逗號串),可備份、可貼給朋友。
- 對戰整合:建房、加入、本機開局的請求新增 `deck` 欄位(`{"preset": "level1"}` 或 `{"pages": [...]}`);伺服器以既有 `validate_deck` 做最終裁決(防改造 client 送非法牌組),`_start_game` 改以雙方各自的牌組呼叫 `new_game(decks=...)`。
- 首頁新增「牌組構築」入口;建房/加入/本機流程加牌組選擇(預設 level1)。
- 引擎(`game-engine`/`card-effects`)零改動:`new_game` 本就支援雙方不同牌組,`validate_deck` 重用。卡片資料抽取補存收錄產品(Sets)欄供產品篩選。

## Capabilities

### New Capabilities
- `deck-builder`: 構築器編輯(對頁網格、放卡/移除/拖拉互換、複製起手)、即時合法性提示、localStorage 儲存管理、文字碼匯出/匯入。

### Modified Capabilities
- `online-room`: 建房與加入請求攜帶牌組;伺服器逐一驗證構築合法性後才開局;本機房雙方各選牌組。
- `battle-ui`: 首頁新增構築器入口;建房/加入/本機流程加入牌組選擇。
- `card-data`: 抽取保留收錄產品(Sets)欄,供構築器產品篩選。

## Impact

- 受影響程式碼:`frontend/`(構築器視圖、牌組儲存/匯出匯入、開局選牌組)、`src/gash/api/`(create/join 的 deck 參數與驗證、`_start_game` 雙牌組)。
- `src/gash/engine/` 不變更;`data/decks/level1.json` 續作預組來源;`tools/extract_cards.py` 補存 Sets 欄並重產 cards.json。
- 新增相依:無。
- API 相容性:`deck` 欄位可選,缺省即 level1(舊 client 行為不變,非 BREAKING)。
