## MODIFIED Requirements

### Requirement: 預組魔本探索
API SHALL 提供 `GET /api/decks` 端點,回傳伺服器 `data/decks/` 目錄下所有預組魔本的清單(每項含 `id`、顯示名 `name`,以及牌組 JSON 有 `name_key` 時的 `name_key`)。顯示名 SHALL 依牌組 JSON 解析:有 `name_key` 則經中文 i18n 字典解析,否則用內嵌 `name`,再無則退回 `id`。前端 SHALL 以 `name_key` 依目前語言解析顯示名,字典中沒有時使用 `name`。清單 SHALL 於啟動時掃描並可快取;無法解析為合法牌組的檔案 MUST 被排除而不使端點失敗。

#### Scenario: 列出預組
- **WHEN** 前端請求 `GET /api/decks`
- **THEN** 回應含至少 level1 一項,每項有 `id` 與可顯示的 `name`;level1 另含 `name_key`

#### Scenario: 丟檔即現
- **WHEN** 開發者於 `data/decks/` 放入一個合法的新預組 JSON 並重啟伺服器
- **THEN** 該預組出現在 `GET /api/decks` 回應中,無需其他程式碼改動

#### Scenario: 預組名稱依語言
- **WHEN** 語言為英文,玩家打開 NPC 對戰設定頁的牌組選單
- **THEN** level1 以英文字典中 `deck.level1` 的名稱顯示
