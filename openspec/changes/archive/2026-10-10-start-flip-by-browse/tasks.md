## 1. 前端

- [x] 1.1 先寫瀏覽器測試,確認修改前失敗:開始階段沒有翻閱時行動欄只有「不翻頁」;按右鍵 1 / 2 / 3 次分別只有「翻 1 / 2 / 3 張(MP +…)」;按「翻 2 張」後實際翻 2 張、魔書區回到新的目前頁;往前翻閱或往後 4 次時沒有翻頁按鈕、顯示提示含最多張數;魔書剩餘只能翻 1 張時,往後翻閱到第 32 頁為「翻 1 張」且右鍵停用(張數與翻閱都以第 32 頁為界)
- [x] 1.2 `renderActionBar` 開始階段改為依翻閱對頁顯示單一按鈕或提示(design D1、D2),i18n(design D3,簡中以工具產生);1.1 與 `pytest tests/test_book_browse_ui.py tests/test_timing_ui.py tests/test_i18n_languages.py` 全過
- [x] 1.3 使用者在瀏覽器實際操作確認

## 2. Reconciliation 與歸檔(指南 §13)

- [x] 2.1 同步 delta spec 回 `battle-ui` 主 spec
- [x] 2.2 Reconcile affected capability design:`battle-ui/design.md`「場上魔書翻閱」補充開始階段的對應方式
- [x] 2.3 確認 capability map 不需更新;`openspec validate --all --strict`(與既有基準相比沒有新增失敗)與 `pytest` 全過後歸檔
