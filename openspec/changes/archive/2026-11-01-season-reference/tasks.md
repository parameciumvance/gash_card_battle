# Tasks

## 1. 測試先行

- [x] 1.1 瀏覽器測試:規則頁「賽季」段落的表格(第 1 賽季的範圍與產品、第 1 賽季 Ex 為「—」、第 3 賽季的上限與產品、Ex-000 註記);改 `SEASONS` 後重建規則頁,表格跟著變;四種語言段落一致(既有的規則頁內容檔測試)。執行並確認修改前失敗
- [x] 1.2 瀏覽器測試:設定頁四個賽季選單旁的連結、構築器的賽季標示,點了都開啟規則頁並捲動到賽季段落,關閉後選擇與魔書不變。執行並確認修改前失敗

## 2. 規則頁

- [x] 2.1 `renderRuleSeasons`(D1、D2)與 `{"seasons": true}` 區塊;確認與 `SEASONS`、卡片資料的載入順序(Risks):規則頁在第一次開啟時才建立,`boot` 已載入兩者;切換語言會重新載入頁面
- [x] 2.2 三種撰寫語言的內容檔新增「賽季」段落與 `seasons` 標籤(D4);`tools/build_zh_cn.py` 產生簡中
- [x] 2.3 表格樣式(窄螢幕可橫向捲動、不撐破版面)

## 3. 入口

- [x] 3.1 四個賽季選單旁的「?」連結;`ui.season.help`(四語)(D3)
- [x] 3.2 構築器 `#builder-season` 可點(D3)

## 3a. 附帶修正

- [x] 3a.1 構築器的賽季標示在淺色標題列上看不清(淺色字、透明背景,對比 1.16):改用按鈕的深色背景,與旁邊的按鈕一致;瀏覽器測試檢查文字對比 ≥ 4.5,修改前失敗
- [x] 3a.2 日文的回報入口不一致(頂欄按鈕「報告」、對話框標題與首頁入口「フィードバック」):標題與首頁入口改為「ご意見・報告」,比照繁中「回報」/「意見回報」;`test_i18n_languages` 檢查四語的按鈕詞包含在標題裡、首頁入口與標題相同,修改前日文失敗
- [x] 3a.3 「第 N 賽季起」改為「第 N 賽季起可用」(構築器標示 `ui.season.from`、牌組選單 `ui.deck.season_suffix`、規則頁說明;四語);瀏覽器測試的期望文字先改、修改前失敗

## 4. 驗證

- [x] 4.1 快速測試組(1493 passed)與相關瀏覽器測試(`test_season_reference_ui`、`test_rules_ui`、`test_language_ui`、`test_tables_ui`、`test_npc_ui`、`test_builder_card_info_ui`、`test_pool_filters_ui` 共 96 passed)通過;寬 / 窄螢幕截圖確認表格不撐破版面(窄螢幕在段落內橫向捲動);`openspec validate --all --strict` 與基準相比沒有新增失敗
- [x] 4.2 本機實際操作抽查(使用者)

## 5. Reconciliation(指南 §13)

- [x] 5.1 同步 delta spec 到 `battle-ui`、`deck-builder` 主 spec
- [x] 5.2 `battle-ui/design.md` 規則頁一節記錄動態賽季表與產品賽季的推導(D1、D2)
