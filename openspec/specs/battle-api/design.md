# battle-api — 設計

目前只整理了快照中「公開 / 私有」的界線;其餘(端點、WebSocket)以 `src/gash/api/app.py` 與測試為準。

## 視角過濾的單點

- 所有送出伺服器的狀態與事件都經 `api/views.py`:`snapshot(game, viewer)` 與 `filter_events(events, viewer)`。不存在「先送全量、由前端隱藏」的路徑。
- NPC 看得到什麼也以這裡為準(見 `npc-opponent/design.md`)。

## 快照中的公開脈絡

以下欄位對所有視角相同,因為內容本來就是公開資訊:

- `pending.info`:決策的公開脈絡(目前是擲幣結果,見 `game-engine/design.md`「中途決策」)。`pending.data` 永遠不送。
- `battle.attacker_breakdown` / `defender_breakdown`:合計魔力的即時明細,內容是場上的卡、已宣告的術與已公開的效果。
- `effects`:作用中的待命與持續效果(待命在前、持續效果在後,各自依建立順序)。
  - 待命與持續效果建立時都發過公開事件(`standby_set` / `modifier_added`),所以清單本身是公開資訊。
  - 只送整理過的欄位;效果的 `data` 只挑白名單 `_PUBLIC_EFFECT_DATA` 內、型別相符的欄位(`mamodo`、`card`、`power_delta`、`cost_delta`、`optional`),續體等內部資料一律不送。
  - 新增效果種類時,若要在清單顯示額外資訊,把欄位加進白名單並確認它是公開資訊。

`choice_required` 事件對非決策者仍去除 `options` / `item` / `results`;擲幣結果另有公開的 `coin_flipped` 事件與快照的 `pending.info`。
