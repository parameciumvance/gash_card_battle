## 1. 伺服器

- [x] 1.1 先寫 API 測試確認修改前失敗:有公告檔時回傳公告;刪除後回傳 null;`until` 已過回傳 null;JSON 錯誤 / 缺 `message` 回傳 null 且 200
- [x] 1.2 `GET /api/announcement`(design D1);1.1 全過

## 2. 前端

- [x] 2.1 先寫瀏覽器測試確認修改前失敗:有公告時首頁與對局畫面顯示橫幅、依語言選訊息、關閉後重新整理不再顯示、新 `id` 再顯示、撤下後移除
- [x] 2.2 `#announcement` 橫幅、定期查詢、關閉記錄(design D2)、CSS、i18n(簡中以工具產生);2.1 與既有瀏覽器測試全過
- [x] 2.3 README 說明發布與撤下公告
- [x] 2.4 使用者確認

## 3. Reconciliation 與歸檔(指南 §13)

- [x] 3.1 同步 delta spec 回 `battle-api`、`battle-ui` 主 spec
- [x] 3.2 `battle-api/design.md`、`battle-ui/design.md` 補公告的設計;capability map 的 battle-ui 說明補「維護公告」
- [x] 3.3 `openspec validate --all --strict`(與既有基準相比沒有新增失敗)與 `pytest` 全過後歸檔
