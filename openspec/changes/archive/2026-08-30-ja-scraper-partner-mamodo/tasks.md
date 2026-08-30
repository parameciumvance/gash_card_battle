## 1. 規格

- [x] 1.1 `card-data` 的「日文權威資料抓取(atwiki)」需求擴充尾行解析規則(夥伴卡「魔物＝X」、明確記錄魔物/事件卡的決定)

## 2. 腳本

- [x] 2.1 `tools/scrape_ja_effects.py` 新增 `PARTNER_TAIL_RE = re.compile(r'^魔物＝(.+)$')`
- [x] 2.2 `parse_card_page` 依 `type_` 分派尾行判斷:術卡用既有 `SPELL_TAIL_RE`,夥伴卡用 `PARTNER_TAIL_RE`,其餘類型不檢查尾行

## 3. 測試

- [x] 3.1 新增夥伴卡測試:最後一行為「魔物＝X」時正確解析 related_mamodo_ja 並排除於效果文外
- [x] 3.2(改為 3.6 的必填欄位報錯測試,見下——原「不符合格式時留空」的行為已改為必填報錯)
- [x] 3.3 確認既有術卡尾行測試與魔物卡測試不受影響(不自動解析 related_mamodo_ja);另以真實頁面 ref/341.html(P-001)核對正確解析出「ガッシュ・ベル」
- [x] 3.4 執行 `python -m pytest` 確認全數通過(190 passed)

## 4. 收尾

- [x] 4.1 執行 `openspec validate ja-scraper-partner-mamodo` 確認格式正確

## 5. 實際整批抓取後發現的擴大範圍(指示術/無連結魔物名/必填欄位/P-018)

- [x] 5.1 `SPELL_TAIL_RE` 改為 `[^。]+?第(\d+)の?術$` + `.search()`:同時支援連結包住與純文字兩種魔物名寫法,且能在尾段與前一句效果文黏同一行時正確切分(只切最後一個句號之後的段落)
- [x] 5.2 新增 `COMMAND_SPELL_TAIL`/`COMMAND_SPELL_TAIL_RE`:術卡尾段為「コマンド」時,related_mamodo_ja 存為「コマンド」(指示術,對應英文 `Command: All`)
- [x] 5.3 `related_mamodo_ja` 改為術卡/夥伴卡必填欄位:尾行解析完成後檢查,解析不出時查 `KNOWN_DATA_GAPS`,否則 raise
- [x] 5.4 `KNOWN_DATA_GAPS` 新增 `P-018: {"related_mamodo_ja": "ヨポポ"}`(頁面尾行寫成「パートナー＝X」而非「魔物＝X」)
- [x] 5.5 補測試:無連結魔物名、指示術、尾段黏同行的切分、已知缺漏覆寫(P-018)、術卡/夥伴卡缺 related_mamodo_ja 報錯
- [x] 5.6 移除/更新因新規則失效的舊測試(夥伴卡「無尾行→留空」的測試已由「無尾行且未登記→報錯」取代)
- [x] 5.7 執行 `python -m pytest` 確認全數通過(194 passed)
- [x] 5.8 提醒使用者:`data/cards_ja.csv` 中受影響的 12 張術卡(指示術 6 張 + 未連結魔物名 7 張,扣除重複)`effect_ja` 已被舊程式誤黏尾行文字,需刪除舊檔整批重新抓取

## 6. 魔物卡對應搭檔(related_partner_ja)

- [x] 6.1 `FIELDNAMES` 新增 `related_partner_ja`
- [x] 6.2 新增 `PARTNER_NAME_TAIL_RE = re.compile(r'^パートナー＝(.+)$')`,`parse_card_page` 對魔物卡分派此判斷式
- [x] 6.3 `related_partner_ja` 加入必填欄位檢查(`REQUIRE_RELATED_PARTNER = {"mamodo"}`),沿用 5.3 的 `require_tail_field` 共用邏輯(查 `KNOWN_DATA_GAPS`,否則 raise)
- [x] 6.4 用真實頁面 ref/301.html(M-001)核對,正確解析出「高嶺清麿」
- [x] 6.5 補測試:魔物卡解析出 related_partner_ja、缺漏時報錯
- [x] 6.6 執行 `python -m pytest` 確認全數通過(195 passed)
- [x] 6.7 提醒使用者:`data/cards_ja.csv` 需重新整批抓取以補上新欄位 `related_partner_ja`(既有魔物卡資料列缺此欄位)

## 7. 框線規則卡的多段 <div>(M-007/M-010/M-024/M-027/M-029)

- [x] 7.1 用真實頁面 ref/M-007.html、ref/M-029.html 核對,確認資料區塊實際為 4 段 `<div>`(3 個 `<hr/>`),原因是卡面多印一段框線規則(變身疊放條件/術相容性規則)
- [x] 7.2 `BLOCK_RE` 改為 `BLOCKQUOTE_RE` + `DIV_RE`:不限定段數,取第一段當資料頭來源、最後一段當風味文來源,中間任意段數併入效果文
- [x] 7.3 新增 `FRAME_NOTE = "以上、枠囲み"` 常數,過濾這個純排版提示段落,不併入效果文
- [x] 7.4 用真實頁面核對修正後 related_partner_ja 正確解析出「連次」(M-007)、「デュフォー」(M-029),框線規則文字與《能力》效果文皆完整保留
- [x] 7.5 補回歸測試:框線規則卡(4 段 <div>)的中間段落正確併入效果文、排版提示被濾掉、related_partner_ja 從最後一段解析
- [x] 7.6 執行 `python -m pytest` 確認全數通過(196 passed)
- [x] 7.7 提醒使用者:`data/cards_ja.csv` 需再次整批重新抓取,補上這 5 張卡(以及可能存在的同類卡片)
