# Tasks

## 1. 賽季定義

- [x] 1.1 先寫測試並確認在修改前失敗:
  - Ex-100 / Ex-101 / Ex-099 依序為第 3 / 3 / 4 賽季。
  - PR-004 / 005 / 010 / 011 / 013 依序為第 2 / 3 / 3 / 4 / 4 賽季。
  - M-085、S-146、Ex-074 為第 4 賽季;M-086 沒有賽季。
  - 前端 `cardSeason` 與引擎的結果相同。
- [x] 1.2 修改 `data/seasons.json`(design D1)。1.1 通過;既有用到 PR 賽季當例子的測試照新定義調整,並在本檔記錄改了哪些。(實作紀錄:沒有既有測試需要調整)

## 2. 抓取與轉換

- [x] 2.1 先寫工具測試並確認在修改前失敗:
  - 卡頁的 `LEVEL:4`、`拡張3`、`限定拡張` 收錄產品行能被辨認,備註行不併入。
  - PR-012 沒有「パートナー＝」時不報錯,`related_partner_ja` 為空;未登記的魔物照舊報錯。
  - 「限定拡張」依卡號轉為 `dx-red-book` / `festa-2004-spring`;未登記的卡號報錯。
  - M-070 的 `LEVEL:4|TBB1|RE` 轉為 `["level-4", "tbb1", "re"]`。
- [x] 2.2 修改 `scrape_ja_effects.py`(`PRODUCT_NAMES`、`KNOWN_NO_PARTNER`、說明文件的來源頁)與 `build_cards_json.py`(`PRODUCTS`、`LIMITED_EXPANSION`、`EXPECTED_COUNT` 426,補收 MJ12 後 432)。2.1 通過。
- [x] 2.3 依序抓 pages/36、54,再抓 pages/61(`--untyped`,範圍 Ex-000、Ex-049、Ex-050、Ex-099~101、PR-012~013),產生 `cards.json`。
  - 遇到未知 token 或頁面漏刊時逐一確認,登記處記錄在本檔。
  - 重新轉換後,逐卡比對既有 332 張的 `cards.json` 沒有變動。
  - 實作紀錄(design D7):
    - 新 token「石版魔物」(Ex-056~058):使用者選擇記為魔物 + `stone_tablet`;`cards_ja.csv` 加欄位,先寫測試確認失敗後實作。
    - Ex-050 的魔力倍率寫成「1000x」:轉換工具接受字母 x。
    - M-080 有兩個效果圖示:記為 `effect_icons`。
    - 沒有頁面漏刊。既有 332 張逐卡比對沒有變動;新卡的戰術與搭檔都對得到魔物家族,新家族 9 個(エルジョ、ゴーレン、ドグモス、ドンポッチョ、バランシャ、ビョンコ、ボルボラ、ロード、黒騎士)。
- [x] 2.4 `data/pending_cards.json` 列入 100 張(含 MJ-001~006);更新各測試的卡片總數(`test_deck.py`;`test_season3_cards.py` 的總數移到 `test_season4_cards.py`)。
- [x] 2.5 卡片資料測試:新卡號齊全、共 432 張、M-070 / Ex-100 / MJ-001 建房回 `deck.card_pending`。
- [x] 2.6 補收 MJ12(design D8,使用者指出漏抓):
  - 先寫工具測試並確認失敗:產品頁的 MJ12 分類、卡頁資料頭「ＭＪ１２」、`MJ-` 範圍、轉換後類型為 `mj12`。
  - 抓取工具辨認 MJ12;抓 MJ-001~006;`seasons.json` 第 4 賽季加入 MJ-006;pending、總數 432、四語卡片文字(英文卡名取自卡表)、卡圖。
  - 重新轉換後,`cards.json` 只多出這 6 張。

## 3. 卡片文字

