# Design

## Context

- `side_breakdown(game, battle, side)` 由 `BattleState` 算一方的合計魔力與明細:戰術魔力(含 `battle.data` 的戰鬥中加成)、屬性加成、常駐戰術加成、依名稱的加成、魔物魔力(`power_breakdown`)、合計加成、S-089 的借用魔力、無效化。
- 快照 `_spell_users` 為每張戰術列出可使用的魔物、費用、是否被封鎖(只給持有者)。
- 常駐魔力加成(`STATIC_POWER` 等)大多不依賴是否在戰鬥中;依戰鬥的條件(`BattleRemembered` 等)讀 `game.state.battle`。

## Decisions

### D1 以假設的戰鬥呼叫 `side_breakdown`

`spell_power_preview(game, player, slot, number, side)` 建一個不掛到狀態上的 `BattleState`(攻擊:攻方為 player、`attack_spell` 為該戰術、`attack_slot` 為該魔物;防禦:防方為 player,`defense_spell` / `defense_slot`),`data` 為空,呼叫 `side_breakdown`。與魔力勝負共用同一個計算,之後新增的加成種類自動反映。不改 `game.state.battle`,所以依戰鬥狀態的條件(戰鬥中才有的待命、宣告時記下的資料)不計入,這正是「不含宣告時與戰鬥中的效果」的範圍。

替代方案:在複製的遊戲上模擬宣告。不採用:宣告可能要選擇與擲硬幣,成本與不確定性都高(explore 時使用者同意以標註處理)。

### D2 哪一方

只有 A 圖示 → 攻擊;只有 D → 防禦;AD → 回合玩家為攻擊、非回合玩家為防禦(與放大檢視顯示「攻擊」或「防禦」的規則一致)。非戰鬥戰術(`effect_icon == "nonbattle"`)不附。

### D3 前端呈現

- 放大檢視的明細區(`zoomDetails`)新增一段「預估合計魔力 N」(只有一隻可用魔物)或每隻一段「〔魔物〕的預估合計魔力 N」,條目沿用 `breakdown.*` 文字;段落下方註明「不含宣告時與戰鬥中的效果」。
- 選擇使用魔物(`pickSpellUser`)時每隻的附註為「合計 N・費用 M」(原為「費用 M」)。
- 只顯示給可操作的一方(快照也只給持有者)。

## Risks / Trade-offs

- 預估與實際不同的情況(戰鬥開始時的待命加成、追加費用、擲硬幣、對手效果)以註明處理;不顯示「可能更高」的提示,避免過度承諾。
- 快照每次為每張攻防戰術 × 可用魔物計算一次:翻開頁最多 2 頁、魔物最多 3 隻,加上 P-015 等任意頁使用的少數頁,成本可忽略。
