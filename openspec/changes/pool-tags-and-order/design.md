## Context

- 篩選列(`renderCardPoolFilters`,構築器與金手指共用):類型 4 顆徽章(`POOL_TYPES`、`TYPE_BADGES` 取卡圖左上的類型符號,缺圖退回文字)多選;魔物、產品、賽季三顆選單按鈕(`FILTER_MENUS`)單選,展開網格。
- 排序 `comparePoolCards`:類型(`POOL_SORT_TYPES`)→ 卡號(`compareCardNumbers`:原有前綴、Ex、PR)。魔物網格的代表卡與家族也用 `compareCardNumbers`。
- 卡片資料:`type`(mamodo / partner / spell / event / mj12)、`class`(intermediate / superior)、`effect_icon` / `effect_icons`(jammer)、`attr_name`(戰術屬性,日文)。

## Goals / Non-Goals

**Goals:** 找得到 MJ12;依標籤找卡;Ex / PR 依編號查找。

**Non-Goals:** W 魔物等其他標籤(todo 原列 W魔,使用者這次只要干擾、中上級、屬性);魔物網格的排列。

## Decisions

### D1 「其他」類型

- `POOL_TYPES` 加 `other`:比對時 `type` 不在主要 4 種的卡都算(MJ12,之後的バルカン),不必每多一種類型就加一顆徽章。
- 徽章圖示取 MJ-001 左上的符號(使用者:「圖示先用 MJ 的」),缺圖文字「他」;文字標籤「其他」。

### D2 標籤篩選

- 第 4 顆選單按鈕「標籤」(`FILTER_MENUS` 加 `tag`),網格只有文字 tile:干擾、中級、上級、各屬性(依 `attr.*` 的語言名稱,順序依卡數多寡:雷、重力、土、風、水、冰、木、火)。
- 多選(使用者選擇):點 tile 切換勾選、網格不收起;「全部」清除;符合任一即可;與其他組同時符合。按鈕摘要:未選為「全部」,選 1 個顯示該名稱,多個顯示「N 個」。
- 判定:干擾 = `effect_icons` / `effect_icon` 含 `jammer`(與資訊列的干擾標籤同一判斷);中級 / 上級 = `class`;屬性 = `attr_name`。

### D3 排序

- 新的 `comparePoolCards`:Ex- / PR- 以外依類型再依卡號;Ex- 全部排在其後依編號,PR- 最後依編號(使用者選擇)。
- `compareCardNumbers` 不變:魔物網格的代表卡與家族排列沿用原順序。

## Risks / Trade-offs

- [風險] 篩選列多一顆徽章與一顆按鈕,手機上要捲動。→ 篩選列本來就是單行、可橫向捲動;截圖確認。
