# Design

## Decisions

### D1:放在第一列、與干擾不互斥(使用者決定)

- `POOL_TAGS` 新增 `{ key: "stone_tablet", group: "stone" }`;標籤網格的第一列放 `jammer` 與 `stone` 兩組,其餘列不變。
- 不同組之間照既有規則同時符合;目前沒有同時是干擾與石版的卡,兩個都勾時結果為空,與「干擾 + 上級 + 水」同樣處理。文字沿用 `card.tag.stone_tablet`(四語已有)。
