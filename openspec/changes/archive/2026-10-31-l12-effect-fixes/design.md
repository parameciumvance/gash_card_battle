## Context

動機見 proposal.md。2026-10-31 的 explore 經過:

1. l12-translation 翻譯時，把可疑的差異記在 `implementation-diffs.md`。
2. explore 依魔物 → 搭檔 → 事件 → 戰術的順序，逐張對照效果樹、日文效果文與 atwiki 卡頁 FAQ(`tools/scrape_ja_effects.fetch` 抓取)。
3. 使用者逐項決定。

搭檔卡、其餘事件卡與戰術卡沒有差異。翻譯時記下的 P-009、S-021、S-056、E-023、S-043 經確認沒有問題。

| # | 卡 | 目前實作 | 決定 |
|---|---|---|---|
| 1 | M-001 / M-017 / M-010 | `SelfInBattleAs`:這隻魔物正在攻擊 / 防禦 | 自己攻擊 / 防禦的戰鬥就能用 |
| 2 | M-005 | `OwnSpellOrEffectAttacking`:只限攻擊 | 任何戰鬥;反擊傷害也 +1 |
| 3 | M-031 | `ImmuneToSpellDamageAtMost` 只看 `cause == "battle_attack"` | 反擊傷害以防禦方合計魔力判斷;非戰鬥戰術不適用 |
| 4 | E-013、S-035 類 | `no_protect_book`:只擋魔書傷害，限制防禦方 | 改為 `no_protect`,魔書與魔物都擋;E-013 限制使用者的對手 |
| 5 | E-027 | `DiscardOtherPartners` 不看 M-049 的保護 | 對手那一半跳過受保護的搭檔 |
| 6 | S-040 | `When(SideIs("attack"), ...)`:防禦時魔力 0 | 防禦時也擲幣 |
| 7 | S-057 | 改為傷害魔物的判斷排在 `no_book_damage` 之前 | 只改本來會造成傷害的戰術 |
| 8 | M-025 | 可選擇不放回 | 不改;補記 FAQ 衝突 |

## Goals / Non-Goals

**Goals:**
- 8 項依效果文 / FAQ 修正，每項先寫依效果文的測試並確認修改前失敗(M-025 除外，行為不變)。
- 「不能保護」只剩一種「本場戰鬥不能保護」的機制，名稱不再寫 book。

**Non-Goals:**
- S-036 / S-101(`on_win_owns_damage`:對手魔書與所有魔物各受傷害)在 S-057 待命下的行為:效果文「ダメージをあたえる」效果改為「相手の魔物1体を選び、ダメージをあたえる」,這兩張的傷害不只一處，怎麼改變需要另外解讀。目前的實作是宣告時仍詢問對象，但獲勝時照原效果解決(對象沒有用到)。這次不改，列為待確認事項，之後另開 change。
- 第 3 彈的翻譯與實作檢查。

## Decisions

### D1 M-001 / M-010 / M-017 的使用條件

新增條件節點 `OwnSideInBattle(side)`:`side == "attack"` 時 `battle.attacker == player`,`"defense"` 時 `battle.defender == player`。這 3 張改用它，加成照舊 `AddPower(target=Ref("self_slot"))`。

`SelfInBattleAs` 若沒有其他使用者就刪除。

替代方案:「這隻魔物沒有參與時不能使用」。被否決的理由：效果文的條件是「自分が攻撃するバトル中」,對象是「この魔物」。依既有決定「搭檔效果的作用對象不是使用條件」,對象沒有作用時，使用照常成立、只是沒有效果。

### D2 M-005 任何戰鬥、反擊也加值

- 使用條件改為只要在戰鬥中(`timing="battle"` 已保證),移除 `OwnSpellOrEffectAttacking`(沒有其他使用者就刪除)。
- `IncreaseSelfDamage` 照舊建立帶 `data["mamodo"]` 的 `damage_delta`。
- 攻擊傷害(`_attack_damage_amount`)照舊只看攻擊方的 modifier。
- `counter_book_damage` 新增:防禦方帶 `data["mamodo"]` 的 `damage_delta`,其名稱在防禦戰術的 `spell_names(card, 防禦的魔物)` 中時，加到反擊傷害。只算帶 `mamodo` 的 modifier:P-003 / P-004 一類以攻擊的魔物限定，不適用反擊。
- S-061 的反擊傷害「等於對手攻擊的傷害」:M-005 的 +1 加在算出的值上。
- S-109 的反擊經 `counter_book_damage`(tree 的反擊結算節點),一樣適用。

### D3 M-031 的反擊

- `_resolve_showdown` 另外記錄 `battle.data["defense_total"]`。
- `ImmuneToSpellDamageAtMost` 的判斷:
  - `cause == "battle_attack"` 且攻擊是戰術時，比較 `attack_total`(照舊);
  - `cause == "battle_counter"` 時，比較 `defense_total`(反擊一定來自防禦戰術)。
- 其他原因(非戰鬥戰術、魔物效果)不適用。

### D4 統一為 `no_protect`

