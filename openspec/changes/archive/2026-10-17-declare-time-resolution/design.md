## Context

攻擊戰術的 `on_declare` 在戰鬥開始(`_start_battle`,迎戰確認之後)執行,已用於宣告時擲幣(S-035、S-046 等);`on_win` / `injure_instead` 在魔力勝負攻擊方獲勝時才執行。這次要把「選對象 / 擲幣」移到宣告時,但結算(傷害)仍在獲勝時,所以兩段之間要保存宣告時的結果。效果樹的 `on_declare` 與 `on_win` 是兩次獨立的執行,ctx 不共用。

## Goals / Non-Goals

**Goals:** 7 張卡依規則與效果文的時機;宣告時的結果保存在本場戰鬥,結算時讀取;對象不在或攻防被無效時正確失效。

**Non-Goals:** 效果文明寫「ダメージをあたえたとき」的卡(S-004、S-014、S-037、S-039、S-078)不變。

## Decisions

### D1:宣告時的結果存在 `battle.data`
新節點 `RememberInBattle(key, ref)` 把 `on_declare` 中綁定的值存進 `battle.data[key]`;條件 `BattleRemembered(key, value)` 與結算節點從那裡讀。戰鬥結束時 `battle` 清空,自然失效。替代方案是讓 `on_declare` 與 `on_win` 共用 ctx,但兩者是不同掛鉤的獨立執行,改直譯器的成本與風險都較高。

### D2:選對手魔物代替魔書傷害(S-058、S-057、S-070)
- 攻擊宣告(戰鬥開始、`on_declare` 之後)時,若這次攻擊會改為傷害對手魔物(戰術的 `injure_instead`、S-057 待命套用後的 `battle.data["injure_instead"]`),由攻擊方選擇對手魔物,存入 `battle.data["injure_target"]`;對手沒有魔物時存 None。沿用既有的決策種類 `injure_instead_target`。
- 獲勝時 `_injure_instead_of_damage` 直接對 `injure_target` 造成傷害(仍在場才有效),不再詢問。
- S-070:`on_declare`(攻擊)中 `Choose(EffectOptions(魔書 / 魔物))`,選魔物時再 `Choose(OpponentMamodo)`,以 `RememberInBattle` 存模式與對象;`on_win` 依模式走魔書傷害或對 `injure_target` 造成傷害。

### D3:宣告時的全部魔物(S-036、S-101)
`on_declare`(攻擊)記下當下對手場上全部魔物的 UID;`DamageOpponentBookAndAllMamodo` 改用這份清單(只對仍在場者)。

### D4:宣告時擲幣、獲勝時套用(S-069)
`on_declare`(攻擊)擲幣並以 `RememberInBattle` 記下是否正面;`on_win` 依記錄造成傷害或直接結束。

### D5:S-021 的無效時機
`on_declare`(防禦)擲 2 次硬幣,至少 1 次正面時記下 `battle.data["negate_at_effects_end"]`;`_resolve_showdown` 開始時(雙方 pass 之後)若防禦未被無效,才使攻擊無效並發出 `attack_negated`。戰鬥中效果的時機期間攻擊仍有效。

### D6:AGENTS.md
「規則以 `ref/raw/rule3.md` 為準」改為 atwiki 規則頁(https://w.atwiki.jp/zatchbell/pages/94.html),並加上「效果文明寫時機時以效果文為準」。

### D7:戰鬥開始的特性測試
`tests/golden/battle_start.json` 鎖定戰鬥開始的完整狀態;S-057 待命套用的情境現在會在宣告時記下 `battle.data["injure_target"]`(對手只有一隻魔物時直接選定),以 `GOLDEN_UPDATE=1` 重新產生,差異只有這一欄。

## Risks / Trade-offs

- [宣告時多一個決策] → 戰鬥開始後、防禦宣告前出現攻擊方的決策;NPC 與前端沿用既有的中途決策處理,加測試確認 NPC 能走完。
- [S-021 的提示時機改變] → 防禦方宣告後,攻擊方在戰鬥中效果的時機看得到擲幣結果但攻擊尚未無效;記錄在 card-effects design。
