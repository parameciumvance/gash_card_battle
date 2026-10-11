## Why

疊放(變身)中的魔物在盤面只顯示最上面的卡與「×N」標記,看不到下方是哪些卡;下方的卡會影響之後的效果(例如 M-027 裝甲單獨入墓後回到 M-028),玩家需要能確認。

## What Changes

- 放大檢視疊放中的魔物時,另列出疊在下方的卡(由上而下),小卡可點開放大(純展示),並可返回原本的魔物。
- 雙方的疊放魔物都可確認(疊放的卡是場上的公開資訊,快照本來就有 `stack`)。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `battle-ui`:新增「疊放魔物的下方卡片」。

## Impact

- `frontend/app.js`(`renderZoom`)、`frontend/style.css`、i18n。伺服器不變。
- 測試:瀏覽器測試。
