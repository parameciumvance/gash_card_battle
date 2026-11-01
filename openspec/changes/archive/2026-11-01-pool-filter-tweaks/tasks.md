## 1. 測試先行

- [x] 1.1 `tests/test_pool_filters_ui.py`:再點一次取消(魔物、產品、賽季)、「全部」按鈕高度、Ex 卡與 PR 並排、選 Ex 卡只顯示 Ex- 開頭的卡;確認修改前失敗

## 2. 實作

- [x] 2.1 `frontend/app.js`:點已選取的項目時取消選擇;產品 `ex` 以卡號前綴篩選
- [x] 2.2 `frontend/style.css`:「全部」按鈕放大
- [x] 2.3 `frontend/pool-filters.json` 最後一排 `["ex", "promo"]`;產生 `frontend/products/ex.webp`(比照 promo.webp 的配色),更新 `frontend/products/README.md`
- [x] 2.4 四語 `product.ex`(「Ex 卡」),`tools/build_zh_cn.py` 產生簡中

## 3. 驗證

- [x] 3.1 `tests/test_pool_filters_ui.py` 與相關瀏覽器測試、快速測試組通過;`openspec validate --all --strict` 與基準相比沒有新增失敗
- [x] 3.2 本機實際操作抽查(使用者)

## 4. Reconciliation(指南 §13)

- [x] 4.1 同步 delta spec 到 `openspec/specs/deck-builder/spec.md`
- [x] 4.2 `openspec/specs/deck-builder/design.md` 記錄 Ex 卡為依卡號前綴的虛擬產品
