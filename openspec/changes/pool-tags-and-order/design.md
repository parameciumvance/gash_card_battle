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
- 多選(使用者選擇):點 tile 切換勾選、網格不收起;「全部」清除。按鈕摘要:未選為「全部」,選 1 個顯示該名稱,多個顯示「N 個」。
- 同組互斥(使用者要求):中級 / 上級一組、各屬性一組、干擾單獨一組;勾同組的另一個時取代。因為同組互斥,不同組之間改為同時符合(與其他篩選組一致),例如「上級 + 雷」只列雷屬性的上級卡。
- 打勾(使用者要求「多選要用打勾讓那些有選更清楚」):標籤 tile 前面有方框、勾選時框內打勾;類型徽章也是多選,勾選時右上角出現 ✓。
- 判定:干擾 = `effect_icons` / `effect_icon` 含 `jammer`(與資訊列的干擾標籤同一判斷);中級 / 上級 = `class`;屬性 = `attr_name`。

### D3 排序

- 新的 `comparePoolCards`:Ex- / PR- 以外依類型再依卡號;Ex- 全部排在其後依編號,PR- 最後依編號(使用者選擇)。
- `compareCardNumbers` 不變:魔物網格的代表卡與家族排列沿用原順序。

### D4 篩選列放不下時改緊湊版

- 多了「其他」與「標籤」後,完整版篩選列約需 673px;1280px 寬的構築器卡池欄只有 572px。使用者選擇「緊湊版」:篩選列設為 container(`container-type: inline-size`),寬度不到 700px 時類型徽章與選單按鈕改為「圖示在上、文字在下」的窄版(原本只有手機用)。手機與 1440px 以下的桌面都是緊湊版,1920px 維持完整版;都在一行內。

## Risks / Trade-offs

- [取捨] 中等寬度的桌面改用緊湊版,字比較小。→ 使用者選擇;手機原本就是這個樣式。
