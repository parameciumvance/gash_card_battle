## 1. 實作

- [x] 1.1 先改測試確認修改前失敗:連續回合的第二次 E-018 發出 `opp_mp_reduction_restricted`(player、source),不再發出帶 skipped 的 `effect_applied`;記錄文字在四種語言都有
- [x] 1.2 `ReduceOpponentMpUnlessReducedLastTurn` 改發專用事件;`logLine` 與 i18n(zh-TW / en / ja,zh-CN 由 `build_zh_cn.py` 產生)
- [x] 1.3 前端記錄的瀏覽器測試

## 2. Reconciliation 與歸檔(指南 §13)

- [x] 2.1 同步 delta spec 回 `battle-ui`;`battle-ui/design.md` 記錄理由
- [x] 2.2 `pytest` 全過、`openspec validate --all --strict` 沒有新增失敗後歸檔
