## 1. 測試先行

- [x] 1.1 `tests/test_turn_dial_ui.py`:pass 前後量 Pass 按鈕的水平位置,確認修改前會移動(測試失敗:288 → 398)

## 2. 實作

- [x] 2.1 `frontend/style.css`:`#turn-cluster .turn-side` 改為固定寬度(桌機 170px、窄螢幕 84px)
- [x] 2.2 相關瀏覽器測試通過(`tests/test_turn_dial_ui.py`、`tests/test_timing_ui.py`)

## 3. 驗證

- [x] 3.1 全套 `python -m pytest tests -q` 通過;`openspec validate --all --strict` 與基準相比沒有新增失敗(1847 passed、9 skipped)
- [x] 3.2 本機實際操作抽查(使用者)

## 4. Reconciliation(指南 §13)

- [x] 4.1 同步 delta spec 到 `openspec/specs/battle-ui/spec.md`
- [x] 4.2 `openspec/specs/battle-ui/design.md` 回合轉盤的版面說明補上提示欄固定寬度的理由
