## Why

對局賽季(`match-seasons`)已經定義第 1~3 賽季的卡號範圍,但卡片資料只收錄到 M-053、S-106、P-035、E-043,PR 與 Ex 卡一張都沒有。第 3 賽季範圍內還有 95 張卡沒有資料。這個 change 先補齊資料,讓這些卡可以查閱和顯示;效果之後分批實作。

## What Changes

- 新增 95 張卡的日文權威資料、`cards.json`、四種語言的卡片文字和卡圖。這 95 張全部列入 `pending_cards.json`,效果實作前不能用於構築。
  - M-054~069(16 張)、S-107~112(6 張)、P-036~043(8 張)、E-044~049(6 張)
  - PR-001~011(11 張)、Ex-001~048(48 張)
- 卡號以 atwiki 為準,用 `Ex-` 而不是 `EX-`。`Ex-000` 不在本次範圍。
- atwiki 抓取工具:
  - 支援 `Ex-` 卡號。
  - 略過拡張シート商品頁的重複分類(シート1~12)。
  - PR 卡的類型從個別卡頁讀取,因為 PR 的商品頁沒有分類。
- 收錄產品對照表新增六個代號:
  - LTD1 → `limited-1`
  - SPBOX → `special-box`
  - 拡張1 → `ex-sheet-1`
  - 拡張2 → `ex-sheet-2`
  - プロモ → `promo`
  - 魔本ファイル第2弾 → `mahon-file-2`(第 3 賽季)。atwiki 把第1、2弾都寫作「別売魔本」,轉換時依卡號區分:M-059~061 屬第2弾,M-032~034 維持 `mahon-file`(第1弾,第 2 賽季)。
- 產品篩選:
  - 設定檔一排就是一個賽季的系列,不再因為寬度拆排。
  - 一排放不下時依寬度換行,續行縮排,表示仍屬同一系列。
  - 新增 LIMITED EDITION Ⅰ、スペシャルボックス、魔本ファイル第2弾、拡張シート LEVEL:1 / 2 與 PR 卡。
  - 新產品圖取自維護者的產品照片;PR 卡不是單獨商品,用「PR」字樣的 logo 圖。
- 卡圖下載:Drive 檔名 `EX-xxx.webp` 對應到卡號 `Ex-xxx`。
- 英文卡名的來源 TTS 卡表寫作 `EX-`,讀取時同樣對應到 `Ex-`。
- 前端辨認卡號的格式(行動記錄中的卡號、對局動畫的來源卡)納入 `PR-` 與 `Ex-`。
- 中文與英文的效果文、中文卡名先由 AI 初譯,待使用者校對。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `card-data`:
  - 新增第 3 賽季卡片資料。
  - 抓取工具支援 Ex 卡號、拡張シート頁與 PR 卡類型。
  - 收錄產品對照表加入新代號。
  - 卡圖下載的檔名對應。
- `deck-builder`:產品篩選分排改為一排一個賽季系列、自動換行縮排,並加入新產品與 PR 卡。

## Impact

- 工具:`tools/scrape_ja_effects.py`、`tools/build_cards_json.py`(`PRODUCTS`、`EXPECTED_COUNT`)、`tools/build_card_texts.py`(TTS 卡號對應)、`tools/download_images.py`。
- 資料:
  - `data/cards_ja.csv`、`cards.json`、`cards.{ja,en,zh-TW,zh-CN}.json`、`pending_cards.json`
  - `frontend/pool-filters.json`、`frontend/products/*.webp`(與 README)
- 前端:
  - `frontend/app.js`:產品網格換行縮排、卡號格式。
  - `frontend/anim.js`:卡號格式。
  - `frontend/style.css`。
  - 四語 `product.<代號>`。
- 測試:卡片總數、工具解析、產品分排、卡號格式。
- 正式站:要上傳新卡圖(卡圖 volume)。
