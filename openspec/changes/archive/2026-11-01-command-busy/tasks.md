# Tasks

## 1. 測試先行

- [x] 1.1 瀏覽器測試(在瀏覽器內包 `fetch` 延遲;Playwright route 中 sleep 會卡住驅動):以 route 延遲 `/commands` 回應;送出後行動欄按鈕不可點、再點不會送出第二個請求;超過 200 毫秒出現「處理中…」;回應後消失並可再操作;回應失敗時也恢復;回應很快時不出現。確認修改前失敗

## 2. 實作

- [x] 2.1 `send()` 的送出中狀態與 `body.sending`(D1),CSS
- [x] 2.2 延遲顯示「處理中…」(D2),四語

## 3. 驗證

- [x] 3.1 快速測試組通過;全部非 slow 的瀏覽器測試(365 項)通過,其中 `test_cheat_editor` 與 `test_pool_filters_ui` 各一項在機器負載高時偶發逾時,單獨在修改前後各重跑都通過(與本次無關);`openspec validate command-busy --strict` 通過
- [x] 3.2 本機實際操作抽查(使用者)

## 4. Reconciliation(指南 §13)

- [x] 4.1 同步 battle-ui 主 spec 與 design
