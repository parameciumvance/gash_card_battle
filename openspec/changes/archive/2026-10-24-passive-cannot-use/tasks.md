# Tasks

## 1. 測試先行

- [x] 1.1 新增 `tests/test_passive_cannot_use.py`:逐張寫「受限時不生效」的測試(M-002 / M-003 / M-004 / M-006 / M-007 / M-009 / M-014 / M-023 / M-024 / M-025 / M-028 / M-031 / M-036 / M-040 / M-051 / M-053 / P-013 / P-019 / P-024 / P-030),魔物卡涵蓋全體限制(E-025)與個別限制(E-024),搭檔卡用 E-008;另寫時點型不補發、持續型解除後恢復、M-024 一隻被個別限制仍 2 次。確認這些測試在修改前失敗
- [x] 1.2 同檔寫不受影響的對照:M-029 受 E-025 時仍可用ザケル、M-047 受限時放出仍排定離場、M-038 不受影響、未受限時各卡照常生效(既有測試已涵蓋者不重寫);確認修改前通過

## 2. 專用規則分開登記

- [x] 2.1 `registry.py`「純資料登記(不是效果)」新增 `rule_on_play` / `rule_spell_compat`;M-047、M-029 改登記;`run_on_play` 收斂所有 `ON_PLAY` 呼叫點(`grep "reg.ON_PLAY\["` 只剩一處);`_spell_usable_by` 同時查 `RULE_SPELL_COMPAT`。`python -m pytest tests -m "not slow and not browser" -q` 通過

## 3. 常駐效果的「使えない」

- [x] 3.1 `engine.py` 新增 `card_effect_blocked`;依 design 的表在各消費端加上檢查(開始階段、`power_breakdown`、`run_on_play`、入墓、`_dispatch_triggers`、`_spell_usable_by`、`spell_use_limit`、傷害免疫、`event_cost`、`reveals_open_pages`);M-047 改 `AlwaysImmune`。1.1 / 1.2 全過,快速層通過;若既有測試因此失敗,先列出差異告知使用者

## 4. 驗證與收尾

- [x] 4.1 全套 `python -m pytest tests -q` 通過;`openspec validate --all --strict` 沒有新增失敗
- [x] 4.2 Reconciliation:`card-effects/design.md` 第 4 批機制的「常駐效果與『使えない』」改寫為全面套用,並在「行為決定與理由」記錄專用規則的區分、判斷時點、M-024、M-006 不處理(使用者確認,2026-10-24);`game-engine/design.md`「1 個行動、ジャマー與『使えない』」補 `card_effect_blocked` 與規則表;`todo.md` 移除「既有常駐效果的『使えない』檢查修正」

## Workflow follow-up

- 使用者指示後歸檔並提交。
