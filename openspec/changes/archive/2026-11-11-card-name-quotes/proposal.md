## Why

行動記錄等文字以《》括住卡名,但魔物卡名本身帶效果名(`ui.card_with_attr`「{name}《{attr}》」),出現《布拉葛《嘲笑》》這種巢狀括號。使用者 2026-11-11 決定:卡名與戰術名一律改用「」,《》只留給效果名。

## What Changes

- 介面文字範本中括住卡名的 `{card}`、`{spell}`、`{source}`:zh-TW(zh-CN 隨之產生)與 ja 由《》改為「」,en 由《》改為 “ ”。
- `frontend/app.js` 直接寫《${cname(n)}》的 4 處改用翻譯範本。
- 不變:效果名的《》(`ui.card_with_attr`、《格闘》)、魔書名的《》(`builder.new_from_deck`)、場上魔物的〔〕。
- 守門測試:範本中的卡名佔位符不可被《》括住。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `battle-ui`:修改「使用魔書中卡片的記錄」「效果被擋下的記錄與聚焦」的記錄格式;新增「卡名的括號」。

## Impact

- 前端:`frontend/i18n/*.json`、`frontend/app.js`;相關瀏覽器測試的預期文字。
