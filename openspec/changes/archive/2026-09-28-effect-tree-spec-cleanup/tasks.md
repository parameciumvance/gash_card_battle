## 1. 確認移出的內容有去處

- [x] 1.1 確認 `openspec/design.md` 第 2.2 節記錄了分派鍵(`tree_choice` / `tree_cont`,程式常數 `CHOICE_KEY` / `CONT_KEY`)、續體格式 `(effect_id, path, ctx, floor)`,以及 `CoinWithPaidReflip` 兩種停點各用哪個鍵;缺的補上
- [x] 1.2 確認 `tree_cards.py` 開頭的排版說明涵蓋容器節點換行縮排、收尾括號獨立成行
- [x] 1.3 確認現有測試仍涵蓋改寫後每條需求的情境(`tests/test_effect_tree.py`),`python -m pytest` 全過
- [x] 1.4 `openspec validate effect-tree-spec-cleanup` 通過

## 2. 同步、合併設計、歸檔

- [x] 2.1 同步 delta spec 回 `openspec/specs/effect-tree/spec.md`(含更名)
- [x] 2.2 把本 change 仍有效的決定合併進 `openspec/design.md`:spec 與 design 的分界標準(換一種實作仍須成立的性質寫在 spec;鍵名、欄位格式、排版寫在 design 或程式說明)
- [x] 2.3 歸檔本 change
