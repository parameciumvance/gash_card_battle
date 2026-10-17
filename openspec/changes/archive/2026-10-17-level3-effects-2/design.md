## Context

限制目前散在幾種表示:`restriction` 持續效果加旗標(`no_spells`、`no_attack_spell`、`no_mamodo_effects`、`mamodo_locked`、`no_defense`…),由 `engine.restricted` / `slot_restricted` 在各個檢查點查詢;E-013 是待命(`no_protect_book`);S-035 類是戰鬥資料的旗標。這批要「依分類」無視與移除,所以要有一個地方回答「這個效果屬於哪個分類、作用在誰身上」。

## Goals / Non-Goals

**Goals:**
- 一個限制分類的查詢點,檢查(能不能用)、無視(M-038 / M-042 / E-031)與移除(P-034 / E-036)都用它。
- 21 張卡依效果文實作與測試;既有卡(E-002、E-024、E-025、P-014、E-013…)的行為不變。

**Non-Goals:**
- E-039 的「不能被移除」(第 5 批);第 3 批 S-068 的禁戰術會直接用這套分類。

## Decisions

### D1:限制分類
`engine` 新增 `restriction_categories(effect) -> set[str]`,分類為 `spells` / `mamodo_effects` / `protect`:

| 效果 | 分類 |
|---|---|
| `restriction` `no_spells`、`no_attack_spell` | spells |
| `restriction` `no_mamodo_effects` | mamodo_effects |
| `restriction` `mamodo_locked`(E-024 / S-074 的指定魔物封鎖) | spells + mamodo_effects |
| 新 `restriction` `no_effects_and_spells`(S-075:整個玩家) | spells + mamodo_effects |
| 新 `restriction` `only_mamodo`(E-043:選定魔物以外的魔物全部封鎖,含保護) | spells + mamodo_effects + protect |
| 新 `restriction` `protect_only`(P-026:只能以選定魔物保護) | protect |
| 待命 `no_protect_book`(E-013) | protect |
| 待命標記 `data["restricts"]`(S-074 的待命) | 依標記 |

各檢查點改用 `engine.blocked(game, player, category, slot=None)` 查詢(依分類彙總所有旗標,含指定魔物與「選定魔物以外」),無視的判斷也集中在這裡;既有旗標與它們的作用範圍不變,以既有測試確認舊卡行為不變。

### D2:無視
- M-038:`_validate_spell_declaration` 與非戰鬥戰術的使用檢查中,屬於 spells 分類的限制若使用戰術的魔物是 M-038 就不擋。M-038 的常駐效果不經過「魔物效果」限制的檢查(常駐效果本來就不檢查),不需特別處理。
- M-042 / E-031:新持續效果 `protect_anyway`(M-042 以這隻魔物為目標;E-031 以玩家為目標),`_eligible_protectors` 遇到 protect 分類的限制時,有 `protect_anyway` 的魔物照樣列入。S-035 類的戰鬥旗標 `no_protect_book` 也一樣可被無視。
- M-051:新登記 `reg.cannot_protect(number)`,`_eligible_protectors` 一律排除,優先於 `protect_anyway`。

### D3:移除
新節點 `RemoveRestrictions(categories, whose)`:P-034 為 `({"spells"}, "self")`,E-036 為 `({"spells", "protect", "mamodo_effects"}, "both")`。移除符合分類、作用對象符合的 `restriction` 持續效果與帶分類的待命,整個效果移除;發出 `restrictions_removed`(移除的來源卡清單)供記錄。S-035 類的戰鬥旗標與 M-051 的性質不是持續 / 待命效果,不移除。

### D4:新時效
`DUR_UNTIL_END_OWN_NEXT_TURN`:建立後再過兩個回合的結束階段到期(`turn_no >= created_turn + 2`)。S-075 以新的複合旗標 `no_effects_and_spells`(整個玩家不能使用魔物效果與戰術,分類 spells + mamodo_effects)對雙方各加一個,時效為新時效。不拆成 `no_spells` + `no_mamodo_effects` 兩個:移除時要整個效果一起移除(使用者確認的規則),P-034 移除 S-075 時魔物效果的限制也一起消失。

