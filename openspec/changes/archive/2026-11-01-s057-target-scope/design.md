## Context

動機與解讀見 proposal.md。目前的流程(game-engine design「戰鬥開始與待命表」):
- `BATTLE_START_STANDBYS` 的 `injure_instead`:條件 `a.is_spell and spell_deals_damage(...)`(沒有 `no_book_damage` 的戰術),套用時設 `battle.data["injure_instead"]`。
- `_ask_injure_target`:宣告時(`on_declare` 之前)詢問對象，存 `battle.data["injure_target"]`。
- `_resolve_showdown`:`on_win_owns_damage` 的戰術(S-036、S-069、S-070、S-101)在 `on_win` 之後直接返回，不經過改傷害魔物的分支。

## Goals / Non-Goals

**Goals:**
- S-057 只改變沒有指定對象的「相手の魔本にダメージ」:S-069 生效;S-036 / S-101 / S-070 不詢問對象、不改變。

**Non-Goals:**
- S-057 以外改變傷害對象的效果(M-055、P-022):行為不變，只共用判斷函式。

## Decisions

### D1 適用範圍的判斷

新增 `engine.s057_applies(number) -> bool`(名稱實作時依慣例取語意化名稱，不含卡號):
- 戰術卡的 `effect_ja` 含「相手の魔本にダメージ」;
- 而且 rider 沒有標示「傷害對象由效果的選擇決定」。

細節:
- rider 新增旗標(暫名 `chooses_damage_target`),S-070 設定。「次の効果の1つを使う」由使用者選擇魔書或魔物，選擇本身就明確指定了對象(使用者 2026-11-01)。
- 取代 `spell_deals_damage`。S-019 / S-020 不含這段文字，結果不變。
- 第 1〜3 彈中，有「ダメージ」卻不含這段文字的攻擊戰術只有 S-036 / S-101 / S-058 / S-064,正好是效果文已指定對象的戰術。
- M-055 的 `AttackWithOwnBookDamageSpell` 也是用效果文判斷「相手の魔本にダメージをあたえる」効果の術。字串判斷抽成共用函式，但旗標不套用到 M-055:M-055 的範圍維持現狀，不在這次改動。

替代方案：在 rider 上逐張標示「已指定對象」。被否決：卡片多、容易漏，而且 M-055 已經用效果文判斷。

### D2 S-069

- `AttackBookDamage`(S-069 / S-070 的「相手の魔本にダメージ」結算節點):`battle.data["injure_instead"]` 成立時改呼叫 `_injure_instead_of_damage`。S-070 因 D1 不會有 `injure_instead`,行為不變。
- S-069 的對象由 `_ask_injure_target` 在宣告時詢問(擲幣之前),沿用一般流程。反面時 `FinishAttackWithoutDamage`,對象沒有用到。這和一般戰術的待命一樣：對象在宣告時選，結果由後續決定。

### D3 不適用的戰術

- S-036 / S-101 / S-070 / S-058 / S-064 不符合 D1,`injure_instead` 不套用。待命在戰鬥結束時當作「條件不符」移除，也就是那一場仍用掉待命(效果文「このターン中の次のバトル」)。
- S-058 / S-064 本身帶 `injure_instead` rider,照常詢問自己的對象。

### D4 解讀的記錄

card-effects design「行為決定與理由」新增「S-057 只改變沒有指定對象的傷害」,確認狀態 `Project Decision`(使用者 2026-11-01)。並刪除 l12-effect-fixes 那一節的「待確認」,以及 `todo.md` 的對應項目。

## Risks / Trade-offs

- [以效果文字串判斷，之後的新卡措辭不同] → 新卡實作時依 AGENTS.md 逐字對照效果文。另加守門測試，列出第 1〜3 彈有「ダメージ」但不適用 S-057 的攻擊戰術(S-036 / S-058 / S-064 / S-070 / S-101);名單變動時測試會失敗，需要確認。
