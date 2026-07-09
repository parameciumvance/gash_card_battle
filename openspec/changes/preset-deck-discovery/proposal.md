## Why

新增一個預組魔本目前要改 5 處、其中 3 處是程式碼:資料檔 `data/decks/*.json`、`app.py` 的 `_resolve_deck` 硬編只認 `level1`、`app.js` 的 `deckOptions`/`deckPayload` 硬編單一 `"preset"` 選項值、i18n 的 `ui.deck.preset_*` label(還和牌組 JSON 自帶的 `name_key` 重複)。預組本質是資料,卻被 Python、JS、i18n 三種語言各手動列舉一次。癥結是預組沒有被「探索」而是被「列舉」。改成資料驅動探索後,新增預組縮成「丟一個 JSON 檔」。

## What Changes

- **新增探索端點 `GET /api/decks`**:伺服器掃描 `data/decks/*.json`,回傳 `[{id, name}]`(可快取)。顯示名解析:牌組 JSON 有 `name_key` 就經 i18n 字典解析,否則用內嵌 `name` 字串 —— 純丟檔即可運作,要在地化再補 `name_key`。
- **`_resolve_deck` 一般化**:`{preset: id}` 依 id 載入 `data/decks/<id>.json`;id MUST 限縮在掃描到的集合(白名單,防路徑穿越);未知 id 回 4xx。`{pages:[...]}` 自訂牌組驗證邏輯不變。預設仍為 level1。
- **前端改為消費探索清單**:`deckOptions` 動態生成每個預組的 `<option>`(value=預組 id)、`deckPayload` 送 `{preset: id}`、構築器「從預組複製起手」清單同源、`boot()` 抓探索清單而非硬編 `level1.json`。
- **不變**:構築器產品過濾(依 `cards.json` 的 `sets`)、自訂牌組匯出入、七條構築規則、引擎。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `battle-api`: 新增 `GET /api/decks` 預組探索端點;`_resolve_deck` 由「只認 level1」一般化為「依 id 載入掃描集合內的具名預組」,含白名單防護。
- `battle-ui`: 首頁與構築器的預組來源由硬編改為消費 `GET /api/decks` 動態清單;預組顯示名支援 `name_key`(i18n)或內嵌 `name` fallback。

## Impact

- 受影響程式碼:`src/gash/api/app.py`(新增端點、`_resolve_deck`/`_default_deck` 改為具名載入+快取白名單)、`frontend/app.js`(`deckOptions`/`deckPayload`/`renderNewSelect`/`boot`)、`data/decks/level1.json`(補 `name` 或確認 `name_key` 可解析)。
- 不影響:引擎、`api/rooms.py`、`api/views.py`、構築器規則與產品過濾、既有 `level1` 預組行為。
- 淨效果:新增預組 5 處 → 1 處(要在地化 2 處)。
