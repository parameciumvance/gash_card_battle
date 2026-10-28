## Why

`simplified-chinese`(2026-10-06)加入簡體中文時,只更新了語言選擇、i18n 字典的語言清單與 `card-data`「簡體中文卡片文字」;`battle-ui` 在那之前寫成「三種語言」的地方沒有跟著改。實作與測試早已涵蓋四種語言(`rules.zh-CN.json` 存在並由前端依語言載入,`tests/test_i18n_languages.py` 的段落與錯誤碼檢查都包含 `zh-CN`),規格文字落後。

## What Changes

- 規格改寫成「三種撰寫、一種產生」:繁體中文、英文、日文各自撰寫;簡體中文由 `tools/build_zh_cn.py` 自繁體中文轉換產生(見 `card-data`「簡體中文卡片文字」),因此四種語言的條目、段落與錯誤碼翻譯都一致。
  - `battle-ui`「規則頁的內容檔與開啟」:說明改寫;情境「三種語言段落一致」寫明比對的是繁體中文、英文、日文;新增情境「簡體中文規則頁段落一致」。
  - `battle-ui`「i18n 字典」:情境「三種語言的字典一致」寫明三種撰寫的字典與產生的簡體中文字典。
  - `battle-ui`「錯誤訊息依錯誤碼顯示」:「三種語言的字典」改為四種語言,並註明簡體中文由繁體中文產生。
- `battle-ui` 的 Purpose「中文、英文、日文三種語言的介面」改為四種語言(Purpose 不經 delta,直接改主 spec)。
- 情境名稱保留:名稱中的「三種語言」指撰寫的三種,仍然成立;OpenSpec 的 MODIFIED 也不能改情境名稱。
- 文件:`battle-ui/design.md` 規則頁段落、`README.md` 預組顯示名的在地化說明。
- 行為、程式、資料都不變。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `battle-ui`:「規則頁的內容檔與開啟」「i18n 字典」「錯誤訊息依錯誤碼顯示」的語言範圍寫明為四種(三種撰寫、簡體中文產生)。行為不變。

## Impact

- 規格:`openspec/specs/battle-ui/spec.md`(delta 與 Purpose)。
- 文件:`openspec/specs/battle-ui/design.md`、`README.md`、`todo.md`(移除此項)。
- 程式、測試、資料:不變。