### D5:保護限制的檢查
`_eligible_protectors` 依序:排除 `cannot_protect`;套用 protect 分類的限制(`protect_only` / `only_mamodo` 只留選定的魔物、待命 `no_protect_book` 與戰鬥旗標排除全部),但有 `protect_anyway` 的魔物保留;最後加上 P-027 的對手魔物。

### D6:各卡
- S-073:`RestrictOpponent(no_defense, DUR_TURN)`。
- S-074:比照 E-001,使用時 `Choose` 對手魔物,`Standby(NextStartPhase)` 中 `LockChosenOpponentMamodo`;待命標記 `restricts={"spells","mamodo_effects"}`、對象為對手。
- P-026 / E-043:`Choose` 後加 `protect_only` / `only_mamodo`(E-043 以 `AsOpponent` 由對手選)。
- M-040:`engine.event_cost(game, player, card)` = 卡面費用 + 對手場上 M-040 的張數;使用事件卡與快照都用它。
- S-100:`SpellRider.damage_regardless`:防方獲勝時,攻擊沒被無效仍照攻擊傷害走傷害流程;宣告時 `MakeAttackUndefendable`。
- S-069:攻擊 `on_declare` 不可防禦;`no_book_damage` + `on_win` 擲幣,正面時以戰術傷害對魔書造成傷害(新節點 `DamageOpponentBookBySpell`)。防禦 `on_declare` 擲幣,正面 `NegateAttack`(同 S-025)。
- S-070:`on_win_owns_damage`,`Choose(EffectOptions(魔書 / 魔物))` 由攻擊方選,魔物分支沿用負傷代替的選對手魔物流程。
- S-078:`on_damage` 中 `PeekOpponentOpenPages` → `Choose` 對手翻開頁的卡(排除最後一頁與空頁)→ 棄掉;沒有選項時略過。
- S-079:防禦 `on_declare` 加本場戰鬥的持續效果 `guard_immune`(對象:使用者的ウォンレイ);保護對手攻擊的傷害時,該魔物不受傷害。
- P-028:比照 P-006 的 `NegateNextDamageThisBattle`,對象為自己場上的ウォンレイ。
- M-051:`damage_immunity` 一律免疫 + `cannot_protect`。
- P-024:`views._player_view` 在觀看者是對手、且觀看者場上有 P-024 時公開翻開頁;`determinize.known_opponent_pages` 同樣加入。

### D7:S-069 資料修正
`scrape_ja_effects.py` 新增 `KNOWN_TEXT_ERRORS = {"S-069": (錯誤原文, 修正後)}`:解析後若找到原文就取代,找不到就報錯。直接修正 `cards_ja.csv` 與 `cards.json` / 文字檔中 S-069 的效果文(繁中、英文依修正後的日文重寫),不重新抓取整個網站。

### D8:前端與 NPC
- 記錄:`restrictions_removed`;作用中效果:`protect_only`、`only_mamodo`、`protect_anyway`、`guard_immune`、新時效的文字。
- 事件卡費用:`app.js` 以快照的 `cost` 顯示與判斷(目前用卡面費用)。
- P-024:前端已能顯示含卡號的對手翻開頁(與宣告中的戰術頁同),確認並加測試。
- NPC:`determinize` 依 P-024 加入已知頁;保護判斷沿用引擎的選項。

### D9:非戰鬥戰術也受「術を使えない」限制
實作時發現:既有的 `no_spells`(E-002、M-006、S-004 等)只在戰鬥中宣告戰術時檢查,非戰鬥戰術照樣能用;但 E-024 的封鎖已確認「術不分戰鬥與非戰鬥」。改用 `spell_block` 統一判斷後,非戰鬥戰術也會被 `no_spells` 擋下。這是既有行為的改變,已於 2026-10-15 與使用者確認採用,先寫了修正前失敗的測試。

## Risks / Trade-offs

- [新旗標要加到既有檢查點] → `no_effects_and_spells` 要在戰術宣告、非戰鬥戰術、魔物啟動效果、擲幣重擲(M-012 / M-019)等「魔物效果」檢查處都生效;以 `engine.blocked(game, player, category, slot)` 統一查詢這些檢查點,逐一換掉直接查旗標的地方,並以既有測試確認舊卡不變。
- [限制分類以表格維護] → 新增限制旗標時要同時登記分類,在 card-effects design 寫明。
