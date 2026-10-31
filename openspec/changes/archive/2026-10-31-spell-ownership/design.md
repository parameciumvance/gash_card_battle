## Context

動機與範圍見 proposal.md。2026-10-31 的 explore 經過:

1. 使用者先提出「『X の術』看所屬魔物,『X が使う術』看使用的魔物」。
2. 我比對全部效果文後發現，沒有卡寫「X が使う術」;寫到使用都是「自分が使う」或「この魔物で…使う」(M-023、M-029、M-036)。
3. 使用者認為兩種讀法都直觀，決定採用聯集。
4. 我提過依「有利或限制」區分讀法，使用者指出分界應該看效果文的寫法(魔物名或指示詞),與是否限制無關。最後選定「甲」:所屬一律看魔物名，指示詞的卡也一樣。

atwiki 2078 頁的官方例子(裝在 ガッシュ・ベル＆ブラゴ 的 高嶺清麿 效果不影響 ブラゴ 的戰術)與聯集不衝突:W 魔物使用 B 的戰術時，使用者算 B;搭檔效果所說的「このパートナーの魔物」是 A。

目前引擎的判定方式:

| 判定方式 | 位置 |
|---|---|
| 使用魔物的家族(`family(slot)`) | `_base_spell_cost_items` 的 `spell_cost_zero`(P-005)、`_spell_bonus_standbys`(M-008、P-007、P-023、Ex-007 類)、`BATTLE_START_STANDBYS` 的 `spell_bonus`、`attack_undefendable`(P-001)、`redirect_damage`(P-022)、`battle_lock`(P-042)、防禦宣告的 `spell_bonus`、`AttackByFamilyWithTarget`(P-043) |
| 戰術卡的對應魔物(`card.related_mamodo`) | `spell_block` 的 `NO_NAMED_SPELLS`(PR-009)、`_spell_any_page_standby`(M-037)、`_spell_named_modifiers`(PR-010)、`NamedSpellPowerBonus`(PR-004) |
| 魔物槽(`target_slot` / `slot_uid`) | `damage_delta`(M-005)、`AttackWithOwnBookDamageSpell`(M-055)、`spell_block` 的 `NO_SPELLS`(E-047)、`NO_ATTACK_SPELL`(P-033)、`MAMODO_LOCKED`(E-024、S-074、Ex-044)、`ONLY_MAMODO`(E-043)、`NO_DEFENSE_SPELL_SLOT`(P-043);`attack_undefendable` 的 `slot_uid`(M-054) |

## Goals / Non-Goals

**Goals:**
- 所有「X の術」的判定都經過同一個函式，依聯集規則。
- 依舊解讀寫的測試與規格情境改成新規則，先寫會失敗的測試。

**Non-Goals:**
- 「X による攻撃 / ダメージ」(P-003、P-004、P-012)、S-079 的保護者家族：這些不是戰術歸屬。
- 「その魔物の『魔物の効果』」、「かばう」限制：仍只看選定的那一隻。
- M-058(卡片規則「自分は、この魔物の術を使えない」)在最後一批實作，屆時沿用這個規則。
- W 魔物(目前沒有)。

## Decisions

### D1 共用判定 `spell_names`

在 `primitives.py` 新增 `spell_names(game, card, slot) -> frozenset`:這個戰術算是哪些魔物的戰術。「X の術」的判定一律寫成 `X in spell_names(...)`。

- 名稱以 `family()` 為準(含 `reg.TREATED_AS`,M-047),與戰術卡的 `related_mamodo` 同一套名稱。
- 指令戰術不加入對應魔物(`COMMAND_ALL` 不是魔物名),只看使用者。
- slot 為 None 時只看所屬(畫面顯示時還沒決定使用的魔物)。

### D2 費用與加成的待命

