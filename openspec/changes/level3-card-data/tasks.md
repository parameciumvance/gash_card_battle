## 1. 抓取與轉換

- [x] 1.1 先寫工具測試確認修改前失敗:資料頭「土」「ダメージ?」可解析;`--range` 只保留範圍內卡號;轉換「?」→ `damage_variable`;新卡的 sets 取自 xlsx
- [x] 1.2 修改 `scrape_ja_effects.py`、`build_cards_json.py`(design D1、D2);抓齊四個商品頁的 102 張,產生 `cards.json`
- [x] 1.3 `CardDef.damage_variable`;`test_deck.py` 卡片總數

## 2. 尚未開放的卡

- [x] 2.1 先寫測試確認修改前失敗:含尚未開放卡的牌組被拒絕(`deck.card_pending`,建房 422);構築器卡池與產品篩選不顯示;匯入時驗證列顯示
- [x] 2.2 `data/pending_cards.json`(第三彈 102 張)、引擎驗證、前端卡池與驗證、i18n(design D3);2.1 全過

## 3. 卡片文字與卡圖

- [x] 3.1 `build_card_texts.py` 產生日文、寫入英文卡名;起草英文效果文、繁中卡名與效果文(design D4);`build_zh_cn.py`;`tests/test_i18n_languages.py` 全過
- [x] 3.2 卡面「傷害 ?」顯示
- [x] 3.3 下載卡圖;README 提醒正式站上傳第三彈卡圖(M-050 的 Drive 連結非公開、抓不到,以文字卡面顯示)
- [ ] 3.4 使用者確認(翻譯抽查)

## 4. Reconciliation 與歸檔(指南 §13)

- [ ] 4.1 同步 delta spec 回 `card-data`、`deck-builder` 主 spec
- [ ] 4.2 `card-data/design.md` 補第三彈來源、`damage_variable`、尚未開放清單;capability map 的 card-data 說明補第三彈
- [ ] 4.3 `openspec validate --all --strict`(與既有基準相比沒有新增失敗)與 `pytest` 全過後歸檔
