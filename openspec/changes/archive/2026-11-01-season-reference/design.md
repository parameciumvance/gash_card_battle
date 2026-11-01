# Design

## Context

- **賽季定義**:`data/seasons.json` 記各賽季每個卡號前綴的最大編號,`special` 直接指定賽季(Ex-000 → 4),`selectable` 是可選的賽季。前端已經載入成 `SEASONS`,`cardSeason` / `deckSeason` 用它推導。
- **規則頁**:內容來自 `frontend/i18n/rules.<lang>.json`。內容檔已有動態區塊(`{"figure": ...}`、`{"icons": true}`),由 `buildRules` 交給程式畫;區塊用到的標籤也放在內容檔(如 `figure`)。
- **產品**:卡片的 `sets` 記收錄產品。卡池篩選的 `pool-filters.json` `products` 依賽季分排列出非再收錄產品(最後一排是虛擬的 Ex 卡與特典カード),產品名稱在介面字典的 `product.*`。
- **連結到規則頁的既有做法**:回合轉盤與行動欄詳細提示呼叫 `openRules(sectionId)`。

## Goals / Non-Goals

**Goals**

- 規則頁能查到每個賽季的卡號範圍與新增的產品。
- 從設定頁與構築器的賽季相關位置一鍵打開這個段落。

**Non-Goals**

- 不改 `seasons.json` 格式與伺服器。
- 不在卡池篩選的賽季網格加連結(使用者只要求設定頁與構築器)。

## Decisions

### D1 表格由資料產生

新增區塊 `{"seasons": true}`,`renderRuleSeasons` 依 `SEASONS.seasons` 逐賽季畫一列。

- **欄位**:賽季、M、S、P、E、PR、Ex 的範圍、新增產品。前綴欄的順序固定在程式裡;資料出現新前綴時接在後面。
- **範圍寫法**:`001–015`,從 1 開始。賽季是累積的,第 N 賽季的範圍包含前面的賽季。該賽季沒有的前綴顯示「—」。
- **註記**:`special` 指定到 `selectable` 以外賽季的卡,在表格下方註明(「Ex-000 屬第 4 賽季,目前不能選」)。
- **標籤**:表頭、「—」以外的文字、註記模板放在內容檔的 `seasons` 物件(比照 `figure`),三種撰寫語言各寫一份;賽季名稱沿用介面字典的 `ui.season.n`。
- 替代方案是在內容檔寫死表格。不採用:補卡要改四份檔案,容易和 `seasons.json` 不一致。

### D2 產品的賽季

一個產品的賽季,是收錄卡(卡片 `sets` 含該產品)中最晚的卡的賽季,用既有的 `cardSeason` 計算。

- 列在該賽季的「新增產品」,順序依 `pool-filters.json` 的 `products`。
- 不列:再收錄產品(本來就不在 `products` 裡)、虛擬的 `ex` 與 `promo`(它們跨賽季,範圍已由 Ex、PR 欄表達)。
- 依現有資料:第 1 賽季 LEVEL:1;第 2 賽季 LEVEL:2、魔本ファイル第1弾、魔本拡張シート LEVEL:1;第 3 賽季 LEVEL:3、兩個カードセット、LIMITED EDITION Ⅰ、スペシャルボックス、魔本ファイル第2弾、魔本拡張シート LEVEL:2。與 card-data design「賽季」記載的發售範圍一致。
- 替代方案是直接用 `products` 的排序號當賽季。不採用:排是呈現用的分組,最後一排就不是賽季。

### D3 入口

- **設定頁**:四個賽季選單(`season-npc`、`season-friend`、`season-local`、`season-tables`)旁各加一個小按鈕「?」,`openRules("seasons")`。按鈕的 `title` / `aria-label` 用介面字典 `ui.season.help`(四語)。
- **構築器**:`#builder-season` 改成可點(游標、hover 樣式),點了 `openRules("seasons")`;`title` 同上。標示仍只是資訊,不影響合法性。

### D4 段落位置

「賽季」段落放在「魔書構築」之後、「準備」之前,和構築規則放在一起。三種撰寫語言的段落 id 與順序一致(battle-ui「規則頁的內容檔與開啟」)。

## Risks / Trade-offs

- 規則頁開啟時,`SEASONS` 與卡片資料要已載入。規則頁本來就在資料載入後才能開(`RULES` 也是非同步載入);若規則頁先建好、`SEASONS` 才到,表格會不完整。所以 `buildRules` 要在兩者都載入後才執行,或讓表格在開啟時重新產生。實作時確認載入順序。
