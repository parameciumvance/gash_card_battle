# Proposal

## Why

- 卡池的類型 / 對應魔物 / 產品篩選是三個單選下拉,魔物有 30 個家族、產品名是英文字串,要一個個讀字才找得到;使用者希望改成看圖點選,類型能一次勾多個。
- 產品篩選讀的 `cards.json` `sets` 來自英文 xlsx 的 Sets 欄(Series 1~4、The Gathering Storm 等英文版命名,還有大小寫不一的重複標籤),與日文權威來源的產品不一致;日文來源 `data/cards_ja.csv` 的 `sets_ja` 已經有每張卡的收錄產品。
- 第三系列的兩個構築済み魔本(「ガッシュ・ベルと仲間達」「ゼオンと最凶魔物達」)用到的卡都已開放,但還不能當預組選用。

## What Changes

- **卡池篩選改為圖示篩選**(構築器與金手指共用):
  - 一行篩選列:4 顆類型徽章(從卡圖左上的「魔 / 使 / 術 / 鍵」裁出)平鋪,加「魔物」「產品」兩顆按鈕;按鈕點開彈出圖示網格,同時只開一個。
  - 類型可多選(同組為「或」);魔物與產品單選,點選即收起網格,「全部」取消選擇;跨組為「且」。(原規劃三組皆多選,實際試用後改為只有類型多選。)
  - 每個圖示旁都留文字(類型名稱、魔物名稱、產品名稱),按鈕上的目前選擇也是圖示加名稱。
  - 魔物網格以各家族的代表魔物卡插圖區(卡名列以上)為圖示,另有「無(指令戰術)」;順序可由設定檔調整。
  - 有選對應魔物時,事件不顯示;類型只勾「事件」時魔物篩選停用但保留選擇(沿用現行規則)。
  - 產品網格依設定檔分排:LEVEL:1 / LEVEL:2、魔本ファイル第1弾 / LEVEL:3、ガッシュ・ベルと仲間達、ゼオンと最凶魔物達;再收錄產品(TBB1、TBB2、RE、FILE:1、LEVEL:S)不列出。產品圖取自使用者的 Drive 產品照片,轉成 WebP 放 `frontend/products/`(進 git),缺圖只顯示名稱;產品名稱四種語言翻譯。
  - 卡圖未安裝或缺圖時,類型徽章退回「魔 / 使 / 術 / 鍵」文字,魔物與產品只顯示名稱。
  - **BREAKING**(介面):下拉選單移除,窄螢幕的「篩選以下拉呈現」改為同一套圖示篩選列。
- **`sets` 改用日文來源**:`cards.json` 的 `sets` 由 `cards_ja.csv` 的 `sets_ja` 取產品(去掉稀有度與販售形式),以產品代號表示;修正抓取資料的兩個錯誤(E-024 第二行風味文被當成產品、P-018 的「TBB」實為 TBB2)。
- **新增兩個預組**:`data/decks/` 加入第三系列兩個構築済み魔本,依 atwiki 魔本頁的 32 頁順序;名稱四種語言翻譯。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `deck-builder`:「對頁編輯」的篩選描述與手機篩選情境改為圖示篩選列;「卡池篩選的對應魔物」改為網格選擇的描述;新增「卡池圖示篩選」相關需求(圖示來源與文字、選取方式、產品分排與再收錄產品不列出、設定檔順序、缺圖退回)。
- `battle-ui`:「金手指面板」的組合篩選改為與構築器相同的圖示篩選。
- `card-data`:「卡片資料轉換」的 `sets` 改由 `sets_ja` 產生並以產品代號表示;「預組魔書資料」納入第三系列兩個預組。

## Impact

- 前端:`frontend/app.js`(`renderCardPoolFilters`、`matchesMamodoFilter`、`renderCardPool`、規則頁的卡圖裁切共用)、`frontend/style.css`、`frontend/index.html`;新增 `frontend/pool-filters.json`(產品分排、魔物順序)與 `frontend/products/`(產品圖)。
- i18n:`frontend/i18n/{zh-TW,zh-CN,en,ja}.json` 新增產品名稱、兩個預組名稱與篩選介面文字。
- 資料與工具:`tools/scrape_ja_effects.py`(已知資料錯誤修正)、`data/cards_ja.csv`、`tools/build_cards_json.py`、`data/cards.json`(`sets` 值全部改變)、`data/decks/` 新增兩檔。
- NPC 房「隨機預組」的候選會多出兩個新預組(候選來自預組探索清單)。
- 測試:構築器 / 金手指篩選的瀏覽器測試、`test_build_cards_json.py`、預組測試需配合更新。
