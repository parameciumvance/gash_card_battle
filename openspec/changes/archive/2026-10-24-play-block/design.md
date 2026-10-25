# Design

## Context

`_play_card`(`src/gash/engine/engine.py`)在執行途中逐項檢查並拋出 `IllegalCommand`:魔物依序為 `spell_only` → `no_base`(疊放型)或 `field_full` → `same_name`(非疊放型);搭檔為 `no_mamodo` → `partner_exists` → `same_name`。快照(`api/views.py` 的 `_player_view`)只對戰術 / 事件頁附 `cost`、`users`、`condition_ok`,魔物與搭檔頁只有頁碼與卡號。前端 `pageButtons` 對魔物不判斷,搭檔以 `partnerTargets` 用 `CARDS[slot.top].related_mamodo` 比對,與引擎的 `family()`(M-047 視為ガッシュ・ベル)不一致。

## Goals / Non-Goals

**Goals:**
- 放出可否只在引擎判斷一處,指令與快照結果一致。
- 前端不再自行推論搭檔的對應。

**Non-Goals:**
- 時機判斷(`canActNow`、戰鬥中)維持前端既有寫法。
- NPC 候選不改:它們本來就交給引擎驗證,非法候選會被濾掉。

## Decisions

- **查詢函式回傳錯誤碼,不拋例外。** 新增 `play_block(game, player, number) -> str | None` 與 `partner_targets(game, player, card) -> list[MamodoSlot]`;`_play_card` 先呼叫 `play_block`,有錯誤碼就 `raise IllegalCommand(f"play.{code}", ...)`,其後只做放出。替代方案是讓 views 以 try/except 呼叫 `_play_card` 於複製的狀態上——成本高且有副作用風險,不採用。
- **搭檔指定 `slot_uid` 的驗證留在 `_play_card`。** `play_block` 只回答「有沒有任何可裝備的對象」;指令指定的 slot 不在 `targets`(或已裝搭檔)時仍由 `_play_card` 回 `partner_exists` / `no_mamodo`,錯誤碼不變。
- **錯誤碼順序沿用現狀**,讓既有測試的錯誤碼斷言不變。搭檔:沒有對應魔物 → `no_mamodo`;有對應但都已裝 → `partner_exists`;同名搭檔在場 → `same_name`。
- **前端原因文字沿用 `error.play.*`**,不新增 `ui.play.*` 鍵;原有的 `ui.play.no_mamodo` / `ui.play.partner_exists` 不再使用時刪除(含 zh-CN 由 `tools/build_zh_cn.py` 重建)。
- **欄位只給持有者視角**(`can_see_player`),與 `users`、`condition_ok` 相同;本機測試模式兩邊都看得到。

## Risks / Trade-offs

- [`play_block` 與 `_play_card` 的實際放出條件日後被改到其中一邊] → `_play_card` 只透過 `play_block` 判斷,不保留重複檢查;測試同時斷言快照欄位與指令錯誤碼。
- [快照多了每頁一次的查詢] → 翻開頁最多 2 頁(加上檢視),成本可忽略。