- `_spell_bonus_standbys(game, player, card, slot)`、`_base_spell_cost_items` / `_spell_cost_items` / `_spell_cost_by` / `_base_spell_cost_by`:參數從 `mamodo_name` 改成 `slot`(可為 None),以 `spell_names` 比對。
- `spell_cost_breakdown` 未指定 slot 時照舊在可使用的魔物中取最低費用;沒有可使用的魔物時以 None 計算。
- `AttackStart`:以 `spell_names`(攻擊戰術由攻擊的魔物使用時的名稱集合)取代 `mamodo_name`,並提供 `spell_of(name)`(以「name」の術攻擊)與 `by(name)`(以「name」の術或 name 的魔物效果攻擊)。`BATTLE_START_STANDBYS` 的 `spell_bonus`、`attack_undefendable`、`redirect_damage`、`battle_lock` 與 P-043 的 `AttackByFamily` 都用這兩個方法。
- 防禦宣告的 `spell_bonus` 同樣以 `spell_names` 比對。
- 畫面快照 `_spell_users` 的 `locked` 傳入戰術卡,與引擎相同依名稱判定。

### D3 指示詞以名稱記錄

建立效果時把那隻魔物的名稱(`family`)寫進資料，判定時以名稱比對，不再比對魔物槽:

| 卡 | 節點 / 位置 | 記錄 | 判定 |
|---|---|---|---|
| M-054 | `MakeNextAttackUndefendable(own_slot=True)` | `data["mamodo"] = family(self_slot)`,取代 `slot_uid` | 與 P-001 相同 |
| E-047、P-033 | `LockChosenOpponentMamodo(flag=NO_SPELLS / NO_ATTACK_SPELL)` | `m.data["mamodo"]` | `spell_block` 中以名稱是否在 `spell_names(card, slot)` 中判定 |
| E-024、S-074 | `LockChosenOpponentMamodo()`(`MAMODO_LOCKED`) | 同上 | 戰術部分依名稱;魔物效果部分仍看 `target_slot` |
| Ex-044 | `LockOpponentMamodoPerHeads` | 同上 | 同 E-024 |
| P-043「防御の術を使えない」 | 攻擊時建立的 `NO_DEFENSE_SPELL_SLOT` | `m.data["mamodo"]`(選定時的名稱) | 防禦戰術依名稱;選定的魔物離場後仍有效 |
| E-043 | `RestrictOthersThanChosen`(`ONLY_MAMODO`) | `m.data["mamodo"]` | 見 D4 |

- P-026(`protect_only`)用同一個節點，但不是戰術限制，照舊。
- `spell_block` 現在接受的 `card` 是可選參數，改為所有呼叫端都傳入戰術卡。依名稱判定時需要 card;card 為 None 的呼叫端(例如畫面判斷魔物是否能使用戰術)改成不帶 card 時只看使用者。實作時逐一確認呼叫端。
- 選定的魔物離場後，限制仍依名稱作用(E-047 等原本 `target_slot` 失效即無作用)。這是「甲」的直接結果，和 PR-001 離場後仍適用的結論一致。
- P-043 的發動條件 `AttackByFamilyWithTarget` 目前要求選定的魔物仍在場。改為:選定的魔物不在場時，只提供「不能使用防禦戰術」(依名稱);保護限制需要那一隻在場。

### D3a M-005、M-055(實作時補上)

- 先前的盤點只比對了「この魔物の術」連寫的效果文,漏掉中間夾著括號字句的寫法。重新掃描「(この|その|選んだ)魔物の…術」後補上 M-005、M-055。
- M-005:`IncreaseSelfDamage` 的 modifier 帶 `data["mamodo"]`;`_attack_damage_amount` 遇到帶名稱的 `damage_delta` 時,條件是攻擊戰術屬於該名稱(`attack_spell_names`),或以這隻魔物的魔物效果攻擊。使用條件改為 `OwnSpellOrEffectAttacking`(取代 `SelfInBattleAs("attack")`),只限攻擊,與既有實作相同。
- M-055:`ScheduleOnAttack` 記下使用效果的魔物名稱(`self_mamodo`),`AttackWithOwnBookDamageSpell` 以 `AttackStart.spell_of(self_mamodo)` 判定。

