## ADDED Requirements

### Requirement: 維護公告
API SHALL 提供 `GET /api/announcement`,回傳目前的公告:`{"announcement": null}` 或 `{"announcement": {"id", "message", "until"}}`。公告來自卡圖目錄(`GASH_ASSETS_DIR`)下的 `announcement.json`,每次請求即時讀取,編輯檔案即可發布或撤下,MUST NOT 需要重新部署或重啟。`message` 為語言代碼對應文字的物件;`until`(ISO 8601,可省略)已過時 SHALL 回傳 null。檔案不存在、格式錯誤、缺少 `id` 或 `message` 時 SHALL 回傳 null,MUST NOT 讓請求失敗。

#### Scenario: 發布公告
- **WHEN** 卡圖目錄下有 `{"id": "m1", "message": {"zh-TW": "今晚維護"}}` 的公告檔
- **THEN** `GET /api/announcement` 回傳該公告

#### Scenario: 撤下公告
- **WHEN** 公告檔被刪除
- **THEN** 下一次 `GET /api/announcement` 回傳 null,不需重啟

#### Scenario: 過期的公告
- **WHEN** 公告檔的 `until` 早於現在
- **THEN** 回傳 null

#### Scenario: 格式錯誤
- **WHEN** 公告檔不是合法的 JSON 或缺少 `message`
- **THEN** 回傳 null,狀態碼 200
