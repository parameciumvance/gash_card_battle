## Why

目前只有繁體中文、英文、日文。使用簡體中文的玩家只能看繁體,而且瀏覽器語言是 `zh-CN` 時也會被判為繁中。

## What Changes

- **簡體中文(`zh-CN`)**:介面字典、規則頁、卡片文字三個檔,全部由繁中自動轉換產生,不手動編輯。
  - 轉換用 OpenCC `tw2sp`(字形加上大陸用語,例如「資訊→信息」「連結→链接」),再加一張術語表:保留遊戲術語(「宣告」不轉為「声明」),修正不適合的轉換(「預設→默认」)。
  - 角色名、卡名、術名只轉字形,不改用大陸譯名(「賈修」→「贾修」)。
  - 日文原名不轉換。
- **語言選單**:「中文」改稱「繁體中文」,新增「简体中文」,順序為 繁體中文、简体中文、English、日本語。
- **自動偵測**:`zh-CN`、`zh-SG`、`zh-MY`、`zh-Hans*` → 簡中;其他 `zh`(含只有 `zh`)→ 繁中,維持現狀。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `battle-ui`:修改「語言選擇」(新增簡中、選單名稱、中文的偵測規則)、「i18n 字典」(語言清單)。
- `card-data`:新增「簡體中文卡片文字」。

## Impact

- 新工具 `tools/build_zh_cn.py`;dev 依賴加上 `opencc-python-reimplemented`(執行時不需要)。
- 新檔:`frontend/i18n/zh-CN.json`、`frontend/i18n/rules.zh-CN.json`、`data/cards.zh-CN.json`。
- 前端:`languages.json`、`app.js`(`detectLang`)。
- 測試、README。
