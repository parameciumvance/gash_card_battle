## 1. 實作

- [x] 1.1 先寫瀏覽器測試確認修改前失敗:離開房間後首頁列出該房間並可點選返回;伺服器上不存在的房間不列出並移除記錄;已結束的對局不列出;沒有項目時不顯示;頂欄標題字(含 Enter)在牌組編輯器與對局中回到首頁,對局可再返回
- [x] 1.2 `refreshResumeRooms`、首頁區塊、`goHome` 與標題字(design D1、D2)、CSS、i18n(簡中以工具產生);1.1 與既有瀏覽器測試全過
- [x] 1.3 使用者確認

## 2. Reconciliation 與歸檔(指南 §13)

- [x] 2.1 同步 delta spec 回 `battle-ui` 主 spec
- [x] 2.2 `battle-ui/design.md`「首頁與設定頁」補返回對局與標題字
- [x] 2.3 `openspec validate --all --strict`(與既有基準相比沒有新增失敗)與 `pytest` 全過後歸檔