### D4 E-043「選んだ魔物以外の魔物の術」(使用者 2026-10-31 確認)

- 「選んだ魔物以外の魔物」以單隻魔物為對象。例如對手場上有 A(1)、A(2)、B,選了 A(1),那麼以外的魔物就是 A(2) 與 B。
- 「その魔物の術」依名稱解析。A(2) 的戰術等同 A 的戰術,所以對手不能使用 A 的戰術與 B 的戰術。由 A(1) 使用 A 的戰術也被擋,因為 A(1) 使用的戰術都算 A 的戰術,所以 A(1) 不能使用任何戰術。
- 判定:對手要使用的戰術的 `spell_names` 含有某個名稱 n 時被擋;n 是「目前在對手場上、選定的那一隻以外的魔物」的名稱。
  - 以場上現況判斷,本回合之後放出的魔物也算。
  - 由選定以外的魔物使用時,使用者自己的名稱就在這組名稱裡,所以一定被擋,和現行行為一致。
  - 沒有同名魔物時,選定的魔物仍可使用自己的戰術與指令戰術;使用其他名稱的戰術(戰術相容擴充)時,若那個名稱的魔物在場上就被擋。
- 「魔物の効果」與「かばう」仍以選定的那一隻判定:A(1) 的魔物效果可以使用。

### D5 M-038 的無視範圍

- `spell_block` 在 slot 是 M-038(`reg.IGNORE_SPELL_BLOCK`)時不擋。
- 改為：自己場上有 M-038,且 M-038 的名稱在這個戰術的 `spell_names` 中時不擋。
- 由此，其他魔物使用 ロップス 的戰術、同名的另一隻 ロップス 使用的戰術，都在無視範圍內。
- M-038 受「魔物の効果を使えない」時仍有效(規格既有)。

### D6 不需要改的地方

- 指令戰術只有防禦戰術(S-025、S-027、S-028、S-056)與非戰鬥戰術,沒有攻擊用的。所以「X 使用指令戰術」在攻擊類待命(P-001、M-054、P-022、P-042、P-043、M-037)與 M-008(本來費用 0 不能減)中不會發生;會發生的是防禦宣告與限制(PR-009、E-047 類)。
- M-037:エシュロス 沒有戰術相容擴充,攻擊用的指令戰術也不存在,加上使用者那一半不會多出可用的戰術。保留只看所屬。

- PR-004 `NamedSpellPowerBonus`、PR-010 `_spell_named_modifiers`:名為「ザケル」的戰術，對應魔物是 ガッシュ・ベル(S-001 等)或 ゼオン(S-058、S-099)。ガッシュ・ベル 不能使用 ゼオン 的戰術，所以加上使用者那一半也不會多出符合的戰術。保留只看所屬，並在 design 記錄理由。
  - 日後若有能讓 ガッシュ・ベル 使用其他魔物戰術的卡，要改用 `spell_names`。
  - 實作時以測試確認資料中「ザケル」的對應魔物只有這兩隻。
- PR-009 的 `NO_NAMED_SPELLS` 改用 `spell_names`(多擋 ガッシュ・ベル 使用的指令戰術)。這列在 D3 的同一處修改，不屬於本節。

## Risks / Trade-offs

- 限制類範圍變大，NPC 的「可使用戰術」判斷若與引擎不同步會卡住。不過 NPC 透過快照的 `users` 判斷，而 `users` 由 `spell_block` 產生，所以會跟著同步。自我對戰測試涵蓋。
- `AttackStart.mamodo_name` 移除後，所有使用處都要改。以測試全套與 grep 確認沒有遺漏。
- 既有測試裡依舊解讀寫的情境(M-054「另一隻 ガッシュ・ベル 可以防禦」、P-005 / M-008「由 ポッケリオ 使用 スギナ 的戰術不受影響」等)會反轉。修改前要列出這些測試，在 tasks 中明列，避免把該反轉的測試誤當回歸。
