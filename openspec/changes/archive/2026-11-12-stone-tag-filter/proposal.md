## Why

season4-stone-tablets 為石版卡(Ex-056~058)加了資訊列的「石版」標籤,但卡池的標籤篩選沒有對應的項目,使用者 2026-11-11 回報。

## What Changes

- 卡池標籤篩選的第一列加入「石版」,與「干擾」排在同一列但不互斥(使用者決定),各自是一組,同時勾選時要同時符合。判定依卡片資料的 `stone_tablet`。
- 構築器卡池與金手指卡池共用同一份標籤設定,兩邊都有。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `deck-builder`:修改「卡池標籤篩選」。

## Impact

- 前端:`frontend/app.js`(`POOL_TAGS`、標籤網格分列);瀏覽器測試。
