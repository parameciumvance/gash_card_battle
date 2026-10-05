# card-data — 設計

目前只整理了卡片文字檔(顯示用的多語文字);抓取、`cards.json` 轉換與卡圖管線以 `tools/` 程式、README「資料管線」與測試為準。

## 卡片文字檔

- **分層**:遊戲邏輯只讀 `data/cards.json`(日文權威)。顯示用文字依語言分檔:`data/cards.zh-TW.json`、`data/cards.en.json`、`data/cards.ja.json`,結構相同(卡號 → `{name, name_ja, attr, effect}`),改動只影響顯示。
- **日文 `cards.ja.json`**:由 `tools/build_card_texts.py` 自 `data/cards_ja.csv` 產生,不手動編輯;測試以同一函式(`build_ja`)重新產生並比對。
  - 魔物與夥伴的效果名不在 `attr_ja`,而是 `effect_ja` 開頭《》括起的文字,工具取第一個《》作為 `attr`。`effect` 是原文全文,所以日文效果文本身也帶著《效果名》。
- **英文 `cards.en.json`**:
  - `name` / `attr` 由同一工具自 TTS 卡表(`openspec/specs/card-data/Zatch Bell CCG List for TTS.xlsx`,「The Table」工作表)寫入,「-」為 null;同一卡號有 e / j 兩版時名稱相同,取第一筆。卡表的名稱照用,不另行修正(例:S-011 卡表寫「Ion Gravirei」)。
  - `effect` 是依 `effect_ja` 手寫的翻譯,存在檔中,工具重新執行時保留。
  - 不照抄卡表或卡圖(民間英譯版)的英文效果文:兩者與日文效果文有出入(見 `card-effects` design「行為決定與理由」),遊戲行為依日文效果文,畫面文字應與行為一致。卡表的英文只作用語參考。
  - 寫法:「」括起的卡名 / 術名改為該卡的英文 `name` 並保留引號;效果類型用規則頁的英文稱呼(Declare use →、Reduce MP by N →、Discard this card →、While this card is in play →);開頭的《效果名》省略(與中文一致,效果名已在卡名中)。用語對齊卡圖:MAMODO、SPELL、Spell Book、Power、Partner、Event、[STANDBY]、[STAY]、[COUNTER]、PROTECT、Injured、Healthy、Discard Pile、heads / tails。
- **測試**(`tests/test_i18n_languages.py`):三個檔都涵蓋 `cards.json` 全部卡號且 `name`、`effect` 非空;`name_ja` 與 `cards_ja.csv` 一致;英文 `name` / `attr` 與卡表一致;英文 `effect` 不含假名(避免漏翻)。
- **翻譯狀態**:日文為原文;英文效果文為初版翻譯,尚未經母語者校對。
