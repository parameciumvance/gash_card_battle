## 1. 停留時間

- [x] 1.1 先改 `tests/test_spotlight_ui.py` 的停留時間斷言(標準 2000、pass 1000、追趕時 pass 500),確認修改前失敗
- [x] 1.2 `anim.js` 的 `spotlightMs` 基準改為標準 2000ms、快 1000ms
- [x] 1.3 NPC 等待秒數改為 1.2 / 2.3 秒

## 2. Reconciliation 與歸檔(指南 §13)

- [x] 2.1 同步 delta spec 回 `battle-ui` 主 spec
- [x] 2.2 Reconcile affected capability design and rationale:`battle-ui/design.md`、`online-room/design.md` 的數字
- [x] 2.3 Update capability map(確認無需變更)
- [x] 2.4 `openspec validate --all --strict`、`python -m pytest` 全過後歸檔
