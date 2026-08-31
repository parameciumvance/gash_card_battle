## Context

現況:`data/decks/level1.json`(欄位 `id` / `name_key` / `source` / `pages`)是唯一預組。三處硬編:
- `app.py` `_default_deck()` 讀死 `decks/level1.json`;`_resolve_deck()` 只在 `preset == "level1"` 回 `None`(=用預設)。
- `app.js` `deckOptions()` 塞一個 `value="preset"` 的 `<option>`,label 取 `t("ui.deck.preset_level1")`;`deckPayload()` 把 `"preset"` 映射成 `{preset:"level1"}`;`boot()` 直接 `fetch("/data/decks/level1.json")` 存入 `LEVEL1` 供構築器複製。
- i18n `ui.deck.preset_level1` 與牌組 JSON 的 `name_key` 重複表達同一個名字。

`/data` 已靜態掛載;`load_deck(path, db)` 讀檔並 `validate_deck`。

## Goals / Non-Goals

**Goals:**
- 新增預組 = 丟一個 `data/decks/<id>.json`,零程式碼改動即出現在首頁選單與構築器複製清單。
- 保留 i18n 一致性的路徑(可選 `name_key`),但不強制。
- 安全:請求帶的預組 id 絕不轉成任意檔案路徑。

**Non-Goals:**
- 預組的線上管理/上傳 UI(仍是開發者丟檔)。
- 構築器產品過濾、自訂牌組、引擎邏輯。

## Decisions

### D1. 探索端點 `GET /api/decks`

- 伺服器掃描 `DATA_DIR/decks/*.json`,對每檔解析 `id` 與顯示名,回傳 `[{"id": ..., "name": ...}]`,依 id 穩定排序(level1 置頂或字典序)。
- **顯示名解析**:`name_key` 存在 → 以伺服器端 i18n 字典(`frontend/i18n/zh-TW.json`)解析;解析不到或無 `name_key` → 用內嵌 `name`;再無 → 退回 `id`。
- **快取**:啟動時掃一次建 `{id: path}` 對照表與清單並快取(檔案在部署期不變);端點直接回快取。
- 掃描時對每檔做基本合法性檢查(能 `load_deck`),壞檔記 log 並排除,不讓整個端點掛掉。

### D2. `_resolve_deck` 一般化 + 白名單

- `{preset: id}`:`id` MUST ∈ 掃描集合(D1 的對照表 key);命中 → `load_deck(對照表[id])`;未命中 → `HTTPException(400/404, code="deck.unknown_preset")`。
- 因為 id 只用來查對照表、never 拼進路徑,天然免疫 `../` 路徑穿越。
- `spec is None` 或 `{preset:"level1"}` → 仍回 `None`(語意=用預設);`_default_deck()` 改為 `load_deck(對照表["level1"])`,預設 id 定為常數 `DEFAULT_PRESET="level1"`。
- `{pages:[...]}` 自訂牌組:驗證與 422 行為完全不變。

### D3. 前端消費探索清單

- `boot()`:`fetch("/api/decks")` 取得清單,存入模組變數(如 `PRESETS`);同時保留抓 level1 pages 供構築器複製(改為抓 `DEFAULT_PRESET` 或按需抓各預組 pages)。
- `deckOptions(sel)`:遍歷 `PRESETS`,每個預組一個 `<option value=preset:<id>>`(或 value 帶 id、另存 dataset 標記為 preset),label=清單提供的 `name`。自訂牌組選項邏輯不變。
- `deckPayload(selectId)`:值為預組時回 `{preset: id}`;為自訂牌組 id 時回 `{pages}`。以「值是否在 PRESETS 集合」區分,不再靠字面 `"preset"`。
- 構築器 `renderNewSelect()`「從預組複製起手」:遍歷 `PRESETS` 生成複製選項;選取時抓該預組 pages(可 `GET /data/decks/<id>.json` 或探索端點附帶 pages)。

### D4. 牌組 JSON 顯示名欄位

- `level1.json` 補一個內嵌 `name`(如「賈修+蒂歐+凱喬美」)作為 fallback,並保留 `name_key`;確認兩者擇一都能正確顯示。
- 新預組作者:最省 = 只寫 `name`;要多語 = 加 `name_key` 並在各 `i18n/<lang>.json` 補條目。

## Risks / Trade-offs

- [伺服器端讀 i18n 字典以解析 name_key] → 字典是靜態 JSON,啟動時載入快取即可;解析失敗 fallback 到 `name`/`id`,不阻斷。
- [掃描目錄的效能/穩定性] → 啟動時掃一次並快取;壞檔排除而非整體失敗。
- [前端如何區分「預組」與「自訂牌組」選項] → 以 PRESETS 的 id 集合判定;避免與 localStorage 牌組 id 撞名(預組 id 來自檔名,自訂 id 為隨機碼,實務不衝突;必要時 value 加 `preset:` 前綴明確化)。
- [既有前端行為回歸] → level1 仍在清單、仍為預設、仍可複製;E2E 覆蓋牌組選單渲染與開局。

## Migration Plan

單一變更內:後端(端點+對照表+`_resolve_deck`)→ `level1.json` 補 `name` → 前端(boot/deckOptions/deckPayload/renderNewSelect)→ 測試。無資料遷移;既有 `{preset:"level1"}` 請求與 level1 行為完全相容。

## Open Questions

- 探索端點是否一併回傳每個預組的 `pages`(讓構築器複製免二次請求)?先只回 `{id, name}`,構築器複製時再抓 `/data/decks/<id>.json`;若嫌多一跳再合併。
