## 1. 實作

- [x] 1.1 先寫瀏覽器測試確認修改前失敗:連點有卡頁兩次卡仍在且取消選取;選中有卡頁顯示「移除」按鈕,按下移除且仍選中該頁;選中後按 Delete 移除;空頁、未選中的頁沒有移除按鈕;金手指頁位沒有移除按鈕
- [x] 1.2 `togglePage` 與 `bookPageSlotEl` 的 `remove`(design D1)、CSS、i18n(簡中以工具產生);1.1 與既有瀏覽器測試全過
- [x] 1.3 使用者確認

## 2. Reconciliation 與歸檔(指南 §13)

- [x] 2.1 同步 delta spec 回 `deck-builder` 主 spec
- [x] 2.2 `battle-ui/design.md` 卡片元件段落(頁位共用元件)補移除按鈕
- [x] 2.3 `openspec validate --all --strict`(與既有基準相比沒有新增失敗)與 `pytest` 全過後歸檔
