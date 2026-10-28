# Tasks

## 1. 收錄產品資料

- [x] 1.1 `tools/scrape_ja_effects.py` 登記 E-024(第二行風味文併入 `flavor_ja`)與 P-018(`TBB　N` → `TBB2　N`)的已知錯誤,找不到原文時報錯;先寫測試(以存下的頁面 HTML 或解析函式輸入)確認修正前失敗;`python -m pytest tests -k scrape -q` 通過
- [x] 1.2 自 `data/cards_ja.csv` 移除 E-024、P-018 兩列後以卡號範圍重抓;確認 diff 只有這兩列的 `flavor_ja` / `sets_ja`
- [x] 1.3 `tools/build_cards_json.py`:以產品對照表把 `sets_ja` 轉成代號清單,未登記產品名報錯;移除 xlsx 讀取;更新 `tests/test_build_cards_json.py`(P-018 得 `["level-2", "tbb2", "re"]`、未登記產品名中止、每張卡至少一個產品),先確認新測試在修改前失敗
- [x] 1.4 重新產生 `data/cards.json`;確認 diff 只有 `sets`

## 2. 預組

- [x] 2.1 新增 `data/decks/gash-nakama.json`、`data/decks/zeon.json`(頁序取自 atwiki pages/2056、2057,記 `source` 與 `name_key`);四種語言介面字典加 `deck.gash-nakama`、`deck.zeon`(繁中先翻,簡中以 `tools/build_zh_cn.py` 同步);預組測試涵蓋兩者通過驗證與首末頁,`python -m pytest tests/test_preset_decks.py -q` 通過

## 3. 篩選設定與資源

- [x] 3.1 新增 `frontend/pool-filters.json`(產品分排;魔物順序依代表卡卡號產生初始內容)與 `frontend/products/`(放 README 說明檔名 `<代號>.webp` 與建議尺寸,產品圖由使用者放入)
- [x] 3.2 四種語言介面字典加 `product.<代號>`(11 個產品)與篩選介面文字(「全部」「無」、魔物 / 產品按鈕、已勾選數);繁中先翻,簡中同步;i18n 語言一致性測試通過

## 4. 篩選介面

- [x] 4.1 抽出規則頁的卡圖裁切為共用函式(缺圖回傳文字標籤),規則頁改用它;`ART_BOXES` 加 P-001 / S-001 / E-001 類型徽章與魔物插圖區座標,目視確認 4 個徽章與全部魔物代表卡的裁切;規則頁既有瀏覽器測試通過
- [x] 4.2 篩選狀態改為三個集合與新的比對規則(同組或、跨組且、事件 B 規則、只勾事件時魔物停用但保留);構築器與金手指共用;以瀏覽器測試(在頁面中呼叫比對函式)覆蓋各規格情境
- [x] 4.3 篩選列與彈出網格:類型徽章切換、魔物 / 產品按鈕顯示勾選、同時只開一組、點外面 / Esc 收起、「全部」清除、鍵盤操作與無障礙名稱;魔物依設定檔順序並附「無」,產品依設定檔分排、只列有開放卡片的產品;缺圖退回文字;寬窄螢幕版面
- [x] 4.4 更新既有依賴 `select` 的瀏覽器測試(`tests/test_cheat_editor.py`、`tests/test_builder_card_info_ui.py` 等),新增:多選、跨組、產品分排與不列再收錄產品、魔物順序依設定檔、缺圖文字、同時只開一組、窄螢幕一行;`python -m pytest tests -m "not slow" -q` 通過

## 5. 收尾

- [x] 5.1 全套 `python -m pytest tests -q` 通過;`openspec validate --all` 通過
- [x] 5.2 Reconciliation:同步 delta spec;直接修改主規格 `card-data`「卡片資料轉換」(刪除 `sets` 條目與「新卡的收錄產品取自 xlsx」「卡號在 xlsx 中無對應列」兩個情境,「cards.json 不含卡圖連結」拿掉 xlsx 字樣);`card-data/design.md` 改寫收錄產品的來源與理由(取代「舊卡沿用 sets、新卡取卡表 Sets 欄」);`deck-builder` 建立 `design.md` 記篩選設計與理由(事件 B 規則、彈出網格、裁切共用、設定檔);`battle-ui/design.md` 註明金手指篩選沿用構築器;更新 `openspec/capability-map.md` 的 deck-builder design 狀態

## 6. 試用後調整

- [x] 6.1 只有類型多選,魔物與產品改單選(點選即收起、「全部」取消選擇);按鈕摘要與網格項目都是圖示加名稱,類型徽章旁加類型名稱;窄螢幕上圖下字仍為一行;缺圖時魔物、產品只留名稱;更新 delta spec(「卡池篩選多選」改為「卡池篩選的選取方式」)與瀏覽器測試
- [x] 6.2 產品代號 `gash-nakama` / `zeon` 改為 `cardset-gash-nakama` / `cardset-zeon`(重新產生 `cards.json`);繁中產品名:LEVEL:3「金色的超咒文」、魔本ファイル「魔書卡本 第一彈」(其他語言補「第1弾 / Vol. 1」)
- [x] 6.3 從使用者 Drive 取 6 個產品照片轉 WebP 放入 `frontend/products/`,目視確認產品網格
- [x] 6.4 魔物網格不列金色のガッシュベル,以設定檔 `mamodo_merge` 併入ガッシュ・ベル;魔物名稱去掉括號註記(ロブノス、バルトロ);delta spec 與瀏覽器測試
- [x] 6.5 卡池排序改為 魔物 → 搭檔 → 戰術 → 事件(同類型依卡號),構築器與金手指共用;delta spec 新增「卡池排序」與瀏覽器測試
- [x] 6.6 全套 `python -m pytest tests -q` 通過;`openspec validate --all` 通過

## Workflow follow-up

- 使用者指示後歸檔並提交、合併。
