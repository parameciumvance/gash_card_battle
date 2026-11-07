# Design

## Context

- 構築規則由前端 `validateDeckPages` 即時檢查,伺服器的 `validate_deck` 為最終裁決;兩者都只看構築規則。
- 戰術的使用者由引擎 `_spell_usable_by(game, player, slot, card)` 判斷:家族相符(`family`,含 `TREATED_AS`)、`RULE_SPELL_COMPAT`(M-029:可用賈修名稱完全為「ザケル」的戰術)、`SPELL_COMPAT`(M-023 木、M-036 冰)、對局中的 `spell_compat_attr` 修正(P-029:本回合ザバス家族可用風屬性戰術)。搭檔的裝備對象由 `partner_targets` 判斷(家族相符)。

## Decisions

### D1 引擎的靜態判斷

`engine/deck.py` 的 `deck_warnings(pages, db)`:
- 以一場固定的對局(預組開局)為環境,把魔書中每張魔物卡放成假設的場上魔物,沿用 `_spell_usable_by` 判斷每張非指令戰術能不能用;家族相符與相容規則都只依卡片資料,在假設盤面上判斷準確。
- `spell_compat_attr` 是對局中由搭檔效果產生的暫時修正:掃描魔書中各卡的效果樹,找出 `AllowAttrSpellsThisTurn(mamodo, attr)`,魔書中有該家族的魔物時,把該屬性的戰術視為能使用(不提醒)。
- 搭檔:魔書中沒有家族相符的魔物時提醒(與 `partner_targets` 同一判斷)。
- 空頁略過;回傳 `[{code: "spell_no_user" | "partner_no_mamodo", page, card}]`(頁碼從 1 起)。
- 替代方案:前端依 `related_mamodo` 自行判斷。會漏掉相容規則(M-029 等)而誤報。

### D2 API 與前端

- `POST /api/decks/warnings`,body `{pages}`(可含空頁),回傳 `{warnings}`。
- 構築器每次重新驗證時以魔書內容為鍵請求(只採用最後一次請求的結果),提醒以 `.warn` 樣式列在違規之後;「魔書合法」的判斷不受提醒影響。
- 提醒不是規則:不放進 `validate_deck`,線上房與 NPC 的魔書驗證不變。

## Risks / Trade-offs

- [之後新增以其他方式讓魔物使用戰術的效果,靜態判斷不認得] → 最多是誤報提醒(不影響合法性);新增這類效果時在 `deck_warnings` 補上。
