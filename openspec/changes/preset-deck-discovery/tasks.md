## 1. 後端探索與解析

- [x] 1.1 掃描 `data/decks/*.json` 建 `{id: path}` 對照表與清單快取(啟動時、壞檔排除記 log)
- [x] 1.2 顯示名解析器:`name_key`(讀 i18n 字典)→ 內嵌 `name` → `id` fallback
- [x] 1.3 新增 `GET /api/decks` 端點回 `[{id, name}]`(依 id 穩定排序,level1 可置頂)
- [x] 1.4 `_resolve_deck` 一般化:`{preset:id}` 查對照表載入(白名單,未知 id 回 4xx);`_default_deck` 改讀 `DEFAULT_PRESET`;`{pages}` 驗證不變

## 2. 資料

- [x] 2.1 `data/decks/level1.json` 補內嵌 `name`(保留 `name_key`),確認擇一都能顯示

## 3. 前端消費

- [x] 3.1 `boot()` 抓 `GET /api/decks` 存入 PRESETS;複製起手來源改為按需抓 `/data/decks/<id>.json`
- [x] 3.2 `deckOptions` 遍歷 PRESETS 動態生成選項;`deckPayload` 依「值是否為預組 id」回 `{preset:id}` 或 `{pages}`
- [x] 3.3 構築器 `renderNewSelect` 的「從預組複製」清單改為遍歷 PRESETS
- [x] 3.4 移除硬編 `ui.deck.preset_level1` 依賴(label 改用探索清單的 name)

## 4. 驗證

- [x] 4.1 端點單元測試:列出含 level1、丟入臨時預組檔即現、壞檔被排除
- [x] 4.2 安全測試:`{preset:"../.."}` 等惡意 id 被拒 4xx、不讀任意檔
- [x] 4.3 回歸:既有 `{preset:"level1"}` 與缺省牌組行為不變(全量 pytest 綠)
- [x] 4.4 前端 E2E:牌組選單自探索清單正確渲染、選預組能開局、構築器複製起手正常
