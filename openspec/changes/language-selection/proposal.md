## Why

遊戲只有中文介面,日文與英文使用者無法遊玩。日文卡片文字(權威來源)與英文卡名(`card-data` 的 TTS 卡表)其實都已在 repo 中,介面文字也已集中在字典,缺的是語言切換與日、英兩種語言的內容。

## What Changes

- **語言選擇**:支援中文(zh-TW)、English(en)、日本語(ja)。第一次開啟時依瀏覽器語言決定(ja → 日本語、zh → 中文、其他 → English);頂欄提供「🌐」按鈕切換,選項以各自的語言標示,首頁與對局中都可用;選擇記在瀏覽器。對局中切換時重新載入頁面並接回對局,行動記錄以新語言重建。
- **介面字典**:新增 `frontend/i18n/en.json`、`ja.json`,條目與 `zh-TW.json` 一致。日文採規則書用語,英文對齊卡圖用語(MAMODO、Spell Book、Power…)。
- **規則頁**:新增 `rules.en.json`、`rules.ja.json`,段落與中文版一致。
- **卡片文字**:
  - 日文:新增 `data/cards.ja.json`,由 `data/cards_ja.csv` 以工具產生(卡名、效果名、效果全文皆為原文)。
  - 英文:新增 `data/cards.en.json`,卡名與效果名取自 TTS 卡表;效果全文**自日文效果文翻譯**(不照抄卡表或卡圖的英文,兩者與效果文有出入)。
  - 卡名下方的小字:中文、英文模式顯示日文原名,日文模式不顯示。
- **錯誤訊息**:前端依伺服器回應的錯誤碼(約 88 種)查字典顯示;字典沒有時才顯示伺服器原文。伺服器不變。
- **預組牌組名稱**:`GET /api/decks` 另回傳 `name_key`,前端依目前語言解析。
- **字型**:日文模式改用日文字型,`<html lang>` 隨語言切換。
- 日文與英文為**初版翻譯,尚未經母語者校對**,於 README 與 design 註明。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `battle-ui`:修改「i18n 字典」(三種語言的字典與卡片文字)、「行動記錄」(依目前語言渲染)、「規則頁」(三種語言);新增「語言選擇」「錯誤訊息依錯誤碼顯示」。
- `deck-builder`:修改「即時合法性提示」(以目前語言顯示)。
- `card-data`:新增「日文與英文卡片文字」(`cards.ja.json` 產生方式、`cards.en.json` 的來源與翻譯依據)。
- `battle-api`:修改「預組魔本探索」(回應含 `name_key`)。

## Impact

- 前端:`frontend/app.js`(語言偵測與切換、字典 / 規則 / 卡片文字依語言載入、錯誤碼對應)、`index.html`、`style.css`(語言按鈕、日文字型)、`frontend/i18n/` 新增 4 個檔案、`zh-TW.json` 補錯誤碼與牌組名稱。
- 資料:`data/cards.ja.json`、`data/cards.en.json`;新增產生 `cards.ja.json` 的工具。
- 伺服器:`/api/decks` 回應多一個欄位;錯誤訊息不變。
- 測試:瀏覽器測試固定中文(`locale="zh-TW"`);新增字典、卡片文字、規則頁三語一致性檢查與語言切換的瀏覽器測試。
- 文件:README。
