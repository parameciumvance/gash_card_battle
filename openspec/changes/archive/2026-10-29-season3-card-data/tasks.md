## 1. 抓取與轉換

- [x] 1.1 先寫工具測試,確認修改前失敗:
  - 拡張シート頁的 `Ex-` 卡號能解析,シート分組不重複。
  - 特典卡頁在 `--untyped` 下取得 PR 卡號,類型取自卡頁。
  - 新產品名轉為代號,含 `拡張2　R|TBB2　N` → `["ex-sheet-2", "tbb2"]`。
  - M-032 / M-060 的「別売魔本」分別轉為 `mahon-file` / `mahon-file-2`。
- [x] 1.2 修改 `scrape_ja_effects.py`(design D1)與 `build_cards_json.py`(D2:`PRODUCTS`、`mahon-file-2`、`EXPECTED_COUNT` 332)。
- [x] 1.3 依序抓 pages/59、58(`--range M-059:M-061`)、56、52、53、61,產生 `cards.json`。
  - 遇到未知 token 或頁面漏刊時逐一確認,登記處記錄在本檔。
  - 實作紀錄:沒有未知 token。拡張シート的版面差異(尾行在最後一段、無 / 多行風味文)依 design D1 處理;登記 Ex-005(風味文位置)與 Ex-002(多餘逗號)。
- [x] 1.4 `data/pending_cards.json` 列入 95 張。
- [x] 1.5 更新 `test_deck.py` 等處的卡片總數。
- [x] 1.6 加入卡片資料測試:第 3 賽季卡號齊全、沒有 `EX-` 卡號、Ex-001 建房回 `deck.card_pending`。

## 2. 卡片文字

- [x] 2.1 先寫測試確認修改前失敗:TTS 卡表 `EX-001` 的英文卡名寫入 `Ex-001`(design D3)。
- [x] 2.2 修改 `build_card_texts.py`,產生日文與英文卡名。
- [x] 2.3 起草英文效果文、繁中卡名與效果文(D6),執行 `build_zh_cn.py`。
- [x] 2.4 `tests/test_i18n_languages.py` 與卡片文字相關測試全過。

## 3. 卡圖與產品圖

- [x] 3.1 先寫測試確認修改前失敗:資料夾檔名 `EX-001.webp` 存成 `Ex-001.webp`(D3)。
- [x] 3.2 修改 `download_images.py` 並下載卡圖,列出缺圖清單。
- [x] 3.3 產品圖(D4):
  - 從產品照片資料夾轉出 `limited-1`、`special-box`、`mahon-file-2`、`ex-sheet-1`、`ex-sheet-2`。
  - 產生 `promo` 的「PR」圖。
  - 更新 `frontend/products/README.md`。

## 4. 產品篩選

- [x] 4.1 先寫瀏覽器測試確認修改前失敗(測試替身清空尚未開放清單):
  - 產品分排為 4 排,依賽季。
  - 手機寬度第 3 排換行,續行縮排,沒有水平捲動。
  - 選特典卡只顯示 PR 卡。
- [x] 4.2 確認新產品在卡片開放前不列出(維持現狀的測試)。
- [x] 4.3 修改 `pool-filters.json`(一排一個賽季系列)與 `.filter-row` 的換行縮排樣式。
- [x] 4.4 四語 `product.<代號>`(D4),zh-CN 用 `build_zh_cn.py` 產生。
- [x] 4.5 目視確認產品網格。

## 5. 前端卡號格式

- [x] 5.1 先寫測試確認修改前失敗:行動記錄的事件引用 `Ex-` / `PR-` 卡號時可辨認(D5)。
- [x] 5.2 修改 `app.js` 的 `cardRefs` 與 `anim.js` 的 `CARD_NO`。

## 6. 確認、Reconciliation 與歸檔(指南 §13)

- [x] 6.1 使用者確認翻譯抽查與產品譯名。
- [x] 6.2 同步 delta spec 回 `card-data`、`deck-builder` 主 spec。
- [x] 6.3 更新設計文件與說明:
  - `card-data/design.md`:第 3 賽季來源、`Ex-` 寫法、`mahon-file-2`、外部來源對應。
  - `deck-builder/design.md`:分排與換行縮排。
  - capability map。
  - README:正式站上傳新卡圖。
- [x] 6.4 驗證後歸檔:
  - 全套 `python -m pytest tests -q` 通過。
  - `openspec validate --all --strict` 與既有基準相比沒有新增失敗。
