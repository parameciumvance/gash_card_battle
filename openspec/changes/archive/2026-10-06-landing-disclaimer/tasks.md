## 1. 先寫測試

- [x] 1.1 瀏覽器測試:首頁顯示免責聲明兩句,意見回報的名稱與入口一致且不是連結;進入設定頁後不顯示。確認修改前失敗

## 2. 實作

- [x] 2.1 `#landing-disclaimer`、i18n 三種語言、樣式(design D1、D2)
- [x] 2.2 截圖確認桌面與手機
- [x] 2.3 README 開頭放同樣的聲明(design D3)

## 3. Reconciliation 與歸檔(指南 §13)

- [x] 3.1 同步 delta spec 回 `battle-ui` 主 spec
- [x] 3.2 Reconcile affected capability design and rationale:`battle-ui/design.md` 的「首頁與設定頁」補免責聲明
- [x] 3.3 `openspec validate --all --strict`、相關測試全過後歸檔
