## Why

場上魔物依清單順序排欄:左邊的魔物送墓後,中間的魔物會補到左邊,玩家會誤以為魔物換了位置。魔物在場上的位置應固定。

## What Changes

- 引擎為每隻場上魔物記錄欄位(0–2,由左至右):新登場的魔物放在最左邊的空欄;疊放、負傷、恢復都維持原欄;魔物離場後那一欄留空,其他魔物不移動。
- 快照的魔物槽加欄位。
- 盤面依欄位排列魔物與搭檔,空欄顯示空的魔物欄。
- 規則判定不變:欄位只影響位置,不影響效果與選擇順序。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `game-engine`:新增「場上魔物的欄位」。
- `battle-api`:新增「魔物槽欄位快照」。
- `battle-ui`:新增「魔物位置固定」。

## Impact

- 引擎:`state.py`(`MamodoSlot.column`、放置用的共用函式)、`engine.py` / `effects/primitives.py` / `effects/tree.py` 中新增魔物槽的地方。
- 伺服器:`views.py` `_slot_view`。
- 前端:`frontend/app.js` `renderFieldBlock`。
- 測試:引擎、快照、瀏覽器。
