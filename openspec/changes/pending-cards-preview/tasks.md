# Tasks

## 1. 構築器卡池顯示尚未開放的卡

- [x] 1.1 先寫瀏覽器測試並確認在修改前失敗:
  - 構築器卡池有 M-070,帶尚未開放的樣式與無障礙名稱。
  - 點選、Enter 都不會放進魔書,並出現提示;詳情按鈕開啟放大檢視。
  - 已開放的 M-001 照常放進魔書,沒有尚未開放的樣式。
- [x] 1.2 實作(design D1):`renderCardPool` 加參數決定是否含尚未開放的卡;構築器的點選改為提示;樣式與四語 i18n(標示、提示)。1.1 通過。(實作紀錄:不設 `aria-disabled`,它會連帶停用卡片內的詳情按鈕,design D1)

## 2. 產品網格與魔物網格

- [x] 2.1 先寫瀏覽器測試並確認在修改前失敗:
  - 構築器的產品網格分 5 排,含 LEVEL:4 等新產品;選 LEVEL:4 後卡池列出的卡都是尚未開放的樣式。
  - 構築器的魔物網格有只含尚未開放卡片的家族(如バランシャ)。
  - 金手指的產品網格與卡池照舊不含尚未開放的卡(維持現狀的測試)。
- [x] 2.2 實作(design D2、D3):`mamodoFilterItems`、`productFilterRows` 加同樣的參數。2.1 通過;既有「新產品在卡片開放前不列出」的測試改為金手指的版本。(實作紀錄:以舊行為為準的既有測試跟著改為新行為——`test_pool_filters_ui.py` 的預期卡池改用 `poolCards(true)`、`test_product_without_open_cards_hidden` 改為構築器照常列出、`test_builder_card_info_ui.py` 的尚未開放測試改為顯示並標示;建房與構築規則的拒絕測試不變)

## 3. 排序

- [x] 3.1 先寫測試並確認在修改前失敗:構築器未篩選時,MJ-001~006 排在所有事件卡之後。
- [x] 3.2 實作(design D4)。3.1 與既有排序測試通過。

## 4. 驗證與文件

- [x] 4.1 快速測試組,以及構築器、金手指、產品篩選相關的瀏覽器測試;`openspec validate pending-cards-preview --strict`。(快速組 1660 項、非 slow 瀏覽器測試 478 項全部通過)
- [x] 4.2 更新文件:`deck-builder/design.md`(顯示但不可選、金手指不顯示、MJ12 排序)、`card-data/design.md`「尚未開放的卡」的說明、capability map(如有需要)。
- [ ] 4.3 使用者確認:本機實際操作(卡池的樣式與提示、產品網格、網格項目不調暗是否可以)。

## Workflow follow-up

- 歸檔前依指南 §13 同步 delta spec 到主 spec(deck-builder)。
- 歸檔後以 `--no-ff` 合併回 `dev`。
