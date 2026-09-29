## Why

對手行動聚焦展示的停留時間(標準約 1 秒)太短,專案負責人要求改為 2 秒。

## What Changes

- 聚焦停留時間:標準 1 秒 → 2 秒;「快」維持為標準的一半(0.5 秒 → 1 秒);只有 pass 的格同樣為一半(標準 1 秒、快 0.5 秒)。
- 排隊過多時的自動加快沿用「快」。
- NPC 的出手間隔跟著拉長,讓標準速度的聚焦跟得上:pass 類 0.7 → 1.2 秒、其他 1.3 → 2.3 秒。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `battle-ui`:「對手行動聚焦展示」的停留時間。

## Impact

- 前端:`frontend/anim.js` 的停留時間。
- API:`src/gash/api/app.py` 的 NPC 等待秒數。
- 測試:`tests/test_spotlight_ui.py` 的停留時間斷言。
- 文件:`battle-ui/design.md`、`online-room/design.md` 的數字。
