## 1. 先寫測試

- [x] 1.1 新增瀏覽器測試 `tests/test_builder_card_info_ui.py`(開 `/?builder=1`),確認修改前失敗:對應魔物選「無」時卡池只剩指令術(對照 `CARDS` 中 `related_mamodo === "コマンド"` 的卡號);先選某魔物再把類型改為事件,對應魔物選單 `disabled`、卡池為全部事件,改回全部後選單恢復、篩選再次套用;卡池與頁位的 S-005 顯示「上級」標籤、中級卡顯示「中級」、一般卡沒有;卡號標籤可見且不被卡圖蓋住(元素可見、有底色);按卡池卡的「詳情」開啟不帶行動按鈕的放大檢視且魔本不變;按頁位卡的「詳情」開啟放大檢視,該頁沒被選取或移除。執行前若容器沒有 playwright,先 `pip install playwright && python -m playwright install --with-deps chromium`

## 2. 實作

- [x] 2.1 `cardEl`:資訊列加中級 / 上級標籤;卡號 `.cnum` 改為有底色的標籤,放大檢視與盤面維持原樣(design D1、D2);1.1 的標籤與卡號情境通過,`pytest tests/test_card_art_ui.py tests/test_battle_info_ui.py` 不受影響
- [x] 2.2 `renderCardPoolFilters` / `renderCardPool`:對應魔物「無」、類型為事件時停用且不套用但保留選擇(design D3);1.1 的篩選情境通過,`pytest tests/test_cheat_editor.py` 全過
- [x] 2.3 `cardEl` 的 `detail` 選項與牌組編輯器的卡池、頁位加上「詳情」按鈕;按鈕不觸發放卡、選取、拖拉,鍵盤可操作(design D4);1.1 的詳情情境通過,`pytest tests/test_book_grid_layout_ui.py` 全過
- [x] 2.4 i18n:`card.class.*`、`builder.filter.none`、`builder.detail` 加到 `zh-TW` / `en` / `ja`,簡中以 `tools/build_zh_cn.py` 產生(design D5);`pytest tests/test_i18n_languages.py` 全過
- [x] 2.5 截圖檢查牌組編輯器寬螢幕與窄螢幕(≤700px):卡號、中級 / 上級標籤、詳情按鈕在卡池與頁位不互相遮擋;使用者實際操作確認

## 3. Reconciliation 與歸檔(指南 §13)

- [x] 3.1 同步 delta spec 回 `deck-builder`、`battle-ui` 主 spec
- [x] 3.2 Reconcile affected capability design and rationale:`battle-ui/design.md` 補充卡片元件的卡號標籤與中級 / 上級標籤;`deck-builder` 目前沒有 design.md,若新增內容(篩選規則、詳情按鈕與共用元件的參數化)值得記錄則建立
- [x] 3.3 若 `deck-builder` 新增了 design.md,更新 capability map 的 Design 覆蓋
- [x] 3.4 `openspec validate --all --strict`(與既有基準相比沒有新增失敗)與 `pytest` 全過後歸檔
