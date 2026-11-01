## Why

S-057「自分が使う術の『ダメージをあたえる』効果は、『相手の魔物1体を選び、ダメージをあたえる』効果になる」遇到自己處理傷害的戰術時，行為和效果文不符(`todo.md`、l12-effect-fixes design Non-Goals):
- S-036 / S-101 / S-070 宣告時會詢問一個用不到的對象;
- S-069 的「相手の魔本にダメージ」沒有被改變。

2026-11-01 explore 中使用者決定解讀:S-057 改變的是**沒有指定對象的**傷害效果，也就是「相手の魔本にダメージ」。已指定對象的傷害不改變:
- 效果文用「選び / 選んだ」指定對象的(S-036 / S-101、S-058 / S-064);
- 由使用者選擇效果、明確選了對象的(S-070 選「相手の魔本にダメージ」或「相手の魔物1体を選び」)。

因此不會弱化已指定多對象的 S-036 / S-101。atwiki S-057 卡頁解說「通常『相手にダメージ』の攻撃処理を魔物攻撃に変更」與此一致。

## What Changes

- S-057 的待命只適用於效果文有「相手の魔本にダメージ」、且對象不是由使用者選擇決定的攻擊戰術。
- **BREAKING(行為改變)**:
  - S-036 / S-101 / S-070:不改變，宣告時不再詢問 S-057 的對象，獲勝時照原效果。
  - S-069(正面時「相手の魔本にダメージ」):正面時改為傷害宣告時選定的對手魔物;反面時沒有傷害。
- 不變:S-058 / S-064(已指定 1 隻)、一般「相手の魔本にダメージ」的戰術、沒有傷害的戰術(S-019 / S-020)。不適用的那一場仍用掉待命(「このターン中の次のバトル」)。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `card-effects`:修改需求「S-057 改變的傷害」。

## Impact

- `src/gash/engine/engine.py`:`BATTLE_START_STANDBYS` 的 `injure_instead` 適用條件(取代 `spell_deals_damage`)。
- `src/gash/engine/effects/registry.py`:rider 新增旗標，標示傷害對象由效果的選擇決定(S-070)。
- `src/gash/engine/effects/tree.py`:`AttackBookDamage` 在 S-057 生效時改傷害選定的魔物;M-055 的 `AttackWithOwnBookDamageSpell` 改用共用的判斷。
- 測試：新增 `tests/test_s057_target_scope.py`。
