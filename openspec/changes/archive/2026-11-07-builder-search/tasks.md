# Tasks

## 1. 卡池文字搜尋

- [x] 1.1 先寫瀏覽器測試(確認修改前失敗):構築器依中文卡名、日文原名、卡號(含省略連字號、全形)、效果文搜尋;與類型篩選同時套用、清空回復;搜尋不改變魔書;金手指卡池同樣可搜尋;Esc 清空不關閉金手指視窗;四語提示文字
- [x] 1.2 實作(`fquery`、比對字串與 `normalize`、搜尋框、四語文字、樣式)。1.1 通過;`tests/test_pool_filters_ui.py`、`tests/test_builder_card_info_ui.py`、金手指相關瀏覽器測試照舊

## 2. 驗證與文件

- [x] 2.1 快速測試組通過;deck-builder design 補搜尋的做法;`openspec validate builder-search --strict`
- [x] 2.2 本機實際操作抽查(使用者)(使用者確認沒問題)

## Workflow follow-up

- 歸檔前同步 deck-builder delta spec 與 design;在 `builder-search` 分支歸檔提交,合併回 `dev`。
