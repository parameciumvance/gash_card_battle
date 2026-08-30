## Why

`tools/scrape_ja_effects.py` 目前只有術卡能解析出 `related_mamodo_ja`(從「XX第N の術」尾行)。夥伴卡(パートナー)也需要這個欄位——之後要把 `related_mamodo` 這個引擎識別鍵改用日文,夥伴卡跟術卡一樣都要能對應回綁定的魔物。用真實頁面(P-001 高嶺清麿,`ref/341.html`)核對過夥伴卡的資料區塊格式,規律跟術卡的「第N の術」尾行是同一種設計,只是判斷式不同(「魔物＝X」)。

## What Changes

- 新增夥伴卡的尾行解析:資料區塊最後一行若符合「魔物＝<名字>」(純文字,無連結)格式,MUST 解析為 `related_mamodo_ja` 並排除於效果文之外——比照術卡「第N の術」的既有機制,只是判斷式與適用類型不同。
- **明確決定,不是留白待補**:魔物卡的 `related_mamodo_ja`(對應魔物身分)一律不自動填值(不論基本形態或變身形態),包含基本形態也不自我參照(不預設等於自己的 name_ja)。這個身分之後若要用,由人工從效果內文判斷,腳本不做自動推論。
- **明確決定**:事件卡不需要 `related_mamodo_ja`(對照英文資料確認事件卡本身沒有這個概念,`related_mamodo` 恆為 null)。
- 實作/測試過程中發現並修正:術卡尾行的「指示術(コマンド)」與「魔物名無連結」兩種真實格式(見 design.md);`related_mamodo_ja` 改為術卡/夥伴卡必填欄位,搭配既有的 `KNOWN_DATA_GAPS` 機制處理個案(P-018)。
- **新增魔物卡必填欄位 `related_partner_ja`**(對應綁定的人類搭檔,與夥伴卡的「魔物＝X」鏡像對稱):資料區塊最後一行若符合「パートナー＝<名字>」格式,MUST 解析為 `related_partner_ja` 並排除於效果文之外;魔物卡 MUST 有此欄位,解析不出時查 `KNOWN_DATA_GAPS`,否則 raise。用真實頁面(M-001 ガッシュ・ベル,`ref/301.html`)核對過此格式。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `card-data`:「日文權威資料抓取(atwiki)」需求擴充尾行解析規則,新增夥伴卡的「魔物＝X」、魔物卡的「パートナー＝X」格式,術卡尾行支援指示術與無連結魔物名;`related_mamodo_ja`(術卡/夥伴卡)與 `related_partner_ja`(魔物卡)皆為必填欄位。

## Impact

- `tools/scrape_ja_effects.py`:新增 `PARTNER_TAIL_RE`/`PARTNER_NAME_TAIL_RE`/`COMMAND_SPELL_TAIL_RE`,`SPELL_TAIL_RE` 改寫為可跨行黏合切分,`parse_card_page` 依類型分派尾行判斷式並統一必填欄位檢查(`require_tail_field` 輔助函式)
- `tests/test_scrape_ja_effects.py`:新增夥伴卡/魔物卡尾行解析測試,含指示術、無連結魔物名、黏同行切分、必填欄位報錯、已知缺漏覆寫等情境
- `openspec/specs/card-data/spec.md`:擴充既有需求的尾行解析規則段落
- `data/cards_ja.csv`:欄位新增 `related_partner_ja`,且受術卡尾行修正影響的卡片 `effect_ja` 需重新抓取(見 tasks.md)