- [x] 3.1 `build_card_texts.py` 產生日文與英文卡名。TTS 卡表沒有的英文卡名,記錄在本檔,由 3.2 起草。
- [x] 3.2 起草英文效果文、繁中卡名與效果文(design D6),執行 `build_zh_cn.py`。
  - 實作紀錄:英文卡名在 TTS 卡表全部都有。效果文裡「」括起的卡名都對上該卡的繁中名;每個日文名只對應一種繁中譯名。新元素「水」譯為「水」。
  - 待使用者校對的地方:
    - ジャマー効果:譯為「CUT-IN效果」(依規則頁)/ Jammer effect(E-052、M-077)。
    - W魔物、VS魔物:保留「W魔物 / VS魔物」(E-050)。
    - 石版魔物:譯為「石版魔物」/ Stone Tablet MAMODO。
    - 【バトル攻撃】【バトル防御】:譯為【戰鬥攻擊】【戰鬥防禦】(S-113)。
    - 原文誤植:M-075「自分も相手は」照「自分も相手も」翻譯;P-045「ドンボッチョ」照卡名翻譯。(使用者採納,design D6)
    - Ex-051「イベントカードやパートナーカードの効果」的範圍。
    - Ex-060「ページを移動させる」。
    - Ex-074「MJ12カード」。
    - Ex-101「端数切り捨て」。
    - 新名稱:ワイフ(英文名 Wife)、指令戰術 S-145 / S-146。
    - MJ-001~006 的繁中卡名與效果文、英文效果文(補收時起草)。
  - 使用者校訂繁中(2026-11-07)後檢查一致性:同一日文卡名只對應一個譯名、效果文「」內的卡名跟著改名;重新產生 zh-CN。
- [x] 3.3 `tests/test_i18n_languages.py` 與卡片文字相關測試全部通過。(另外:`test_cards.py` 的借用搭檔測試排除尚未開放的搭檔,避免 P-044~050 被當成被動搭檔而略過)

## 4. 卡圖與產品圖

- [x] 4.1 用 `download_images.py` 下載新卡的卡圖,列出缺圖清單。(100 張全部下載成功,沒有缺圖)
- [ ] 4.2 產品圖(design D4):有照片的產品轉成 WebP,更新 `frontend/products/README.md`;沒有照片的列入缺圖清單。(進度:`dx-red-book` 已完成;`level-4`、`ex-sheet-3`、`festa-2004-spring` 等使用者提供照片資料夾的位置。之後 `test_product_rows_by_season_when_all_open` 的產品圖檢查要加入這三個)

## 5. 產品篩選

- [x] 5.1 先寫瀏覽器測試並確認在修改前失敗(測試替身清空尚未開放清單):
  - 產品分 5 排。
  - 第 3 排末尾是 DX赤い魔本。
  - 第 4 排是 LEVEL:4、魔本拡張シート LEVEL:3、電撃フェスタ2004春の陣。
- [x] 5.2 確認新卡尚未開放時產品網格與修改前相同(維持現狀的測試)。
- [x] 5.3 修改 `pool-filters.json`;補四語 `product.<代號>`(zh-CN 用 `build_zh_cn.py` 產生)。5.1、5.2 通過。

## 6. 規則頁的賽季表

- [x] 6.1 先寫瀏覽器測試並確認在修改前失敗:
  - 表格沒有第 4 賽季,第 3 賽季的 PR 到 010。
  - 註明 Ex-100、Ex-101 屬第 3 賽季;Ex-000、Ex-099 屬第 4 賽季、目前不能選。
  - 把 4 加入 `selectable` 後,表格出現第 4 賽季。
- [x] 6.2 修改 `renderRuleSeasons`,四語規則內容檔新增註明文字(design D5;英文的 note 改成「Season {n} cards (not selectable yet): {card}.」,因為一句會列出多張卡)。6.1 與 `test_season_reference_ui.py` 既有測試通過。

## 7. 驗證與文件

- [x] 7.1 快速測試組,以及相關的瀏覽器測試(`test_season_reference_ui.py`、`test_seasons_ui.py`、產品篩選相關)。執行 `openspec validate season4-card-data --strict`。(快速組 1652 項;非 slow 瀏覽器測試 472 項全部通過)
- [x] 7.2 更新文件:
  - `card-data/design.md`:第 4 賽季的來源、限定拡張的卡號對應、沒有搭檔的魔物、PR 範圍調整。
  - `deck-builder/design.md`:新的分排。
  - `battle-ui/design.md`:賽季表只列可選賽季與註明。
  - capability map。
- [ ] 7.3 使用者確認:翻譯抽查、產品譯名、本機實際操作(規則頁賽季表;用測試替身開放新卡,看產品網格與卡面)。

## Workflow follow-up

- 歸檔前依指南 §13 同步 delta spec 到主 spec(card-data、deck-builder、battle-ui)。
- 歸檔後以 `--no-ff` 合併回 `dev`。
- 之後依卡號分批開效果實作的 change(比照 season3-effects-1~6)。
