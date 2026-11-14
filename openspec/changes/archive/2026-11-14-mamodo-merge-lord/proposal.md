## Why

M-081 ロード「このカードは場にあるとき、『ゾフィス』としてあつかう」,和 M-047(視為ガッシュ・ベル)同類。使用者 2026-11-14 要求在卡池的魔物篩選比照 M-047 合併。

## What Changes

- `frontend/pool-filters.json` 的 `mamodo_merge` 加上「ロード → ゾフィス」:魔物網格不單獨列出ロード,選ゾフィス時一併顯示 M-081。只影響篩選,卡片資料不變。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `deck-builder`:修改「魔物篩選圖示與順序」。

## Impact

- `frontend/pool-filters.json`;測試 `tests/test_pool_filters_ui.py`。
