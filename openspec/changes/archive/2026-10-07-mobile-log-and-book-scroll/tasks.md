## 1. 先寫測試

- [x] 1.1 瀏覽器測試(窄螢幕 390×844):收合時顯示最新 4 條且頁籤只有標題;展開後面板為 45vh、最新記錄可見、盤面高度不為 0、整頁不捲動;查閱魔本開啟時當前頁在可見範圍內且標題列固定在上緣;開啟期間重繪不改變捲動位置。確認修改前失敗

## 2. 實作

- [x] 2.1 `style.css`:窄螢幕抽屜 `min-height: 0`、收合時顯示最後 4 條單行(design D1、D2)
- [x] 2.2 `app.js`:`updateLogTab` 頁籤只顯示標題;`showBookReview` 開啟時捲到當前頁、重繪時保留位置(design D2、D3);`#book-review-head` 固定在上緣
- [x] 2.3 截圖確認手機收合 / 展開與查閱魔本

## 3. Reconciliation 與歸檔(指南 §13;主 spec 已手動同步,歸檔用 `--skip-specs`)

- [x] 3.1 同步 delta spec 回 `battle-ui` 主 spec
- [x] 3.2 Reconcile affected capability design and rationale:`battle-ui/design.md` 補記錄抽屜與查閱魔本的捲動
- [x] 3.3 `openspec validate --all --strict`、相關測試全過後歸檔