- 旗標與節點改名:
  - `state.NO_PROTECT_BOOK` → `NO_PROTECT`;
  - `battle.data["no_protect_book"]` → `battle.data["no_protect"]`,值是被限制的玩家集合;
  - `DisableBookProtection` → `DisableProtection`:S-035 類，限制防禦方;
  - `ScheduleNoProtectBookNextBattle` → `ScheduleNoProtectNextBattle`:E-013,待命 `kind="no_protect"`,套用時限制 `1 - sb.owner`;
  - `STANDBY_CATEGORIES` 與 `RESTRICTION_KINDS` 對照表同步改名。E-036 / E-045 的分類不變。
- `_eligible_protectors`:受方在 `battle.data["no_protect"]` 中時，魔書與魔物項都不能保護。M-042 / E-031(`_protect_anyway`)照舊優先。
- P-027 指定的對手魔物(使用者 2026-10-31 指正):以對手的魔物保護也是「かばう」,所以受方的「かばうことができない」限制同樣適用。目前 `_eligible_protectors` 對它只排除 `CANNOT_PROTECT`,game-engine design 寫的「P-027 指定的對手魔物不受受方的限制」沒有規則依據，這次一併修正:
  - `no_protect`(E-013、S-035 類):不能用它保護;
  - `PROTECT_ONLY`(P-026)/ `ONLY_MAMODO`(E-043):它不是選定的魔物，不能用它保護;
  - `NO_PROTECT_SLOT`(P-043):選定的是受方自己的魔物，與它無關;
  - E-031(「自分は…かばうことができる」,整個玩家)照樣讓受方可以用它保護;M-042(「この魔物で」)只對 M-042 持有者自己的保護有效，它被對手的 P-027 指定時不適用。

替代方案:S-035 類保留只擋魔書、E-013 另開旗標。被否決的理由:S-035 類的傷害經 S-057 / M-055 / P-022 轉到魔物時，依「この術のダメージ」仍不能保護。這場戰鬥中防禦方受到的傷害只來自這次攻擊(反擊打的是攻擊方),所以「本場戰鬥受方不能保護」等於「這個戰術的傷害不能保護」。

### D5 E-027 跳過受保護的搭檔

`DiscardOtherPartners` 在 `ctx["player"]` 不是效果擁有者時(`AsOpponent` 子樹，即對手那一半),跳過 `partner_discard_guarded` 的魔物。效果擁有者由 ctx 的來源取得，實作時沿用既有的取法(例如 E-030 的 `obj.owner` 比對)。

對手仍從所有裝了搭檔的魔物中選要保留的 1 張(`pick_partner_to_keep` 選項不變);選到受保護的那張時，其餘未受保護的照常棄掉。這是 `Inferred`:效果文「1枚残してすべて選び、捨て札にする」由對手選，FAQ 只說受保護的不棄掉。

### D6 S-040 防禦時擲幣

- `on_declare` 去掉 `SideIs("attack")`。
- `AddAttackBonusPerHeads` 改為 `AddSpellPowerPerHeads`,加到 `ctx["side"]` 那一方(`add_spell_power(battle, side, ...)`)。
- 防禦的宣告時效果在防禦被無效時不生效，沿用既有的宣告時流程。

### D7 S-057 只改變本來會造成傷害的戰術

- 「本來會造成傷害」:戰術卡沒有 `no_book_damage` 的 rider。S-019 / S-020 這類「獲勝時只發生效果」的戰術都標了 `no_book_damage`。
- `BATTLE_START_STANDBYS` 的 `injure_instead` 適用條件改為 `a.is_spell and 本來會造成傷害`。不符合時不套用，待命照「條件不符」在戰鬥結束時移除(效果文「このターン中の次のバトルで」,已經過了那一場)。
- 這樣 `_ask_injure_target` 不會詢問，`_resolve_showdown` 也不會走改傷害魔物的分支。
- S-058 本身帶 `injure_instead`,不受影響。

替代方案:在 `_resolve_showdown` 把 `no_book_damage` 的判斷移到前面。被否決的理由：宣告時仍會詢問一個用不到的對象。

### D8 M-025 的 FAQ 衝突

只記錄，不改行為。寫進 card-effects design「M-025 由玩家選擇放回的空頁」一節或新的一節:

- 效果文是「もどすことができる」;
- atwiki 卡頁新規則 FAQ 寫「可能な限りもどします」,舊規則 FAQ 寫「必要ありません」,兩者互相衝突;
- 依 AGENTS.md「以日文效果文為準」採用效果文，維持可選。確認狀態 `Project Decision`(使用者 2026-10-31 決定)。

## Risks / Trade-offs

- [改名牽動既有測試與 design 的字串] → 以 grep `no_protect_book` / `NO_PROTECT_BOOK` / `DisableBookProtection` 確認沒有遺漏;game-engine design 的待命表與保護順序說明一併更新。
- [M-001 類在沒有參與時仍可使用，NPC 可能白花 MP] → 自我對戰測試確認不卡住;NPC 是否使用不在這次範圍。
- [S-057 待命遇到沒有傷害的戰術時被消耗] → 依效果文「次のバトル」就是那一場，消耗是正確的;以測試確認下一場戰鬥不再適用。

## Open Questions

- S-036 / S-101 在 S-057 待命下怎麼改變傷害(見 Non-Goals),已記入 `todo.md`,之後另開 change 與使用者確認。
