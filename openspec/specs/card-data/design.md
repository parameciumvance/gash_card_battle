# card-data — 設計

目前整理了卡片文字檔(顯示用的多語文字)與卡圖格式;抓取、`cards.json` 轉換以 `tools/` 程式、README「資料管線」與測試為準。

## 卡片文字檔

- **分層**:遊戲邏輯只讀 `data/cards.json`(日文權威)。顯示用文字依語言分檔:`data/cards.zh-TW.json`、`data/cards.zh-CN.json`、`data/cards.en.json`、`data/cards.ja.json`,結構相同(卡號 → `{name, name_ja, attr, effect}`),改動只影響顯示。
- **日文 `cards.ja.json`**:由 `tools/build_card_texts.py` 自 `data/cards_ja.csv` 產生,不手動編輯;測試以同一函式(`build_ja`)重新產生並比對。
  - 魔物與搭檔的效果名不在 `attr_ja`,而是 `effect_ja` 開頭《》括起的文字,工具取第一個《》作為 `attr`。`effect` 是原文全文,所以日文效果文本身也帶著《效果名》。
- **英文 `cards.en.json`**:
  - `name` / `attr` 由同一工具自 TTS 卡表(`openspec/specs/card-data/Zatch Bell CCG List for TTS.xlsx`,「The Table」工作表)寫入,「-」為 null;同一卡號有 e / j 兩版時名稱相同,取第一筆。卡表的名稱照用,不另行修正(例:S-011 卡表寫「Ion Gravirei」)。
  - `effect` 是依 `effect_ja` 手寫的翻譯,存在檔中,工具重新執行時保留。
  - 不照抄卡表或卡圖(民間英譯版)的英文效果文:兩者與日文效果文有出入(見 `card-effects` design「行為決定與理由」),遊戲行為依日文效果文,畫面文字應與行為一致。卡表的英文只作用語參考。
  - 寫法:「」括起的卡名 / 戰術名改為該卡的英文 `name` 並保留引號;效果類型用規則頁的英文稱呼(Declare use →、Reduce MP by N →、Discard this card →、While this card is in play →);開頭的《效果名》省略(與中文一致,效果名已在卡名中)。用語對齊卡圖:MAMODO、SPELL、Spell Book、Power、Partner、Event、[STANDBY]、[STAY]、[COUNTER]、PROTECT、Injured、Healthy、Discard Pile、heads / tails。
- **簡體中文**:`tools/build_zh_cn.py` 把繁中的卡片文字、介面字典、規則頁三個檔轉成簡中,不手動編輯;測試以同一函式(`build()`)重新產生並比對,繁中改了沒重跑就會失敗。
  - 轉換:OpenCC `tw2sp`(字形 + 大陸用語,例如「圖示→图标」「連結→链接」「咖哩→咖喱」)。轉換前把 `TERMS` 的詞換成私用區佔位字元,轉換後換回指定寫法:保留遊戲術語「宣告」(不轉為「声明」),修正誤轉(「進階→高端」、「顯示」被斷詞、「複製→拷贝」、「文字→文本」),替換「預設→默认」「帳號→账号」。
  - 譯名只轉字形(賈修・貝爾→贾修・贝尔),使用者決定先不改用大陸譯名;之後要換譯名時加進 `TERMS`。
  - `name_ja` 不轉換:日文漢字會被改掉。`app.title` 不轉換:網站名稱是專有名稱,各語言相同。
  - `opencc-python-reimplemented` 只是 dev 依賴,執行時不需要。OpenCC 詞典升級可能改變輸出,同步測試會抓到,檢查差異後重跑工具。
- **測試**(`tests/test_i18n_languages.py`):三個檔都涵蓋 `cards.json` 全部卡號且 `name`、`effect` 非空;`name_ja` 與 `cards_ja.csv` 一致;英文 `name` / `attr` 與卡表一致;英文 `effect` 不含假名(避免漏翻)。
- **翻譯狀態**:日文為原文;英文效果文為初版翻譯,尚未經母語者校對;簡體中文是自動轉換,尚未校對。

## 卡圖

- **格式**:WebP q80(有損、保留透明通道),檔名 `{卡號}.webp`,尺寸與原圖相同(465×679)。系統只認這一種格式:前端的 `artUrl()`、`/api/meta` 的張數、下載工具的續抓都只看 `.webp`。
  - 原圖是 RGBA PNG,四角透明做圓角,所以不能用 JPEG。
  - 135 張實測:原圖約 90MB;q80 約 11MB(每張約 83KB),q88 約 15MB,無損每張約 460KB。效果文區塊放大兩倍比對,q80 與原圖看不出差別。
  - 不支援其他格式並存:換格式時所有環境重新下載,不在執行時轉換或退回舊格式。
- **轉檔位置**:`tools/download_images.py` 下載原圖後在記憶體中轉成 WebP(`to_webp()`),原圖不落地。`pillow` 只是 dev 依賴,執行環境(映像檔)不需要。
- **測試**(`tests/test_download_images.py`):轉檔保留尺寸與透明圓角;續抓只跳過已有 `.webp` 的卡。以假的下載函式代替 Google Drive,不連網。
