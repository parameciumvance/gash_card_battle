## MODIFIED Requirements

### Requirement: 首頁入口
UI SHALL 提供首頁入口:本機測試模式(即開即玩,等同 v1;雙方全視角,附金手指狀態編輯面板)、建立房間(選擇計時選項,顯示房號/加入連結/觀戰連結供分享)、加入房間(輸入房號或經 join_url 直達)、牌組構築(開啟構築器視圖)。本機、建房與加入流程 SHALL 提供牌組選擇:**由 `GET /api/decks` 動態取得的所有預組** + 本機儲存的合法牌組(不合法牌組顯示為禁用),缺省為 level1。選擇預組時 SHALL 以 `{preset: id}` 送出。進入對局後 URL SHALL 可直接分享重入(token 存於本機)。

#### Scenario: 動態列出預組
- **WHEN** 使用者開啟任一入口的牌組選擇下拉
- **THEN** 選單含 `GET /api/decks` 回傳的所有預組,以及本機合法自訂牌組

## ADDED Requirements

### Requirement: 金手指面板
本機測試模式的對局畫面 SHALL 提供一個金手指面板(僅 `mode=="local"` 呈現,線上/觀戰模式 MUST NOT 顯示):雙方各一個文字框(顯示/編輯該玩家 `book` 的 32 項卡號 JSON 陣列,來自 `GET /api/rooms/{code}/debug-state`)搭配一個 MP 數字輸入框、「套用」送出編輯後內容至 `POST` 同端點、「重新整理」重新取得目前狀態覆蓋面板內容。套用失敗(如 JSON 格式錯誤、卡號不存在、伺服器回應非 2xx)時 SHALL 顯示錯誤訊息,不清空使用者已編輯的內容。

#### Scenario: 編輯並套用 MP
- **WHEN** 使用者在金手指面板修改某方的 MP 數字輸入框並按「套用」
- **THEN** 面板顯示套用成功,盤面隨即反映新的 MP 值

#### Scenario: 編輯並套用 book
- **WHEN** 使用者在金手指面板修改某方 book 文字框中某一項卡號並按「套用」
- **THEN** 面板顯示套用成功,該玩家對應頁翻開時呈現新卡號

#### Scenario: 卡號不存在不清空編輯內容
- **WHEN** 使用者送出的 book 陣列含不存在的卡號
- **THEN** 面板顯示錯誤訊息,文字框仍保留使用者原本輸入的內容供修正
