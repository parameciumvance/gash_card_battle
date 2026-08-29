## Why

`data/cards.json` 中 S-017(ゼルセン/澤爾森)的 `effect_en` 記載自身魔力加值於「以此術**防禦**時」觸發(+2000),與 S-016(ゼルク)同款 handler。但核對權威來源試算表(`openspec/specs/card-effects/Zatch Bell CCG List for TTS.gsheet`)後,官方原文其實是「When **Attacking**, add 2000 Power to this SPELL card.」——目前的資料與程式行為是抽取/轉錄時的錯誤,不符合官方效果文,須修正。

## What Changes

- 修正 S-017 卡片效果的觸發時機:自身魔力加值(+2000)改為「以此術攻擊時」觸發,不再於防禦時觸發;香草的「攻擊方獲勝時對魔本造成傷害」效果不變。
- 修正 `data/cards.json` 的 `effect_en` 與 `data/cards.zh-TW.json` 的中文效果文本,使其與官方試算表一致。
- 修正 `src/gash/engine/effects/spells.py` 中 S-017 的 `spell_rider` 註冊:不再與 S-016 共用「防禦時加值」handler,改為攻擊宣告時加值。
- 更新 `tests/test_cards.py` 中涉及 S-017 的測試案例,驗證加值改於攻擊方觸發、防禦方不再觸發。
- **BREAKING**:S-017 的實際規則行為改變(修正 bug),先前依賴「防禦時 +2000」誤植行為設計魔本的玩家需重新評估此卡用法。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `card-effects`:「第一彈 67 種卡全數可用」需求文字不變,新增 S-017 的專屬情境,鎖定其修正後(攻擊時加值)行為以符合既有「行為與日版(j)效果文一致」需求。

## Impact

- `data/cards.json`:S-017 的 `effect_en` 文本(修正抄錄錯誤)
- `data/cards.zh-TW.json`:S-017 的中文 `effect` 文本
- `src/gash/engine/effects/spells.py`:S-017 的 spell_rider 註冊邏輯(改為攻擊時加值)
- `tests/test_cards.py`:S-017 相關測試案例
