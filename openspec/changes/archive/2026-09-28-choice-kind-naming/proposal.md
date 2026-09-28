## Why

效果樹中 `Choose` / `CoinWithPaidReflip` 的決策種類(`prompt`,也就是 pending 的 `kind` 與前端 `choice.title.<kind>` 的 key)有 31 個含卡號,例如 `e001_pick`、`m016_open`。這是效果樹遷移時為了不動前端刻意保留的過渡(見 effect-tree 的已知限制)。問題:同樣的選擇在不同卡上各有一個種類(E-001、E-006、E-009、E-015、E-019 都是「選自己的魔物」),每張新卡都要新增 i18n 標題;E-017 甚至直接借用 `e016_pick`。專案負責人決定改為依選擇內容命名,決策對話框改用通用標題並顯示來源卡。

## What Changes

- 決策種類改為依「選的是什麼」命名(如 `pick_own_mamodo`、`pick_opponent_partner`、`paid_reflip`),不含卡號;不同卡的相同選擇共用同一種類。31 個含卡號的種類併為 17 個。
- **BREAKING**(API 值):pending 與 `choice_required` 事件的 `kind` 值改變。前端與 `rooms.py` 的逾時預設同步更新;沒有外部使用者。
- 決策對話框:標題改為依種類的通用文字;有來源卡時,另外顯示來源卡的名稱與效果文。
- `frontend/i18n/zh-TW.json`:移除以卡號命名的 `choice.title.*`,加入通用標題。
- 新增測試:登記中的決策種類不含卡號、每個決策種類都有 i18n 標題、對話框顯示通用標題與來源卡。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `effect-tree`:新增「決策種類依選擇內容命名」需求。
- `battle-ui`:「操作與決策互動」加入對話框的通用標題與來源卡顯示。
- `battle-api`:「狀態快照與資訊隱藏」寫明 pending 含來源卡(`source`,既有欄位,原本 spec 未記載)。

## Impact

- 程式:`src/gash/engine/effects/tree_cards.py`(prompt 名稱)、`src/gash/api/rooms.py`(`e011_retry` 的逾時預設)、`frontend/app.js`、`frontend/index.html`、前端 CSS、`frontend/i18n/zh-TW.json`。
- 測試:引用舊種類名稱的測試(約 10 處)。
- 文件:`AGENTS.md` 的 i18n 規則、`effect-tree/design.md` 的已知限制、`openspec/changes/todo.md`。
