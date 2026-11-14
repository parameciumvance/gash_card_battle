# Tasks

## 1. 頂欄換行

- [x] 1.1 先寫瀏覽器測試(確認修改前失敗):寬度 800、1000px,日文 / 繁中 / 英文的對局畫面(有等待狀態),每個頂欄文字欄位與標題字都是單行、所有按鈕都在畫面內;1540px 時頂欄只有一行;手機 390px 時照舊(只有徽章、按鈕在畫面內)
- [x] 1.2 `style.css`:`#topbar` 一律可換行,文字欄位與標題不縮小、不在欄位內換行(≤700px 維持原規則)。1.1 通過;既有的頂欄相關瀏覽器測試照舊

## 2. 驗證與文件

- [x] 2.1 `python -m pytest tests -m "not slow and not browser" -q`;battle-ui design 補頂欄換行的做法與理由;`openspec validate topbar-wrap --strict`
- [x] 2.2 本機實際操作抽查(使用者):800px 左右(或瀏覽器縮放)日文對局畫面的頂欄(使用者確認後要求歸檔)

## Workflow follow-up

- 歸檔前依指南 §13 同步 battle-ui delta spec 與 design;在 `topbar-wrap` 分支歸檔提交,合併回 `dev`。
