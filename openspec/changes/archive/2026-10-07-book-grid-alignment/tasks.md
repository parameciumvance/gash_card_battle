## 1. 先寫測試

- [x] 1.1 瀏覽器測試:查閱魔本同一列的卡片等高;構築器(桌面與手機)與金手指網格的各對頁欄位上下對齊,P1 靠第一欄右側、P32 在最後一列第一欄靠左;已上場的卡背不超出對頁框;金手指同一對頁兩張卡等高。確認修改前失敗

## 2. 實作

- [x] 2.1 `style.css`:三個網格改 grid、`--slot-w`、單頁欄位對齊(design D1)
- [x] 2.2 查閱魔本卡片填滿列高,已上場頁的卡背同寬;構築器與金手指的卡片填滿頁位(design D2)
- [x] 2.3 截圖確認桌面與手機的查閱魔本、構築器、金手指

## 3. Reconciliation 與歸檔(指南 §13;主 spec 手動同步,歸檔用 `--skip-specs`)

- [x] 3.1 同步 delta spec 回 `battle-ui`、`deck-builder` 主 spec
- [x] 3.2 Reconcile affected capability design and rationale:`battle-ui/design.md` 補魔本網格排版;`deck-builder` 的 design 尚未建立(capability map 標 Not documented),排版規則記在 `battle-ui/design.md` 並註明構築器共用
- [x] 3.3 `openspec validate --all --strict`、相關測試全過後歸檔
