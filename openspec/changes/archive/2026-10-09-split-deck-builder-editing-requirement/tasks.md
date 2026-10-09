## 1. 驗證

- [x] 1.1 確認拆分前後一致:比對主 spec 與 delta,「對頁編輯」只刪去新增的那段說明、11 個情境原文保留;新需求的說明與原段落意思相同;新情境對照 `tests/test_builder_card_info_ui.py`、`tests/test_deck.py` 確認都是現有行為(「無」+產品複合、事件下「無」暫停若無直接測試,補測試)
- [x] 1.2 `openspec validate split-deck-builder-editing-requirement --strict` 通過

## 2. Reconciliation 與歸檔(指南 §13)

- [x] 2.1 同步 delta spec 回 `deck-builder` 主 spec,確認 `openspec validate deck-builder --type spec --strict` 通過,`--all --strict` 回到既有基準(battle-api、battle-ui、card-data、effect-tree 四個既有警告)
- [x] 2.2 Reconcile affected capability design and rationale:行為與設計都沒有改變,`deck-builder` 沒有 design.md,`battle-ui/design.md` 的卡片元件一節不受影響,確認後不需修改
- [x] 2.3 確認 capability map 不需更新(責任與覆蓋程度不變)後歸檔
