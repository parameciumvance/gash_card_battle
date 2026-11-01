# Design

## Context

- 放大檢視的按鈕由 `zoomActions` → `slotButtons` / `partnerButtons` / `borrowedButtons` / `pageButtons` 產生,停用時 `reason` 直接顯示在按鈕旁(觸控沒有 hover)。可用卡發光(`markUsable`)只看啟用的按鈕。
- 效果的使用驗證在 `_use_field_ability` / `_use_borrowed_effect`;放出可否已有 `play_block` 模式(快照只給持有者)。
- 「行動權」(是不是輪到自己、是否在等決策)由 `submit` 檢查,與卡片本身無關。

## Decisions

### D1 `ability_block` 由引擎判斷,指令共用

`ability_block(game, player, zone, slot, number)` 依指令原本的順序回傳第一個不符合的代碼:`partner_restricted`、`mamodo_locked` / `mamodo_restricted`、`timing_battle`、`timing_nonbattle`、`own_turn`、`used`、`per_game`、`mp`、`condition`。`in_battle` 以 `state.battle is not None` 判斷,與指令相同。`_use_field_ability` / `_use_borrowed_effect` 改為呼叫它,再把代碼對回原本的錯誤碼(三種時機都對回 `ability.timing`),錯誤碼與訊息不變。借用效果沒有 `used` / `per_game`(有自己的使用標記),`slot` 為 None。

### D2 只給持有者

使用條件可能看非公開資訊(例如自己的魔書),所以 `ability_block` 與 `borrowed_block` 只在持有者本人(含本機的全視角)的快照中出現,比照 `play_block`。按鈕也只對操作的一方顯示。

### D3 前端原因的順序

1. 卡本身的原因(`ability_block`,沒有欄位時退回既有的 `*_used` 判斷)。
2. 卡本身可用時,說明現在的時機:等待決策「請先完成目前的選擇」、開始階段「戰鬥階段才能使用」、戰鬥中未到效果步驟「戰鬥的效果步驟才能使用」、不是自己行動「輪到你行動時才能使用」。
這樣「只能在戰鬥中使用」這類固定的限制優先,玩家先知道卡的用法。MP 不足一律用 `ui.spell.mp`(「MP 不足(目前 m,需要 n)」)。

### D4 翻開頁的停用按鈕

`pageButtons` 在 `canActNow` 不成立時(且不是防禦步驟的防方使用防禦戰術)為卡的主要動作加停用按鈕:
- 魔物 / 搭檔「放出」、事件卡與非戰鬥戰術「使用」:原因為 D3 第 2 點的時機;戰鬥中為「非戰鬥中才能使用」。
- 攻擊戰術(A / AD)由回合玩家看:「攻擊」停用,原因同上。
- 只有防禦圖示(D)的戰術,以及非回合玩家的 AD 戰術:「防禦」停用,「對手攻擊時才能用來防禦」;能行動時也一樣加上(原本沒有按鈕)。非回合玩家的 AD 戰術不顯示「攻擊」,因為對它來說防禦才是會用到的動作。
- 只有攻擊圖示(A)的戰術由非回合玩家看:「攻擊」停用,「只能在自己的回合攻擊」。
只對 `iControl(p)` 的一方;發光照舊只看啟用的按鈕,盤面不會多出提示。

## Risks / Trade-offs

- 快照每次為每張有效果的場上卡評估使用條件:條件函式是純查詢,場上最多 3 隻魔物與搭檔,成本可忽略。
- 放大檢視多了停用按鈕:只在玩家主動點開時出現。
