## Context

- 金手指面板(`frontend/app.js` 的 `CHEAT`、`renderCheatBook`)只顯示所選玩家的魔書網格,資料是 `debug-state` 的 `book` / `mp`。本機模式與 NPC 房的快照(`S`)已含雙方 `pos` 與 `consumed_pages`。
- `engine.new_game` 一律以 `game.rng.randint(0, 1)` 決定先攻並發出 `coin_flipped(source="setup")`;`api/app._start_game` 對所有模式呼叫它。
- 保護決策由 `engine._protect_choice` 建立,目前的傷害只放在 `pending.data["ctx"]` 與 `choice_required` 事件的 `item`(只給決策者)。快照的 `pending.info` 是公開脈絡(擲幣結果)。

## Goals / Non-Goals

**Goals:** 三項提示與本機模式先攻;資訊都來自公開狀態。

**Non-Goals:** 金手指仍不提供翻頁或改先攻的操作;NPC 房的先攻不變。

## Decisions

- **D1:金手指提示用快照。** 目前頁與已離開的頁取自 `S.players[p].pos` / `consumed_pages`,不擴充 `debug-state`;提示代表「目前對局狀態」,草稿修改不影響。網格頁位加 class `cheat-open` / `cheat-gone` 與小標籤,摘要放在玩家切換旁。
- **D2:指定先攻。** `new_game(..., first_player=None)`;指定時不擲硬幣,改發 `first_player_set(player, reason="local")`,記錄「自由調查時間:玩家 1 先攻」。`_start_game` 在 `room.mode == "local"` 時傳 0。保留 `coin_flipped(source="setup")` 給其他模式,既有的特性測試不受影響。
- **D3:保護的公開脈絡。** `_protect_choice` 建立決策時設 `pending.info = {"damage": {...}}`:`kind`(book / slot)、`player`、`amount`、`slot`、`injured`、`lethal`(魔書時 `pos + 2 * amount > BOOK_SIZE`,與受傷時的判負條件一致)。`info` 原本就對所有視角公開。
- **D4:前端。** 保護決策的提示在標題下加一行傷害說明(`choice.protect_damage.*`),魔物名以 `cname`、玩家以 `pname`。

## Risks / Trade-offs

- [`lethal` 只看這一份傷害] → 多份傷害時(S-036 等)後面的份數也可能耗盡魔書;只標示目前這一份,和「只顯示目前這一份」一致。
