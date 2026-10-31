## Why

第 1、2 彈當初依英文資源實作，部分卡的實作多了日文效果文沒有的條件，或漏掉了效果文的範圍。l12-translation 把譯文改成日文直譯後，2026-10-31 的 explore 逐張對照了 135 張卡的實作與 atwiki 卡頁 FAQ,找出 8 項差異，使用者決定全部依效果文 / FAQ 修正(差異表見 `openspec/changes/archive/2026-10-31-l12-translation/implementation-diffs.md` 與本 change 的 design)。

## What Changes

- **BREAKING(行為改變)**:
  - M-001 / M-017「自分が攻撃するバトル中、この魔物の魔力を+N」、M-010「自分が防御するバトル中」:使用條件從「這隻魔物正在攻擊 / 防禦」改為「自己是攻擊方 / 防禦方的戰鬥」。這隻魔物沒有參與時可以使用，加成照常加在這隻魔物上。
  - M-005「このバトル中、この魔物の『魔物の効果』や術のダメージを1ふやす」:任何戰鬥都能使用(不再限攻擊);自己防禦時，這隻魔物名稱的戰術的【反擊】傷害也 +1。
  - M-031「合計魔力6000以下の術のダメージを受けない」:【反擊】傷害也適用，以防禦方的合計魔力判斷。非戰鬥戰術造成的傷害沒有合計魔力，不適用。
  - 以 P-027 指定的對手魔物保護也受受方的「かばうことができない」限制(目前不受限制，沒有規則依據)。
  - 「かばうことができない」不限魔書：E-013 與 S-035 / S-060 / S-081 / S-111 的禁止保護，在本場戰鬥中對魔書和魔物受到的傷害都適用(例如 S-057 / M-055 / P-022 把傷害轉到魔物時也不能保護)。E-013 限制的是使用者的對手。
  - E-027:對手那一半，受「相手の効果では捨て札にならない」保護的搭檔(M-049 / M-066)不棄掉，結果留下 2 張以上也可以(卡頁 FAQ)。自己那一半是自己的效果，照常棄掉。
  - S-040「この術の魔力は、コインを3回投げて、オモテの数×2000となる」:防禦時也擲 3 次，魔力為正面數 ×2000(目前防禦時魔力為 0)。
  - S-057:只改變本來會造成傷害的戰術(卡頁 FAQ A2)。沒有傷害的戰術(S-019、S-020 等)不詢問對象，照原本的效果解決。
- 不改行為:M-025「もどすことができる」維持可選(依效果文),design 補記與卡頁新規則 FAQ「可能な限りもどします」衝突、採用效果文的理由。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `card-effects`:新增需求「自己攻擊 / 防禦的戰鬥中的魔力加成」「M-005 的傷害加值」「M-031 的傷害免疫範圍」「不能保護的範圍」(含 P-027 指定的對手魔物)「E-027 與不會被棄掉的搭檔」「S-040 的魔力」「S-057 改變的傷害」。

## Impact

- `src/gash/engine/effects/tree.py`:
  - M-001 / M-010 / M-017 的使用條件節點;
  - M-005 的使用條件;
  - `ImmuneToSpellDamageAtMost`(M-031);
  - `DisableBookProtection` / `ScheduleNoProtectBookNextBattle` 改名並改為不限魔書，限制旗標對照表 `RESTRICTION_KINDS`;
  - `DiscardOtherPartners`(E-027);
  - `AddAttackBonusPerHeads`(S-040)。
- `src/gash/engine/engine.py`:
  - `_eligible_protectors` 的禁止保護判定;
  - `STANDBY_CATEGORIES` 與 `no_protect_book` 待命;
  - `counter_book_damage` 加入 M-005 的加值;
  - 魔力勝負記錄防禦方合計魔力;
  - S-057 待命的適用條件與 `_ask_injure_target`。
- `src/gash/engine/state.py`:`NO_PROTECT_BOOK` 旗標改名。
- 卡片登記 `effects/cards/mamodo.py`、`events.py`、`spells.py`。
- 測試：新增 `tests/test_l12_effect_fixes.py`;依舊解讀的既有測試(如 `tests/test_cards.py::test_e013_no_protect_next_battle` 只驗魔書)視需要改寫。
- 不影響 API 與前端(決策種類不變)。
