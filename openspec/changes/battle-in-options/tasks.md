# Tasks

## 1. 戰鬥開始確認的選項

- [x] 1.1 先寫瀏覽器測試(確認修改前失敗):戰鬥開始確認時有「進入戰鬥」(附註「接著宣告防禦或不防禦」)與「進入戰鬥,不防禦」;按後者送出進入戰鬥,之後同一場戰鬥的防禦步驟自動送出不防禦;按「進入戰鬥」時防禦步驟照常詢問;下一場戰鬥不沿用;提示文字;三語用語
- [x] 1.2 實作(行動欄按鈕、`PRESET_NO_DEFENSE`、四語文字)。1.1 通過

## 2. 用語

- [x] 2.1 「迎戰」改為規則術語:`ui.allow_battle`、附註、提示、`hint.allow_battle`、`error.battle_in.invalid`、規則頁(三語,簡中以工具產生)、引擎錯誤訊息文字;`tests/test_turn_dial_ui.py` 依新文字更新;`grep` 確認介面文字不再有「迎戰」(更新內容的歷史除外)

## 3. 驗證與文件

- [x] 3.1 快速測試組與相關瀏覽器測試通過;battle-ui design 補做法;`openspec validate battle-in-options --strict`
- [ ] 3.2 本機實際操作抽查(使用者)

## Workflow follow-up

- 歸檔前同步 battle-ui delta spec 與 design;在 `battle-in-options` 分支歸檔提交,合併回 `dev`。
