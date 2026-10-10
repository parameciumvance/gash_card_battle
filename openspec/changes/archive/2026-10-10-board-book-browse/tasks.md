## 1. 先寫測試

- [x] 1.1 新增瀏覽器測試 `tests/test_book_browse_ui.py`(本機測試模式),確認修改前失敗:目前頁時「回到目前頁」停用;按右鍵兩次顯示 pos+4、pos+5 兩頁的卡(對照 `S.players[p].book`),按鈕變亮,按下回到目前頁;從 2–3 往左到只有第 1 頁的對頁時左鍵停用,往右到只有第 32 頁時右鍵停用;已放到場上的頁顯示卡背;翻閱中點卡開啟沒有行動按鈕的放大檢視;翻閱中自己的魔書被翻動(開始階段翻頁)時回到新的目前頁,對手行動或 MP 改變時維持;線上視角(`SESSION.viewer` 設為一方)時對手的魔書區沒有左右鍵;鍵盤 → / Home / Esc 生效,放大檢視開著時 → 不生效,本機模式 → 翻的是行動中一方的魔書

## 2. 實作

- [x] 2.1 翻閱狀態 `BOOK_BROWSE` 與 `renderBookBlock` 的唯讀頁位、左右鍵、「回到目前頁」(design D1、D2、D3);1.1 的盤面情境通過,`pytest tests/test_in_use_reveal.py tests/test_choice_ui.py tests/test_spotlight_ui.py` 不受影響
- [x] 2.2 自己的魔書被翻動時,動畫前先回到目前頁(design D4);1.1 的翻動情境通過,翻頁動畫測試(`tests/test_spotlight_ui.py` 等)不受影響
- [x] 2.3 鍵盤操作(design D5);1.1 的鍵盤情境通過
- [x] 2.4 i18n 與樣式(design D3、D6),簡中以 `tools/build_zh_cn.py` 產生;`pytest tests/test_i18n_languages.py` 全過;寬螢幕與窄螢幕截圖確認按鈕不遮住卡名與頁碼
- [x] 2.5 使用者在瀏覽器實際操作確認

## 3. Reconciliation 與歸檔(指南 §13)

- [x] 3.1 同步 delta spec 回 `battle-ui` 主 spec
- [x] 3.2 Reconcile affected capability design and rationale:`battle-ui/design.md` 新增「場上魔書翻閱」一節(狀態、自動回到目前頁、動畫前回位、鍵盤目標與排除條件)
- [x] 3.3 確認 capability map 是否需要更新(`battle-ui` 責任描述若需補「魔書翻閱」則更新)
- [x] 3.4 `openspec validate --all --strict`(與既有基準相比沒有新增失敗)與 `pytest` 全過後歸檔
