"""第 3 賽季效果第 1 批(card-effects「第 3 賽季卡片的開放」)。依日文效果文逐卡驗證可觀察的結果。

白板魔物 Ex-001 / 004 / 005 / 006 / 028 / 029 / 030;香草戰術 Ex-013 / 014 / 016〜020 / 038〜042、S-107;
魔力 Ex-002、Ex-023、PR-002、PR-003、PR-004、E-048、Ex-036、M-064;
MP Ex-008、Ex-009、Ex-033、E-046、E-049、M-056、M-067、PR-011、Ex-027;
本來的費用 Ex-007 / 010 / 011 / 012 / 035、PR-010;魔物效果攻擊 M-068 / M-069;戰術 S-108〜S-112。
"""

import pytest

from gash.engine.cards import pending_cards
from gash.engine.engine import slot_power, spell_cost, submit
from gash.engine.state import MamodoSlot
from tests.test_level2 import HEADS, TAILS, Rng, book, mk, to_battle
from tests.test_level3 import (
    ability, add_slot, attack, battle_in, choose, code, end_turn, finish_damage, no_defense_pass, pass_effects,
    use_event,
)

VANILLA_MAMODO = ("Ex-001", "Ex-004", "Ex-005", "Ex-006", "Ex-028", "Ex-029", "Ex-030")
VANILLA_SPELLS = ("Ex-013", "Ex-014", "Ex-016", "Ex-017", "Ex-018", "Ex-019", "Ex-020",
                  "Ex-038", "Ex-039", "Ex-040", "Ex-041", "Ex-042", "S-107")
EFFECT_CARDS = ("Ex-002", "Ex-007", "Ex-008", "Ex-009", "Ex-010", "Ex-011", "Ex-012", "Ex-023", "Ex-027",
                "Ex-033", "Ex-035", "Ex-036", "S-108", "S-109", "S-110", "S-111", "S-112",
                "PR-002", "PR-003", "PR-004", "PR-010", "PR-011", "E-046", "E-048", "E-049",
                "M-056", "M-064", "M-067", "M-068", "M-069")
BATCH = VANILLA_MAMODO + VANILLA_SPELLS + EFFECT_CARDS


def showdown(g):
    return [e for e in g.events if e["type"] == "showdown"][-1]


def mamodo_attack(g, slot, player=0):
    submit(g, {"type": "declare_attack", "player": player, "mode": "mamodo", "slot_uid": slot.uid})
    submit(g, {"type": "battle_in_response", "player": 1 - player, "allow": True})


def partner_ability(g, slot, player=0):
    return submit(g, ability(player, slot, zone="partner"))


# ---------------------------------------------------------------- 開放

def test_batch_size():
    assert len(set(BATCH)) == 50


def test_batch_cards_are_open():
    assert not set(BATCH) & pending_cards()


# ---------------------------------------------------------------- 白板魔物

@pytest.mark.parametrize("number", VANILLA_MAMODO)
def test_vanilla_mamodo_has_no_effect(number):
    g, _ = mk(book(number), book("M-001"))
    to_battle(g, 0)
    assert code(g, ability(0, g.state.players[0].slots[0])) == "ability.none"


def test_vanilla_mamodo_attacks_with_spell():
    # Ex-001 ガッシュ・ベル(魔力 4500)で「ザケル」S-001(+2000)
    g, _ = mk(book("Ex-001", "S-001"), book("M-001"))
    st = g.state
    st.players[0].mp = 5
    to_battle(g, 0)
    pos1 = st.players[1].pos
    attack(g, 2)
    pass_effects(g)
    finish_damage(g)
    assert showdown(g)["attacker_total"] == 6500
    assert st.players[1].pos == pos1 + 2


@pytest.mark.parametrize("number, mamodo, damage", [
    ("Ex-013", "M-001", 2), ("Ex-017", "M-050", 1), ("Ex-020", "M-001", 3), ("Ex-038", "M-012", 1),
    ("Ex-039", "M-012", 2), ("Ex-040", "M-005", 2), ("Ex-041", "M-001", 2), ("Ex-042", "M-042", 2),
    ("S-107", "M-001", 2),
])
def test_vanilla_attack_spells(number, mamodo, damage):
    # 相手の魔本にダメージ。
    g, _ = mk(book(mamodo, number), book("M-040"))
    st = g.state
    st.players[0].mp = 10
    to_battle(g, 0)
    pos1 = st.players[1].pos
    attack(g, 2)
    pass_effects(g)
    finish_damage(g)
    assert st.players[1].pos == pos1 + 2 * damage


@pytest.mark.parametrize("number, mamodo", [("Ex-014", "M-001"), ("Ex-016", "M-021")])
def test_vanilla_counter_spells(number, mamodo):
    # 【カウンター】魔力勝負で勝ったとき、相手の魔本にダメージ。
    g, _ = mk(book("M-012", "Ex-038"), book(mamodo, number))                  # 攻撃側 1000 + 3000
    st = g.state
    st.players[0].mp, st.players[1].mp = 10, 10
    to_battle(g, 0)
    pos0 = st.players[0].pos
    battle_in(g, 2)
    submit(g, {"type": "declare_defense", "player": 1, "page": 2})
    pass_effects(g)
    finish_damage(g)
    assert showdown(g)["winner"] == "defender"
    assert st.players[0].pos == pos0 + 2


@pytest.mark.parametrize("number, mamodo", [("Ex-018", "M-050"), ("Ex-019", "M-011")])
def test_vanilla_negate_spells(number, mamodo):
    # 魔力勝負で勝ったとき、相手の攻撃を無効にする。
    g, _ = mk(book("M-012", "Ex-038"), book(mamodo, number))
    st = g.state
    st.players[0].mp, st.players[1].mp = 10, 10
    to_battle(g, 0)
    pos1 = st.players[1].pos
    battle_in(g, 2)
    submit(g, {"type": "declare_defense", "player": 1, "page": 2})
    pass_effects(g)
    finish_damage(g)
    assert showdown(g)["winner"] == "defender"
    assert st.players[1].pos == pos1


# ---------------------------------------------------------------- 魔力

def test_ex002_minus_2000_not_below_zero():
    # 《ナァ～!》MPを2へらす→【ステイ】相手の魔物1体を選ぶ。このターン中、その魔物の魔力を-2000する(0より小さくはならない)
    g, _ = mk(book("Ex-002"), book("M-040"))
    st = g.state
    st.players[0].mp = 3
    big = add_slot(g, 1, "M-001")
    to_battle(g, 0)
    submit(g, ability(0, st.players[0].slots[0]))
    assert st.pending.player == 0
    choose(g, st.players[1].slots[0].uid)                                     # パピプリオ 1000
    assert st.players[0].mp == 1
    assert slot_power(g, 1, st.players[1].slots[0]) == 0 and slot_power(g, 1, big) == 4000
    end_turn(g)
    assert slot_power(g, 1, st.players[1].slots[0]) == 1000


def test_ex023_plus_3000_this_turn():
    # 【ステイ】自分の魔物1体を選ぶ。このターン中、その魔物の魔力を+3000する
    g, _ = mk(book("M-001", "Ex-023"), book("M-001"))
    st = g.state
    st.players[0].mp = 5
    other = add_slot(g, 0, "M-040")
    to_battle(g, 0)
    use_event(g)
    assert st.pending.player == 0
    choose(g, other.uid)
    assert slot_power(g, 0, other) == 4000
    end_turn(g)
    assert slot_power(g, 0, other) == 1000


def test_pr002_self_plus_2000_this_turn():
    # 《最高の友達》MPを3へらす→【ステイ】このターン中、この魔物の魔力を+2000する
    g, _ = mk(book("PR-002"), book("M-001"))
    st = g.state
    st.players[0].mp = 3
    to_battle(g, 0)
    me = st.players[0].slots[0]
    submit(g, ability(0, me))
    assert st.players[0].mp == 0 and slot_power(g, 0, me) == 6000
    end_turn(g)
    assert slot_power(g, 0, me) == 4000


def test_pr003_gash_bonus_includes_treated_as():
    # 《走れ!ウマゴン》このカードが場にある→自分の場の「ガッシュ・ベル」の魔力を+2000する
    g, _ = mk(book("PR-003"), book("M-001"))
    st = g.state
    gash = add_slot(g, 0, "M-001")
    golden = add_slot(g, 0, "M-001", "M-047")                                 # 「ガッシュ・ベル」としてあつかう
    other = add_slot(g, 1, "M-001")
    assert slot_power(g, 0, gash) == 6000
    assert slot_power(g, 0, golden) == 11000
    assert slot_power(g, 0, st.players[0].slots[0]) == 1000                   # ウマゴン自身は対象外
    assert slot_power(g, 1, other) == 4000                                    # 相手の魔物は対象外


def test_pr004_zakeru_plus_1000_exact_name():
    # 《電撃の子》このカードが場にある→自分の「ガッシュ・ベル」の術「ザケル」の魔力を+1000する
    g, _ = mk(book("PR-004", "S-001", "S-112"), book("M-040"))
    st = g.state
    st.players[0].mp = 10
    to_battle(g, 0)
    attack(g, 2)
    pass_effects(g)
    finish_damage(g)
    assert showdown(g)["attacker_total"] == 4000 + 2000 + 1000
    attack(g, 3)                                                              # 「ザケルガ」は対象外
    pass_effects(g)
    finish_damage(g)
    assert showdown(g)["attacker_total"] == 4000 + 3000


def test_field_power_effects_stack_per_copy():
    # 同一卡號的常駐效果多張在場時各自生效(design D12):以測試替身放寬同名上限
    g, _ = mk(book("M-001"), book("M-001"))
    st = g.state
    st.players[0].slots = [MamodoSlot(uid=st.next_uid(), stack=["PR-003"]),
                           MamodoSlot(uid=st.next_uid(), stack=["PR-003"]),
                           MamodoSlot(uid=st.next_uid(), stack=["M-001"])]
    assert slot_power(g, 0, st.players[0].slots[2]) == 4000 + 2000 * 2


def test_e048_power_per_own_mamodo_recomputed():
    # 【ステイ】自分の魔物すべてを選ぶ。次のターンのエンドフェイズまで、その魔物の魔力を、自分の場の魔物の数×1000だけふえる
    # FAQ:魔物の数の増減は改めて計算しなおす;新たに場に出した魔物もふやせる
    g, _ = mk(book("M-001", "E-048", "M-040"), book("M-001"))
    st = g.state
    b = add_slot(g, 0, "M-012")
    to_battle(g, 0)
    use_event(g)
    a = st.players[0].slots[0]
    assert slot_power(g, 0, a) == 4000 + 2000
    submit(g, {"type": "pass", "player": 1})
    submit(g, {"type": "play_card", "player": 0, "page": 3})                   # 3 隻目を出す
    c = st.players[0].slots[-1]
    assert slot_power(g, 0, a) == 7000 and slot_power(g, 0, c) == 1000 + 3000
    st.players[0].slots.remove(b)
    assert slot_power(g, 0, a) == 6000
    end_turn(g)
    assert slot_power(g, 0, a) == 6000                                         # 次のターンも有効
    end_turn(g)
    assert slot_power(g, 0, a) == 4000


def test_ex036_total_plus_2000_with_wonrei():
    # 《信じる強さ》このカードが場にある→自分が「ウォンレイ」で攻撃や防御するとき、そのバトルの合計魔力を+2000する
    g, _ = mk(book("M-042", "Ex-042"), book("M-040"))
    st = g.state
    st.players[0].mp = 10
    st.players[0].slots[0].partner = "Ex-036"
    to_battle(g, 0)
    attack(g, 2)
    pass_effects(g)
    finish_damage(g)
    show = showdown(g)
    assert show["attacker_total"] == 4000 + 6000 + 2000
    assert {"kind": "static_total", "source": "Ex-036", "amount": 2000} in [
        {k: i[k] for k in ("kind", "source", "amount")} for i in show["attacker_breakdown"]]


def test_ex036_applies_to_mamodo_effect_attack():
    g, _ = mk(book("M-069"), book("M-040"))
    st = g.state
    st.players[0].mp = 5
    st.players[0].slots[0].partner = "Ex-036"
    to_battle(g, 0)
    mamodo_attack(g, st.players[0].slots[0])
    no_defense_pass(g)
    finish_damage(g)
    assert showdown(g)["attacker_total"] == 6000 + 2000


def test_ex036_action_discard():
    # ※１アクションを使って、このカードを捨て札にできる
    g, _ = mk(book("M-042"), book("M-001"))
    st = g.state
    st.players[0].slots[0].partner = "Ex-036"
    to_battle(g, 0)
    submit(g, {"type": "use_action_effect", "player": 0, "zone": "partner", "slot_uid": st.players[0].slots[0].uid})
    assert st.players[0].slots[0].partner is None and "Ex-036" in st.players[0].discard


def test_m064_game_long_bonus_once_per_game():
    # 《お願ね》このカードを捨て札にする→【ステイ】自分の魔物1体を選ぶ。このゲーム中、その魔物の魔力を+2000する。
    # この効果はゲーム中1回だけ使える
    g, _ = mk(book("M-001"), book("M-001"))
    st = g.state
    korulu = add_slot(g, 0, "M-064")
    korulu2 = add_slot(g, 0, "M-064")
    gash = st.players[0].slots[0]
    to_battle(g, 0)
    submit(g, ability(0, korulu))
    assert st.pending.player == 0 and korulu not in st.players[0].slots
    choose(g, gash.uid)
    assert slot_power(g, 0, gash) == 6000
    end_turn(g)
    end_turn(g)                                                                # 次の自分のターン
    assert slot_power(g, 0, gash) == 6000
    assert code(g, ability(0, korulu2)) == "ability.per_game"


# ---------------------------------------------------------------- MP

def test_ex008_mp_plus_4():
    # 《絆》このカードを捨て札にする→自分のＭＰを４ふやす。この効果は１ターンに１回しか使えない
    g, _ = mk(book("Ex-002"), book("M-001"))
    st = g.state
    st.players[0].mp = 1
    st.players[0].slots[0].partner = "Ex-008"
    to_battle(g, 0)
    partner_ability(g, st.players[0].slots[0])
    assert st.players[0].mp == 5 and st.players[0].slots[0].partner is None


def test_ex009_opponent_mp_minus_4():
    # 《ハサミ使い》このカードを捨て札にする→相手のＭＰを４へらす
    g, _ = mk(book("Ex-003"), book("M-001"))
    st = g.state
    st.players[1].mp = 6
    st.players[0].slots[0].partner = "Ex-009"
    to_battle(g, 0)
    partner_ability(g, st.players[0].slots[0])
    assert st.players[1].mp == 2


@pytest.mark.parametrize("pick, mine, theirs", [(0, 5, 4), (1, 2, 1)])
def test_ex033_choose_one(pick, mine, theirs):
    # 《イタリアの英雄》このカードを捨て札にする→次の効果の1つを使う。●自分のＭＰを3ふやす。●相手のＭＰを3へらす
    g, _ = mk(book("M-012"), book("M-001"))
    st = g.state
    st.players[0].mp, st.players[1].mp = 2, 4
    st.players[0].slots[0].partner = "Ex-033"
    to_battle(g, 0)
    partner_ability(g, st.players[0].slots[0])
    assert st.pending.player == 0
    choose(g, st.pending.options[pick]["value"])
    assert (st.players[0].mp, st.players[1].mp) == (mine, theirs)


@pytest.mark.parametrize("pick, mine, theirs", [(0, 4, 5), (1, 0, 1)])
def test_e049_choose_both_plus_or_minus(pick, mine, theirs):
    # 次の効果の1つを使う。●自分と相手のMPをそれぞれ2ふやす。●自分と相手のMPをそれぞれ2へらす
    g, _ = mk(book("M-001", "E-049"), book("M-001"))
    st = g.state
    st.players[0].mp, st.players[1].mp = 2, 3
    to_battle(g, 0)
    use_event(g)
    assert st.pending.player == 0
    choose(g, st.pending.options[pick]["value"])
    assert (st.players[0].mp, st.players[1].mp) == (mine, theirs)


@pytest.mark.parametrize("coins, gain", [((HEADS, HEADS, TAILS), 2), ((TAILS, TAILS, TAILS), 0)])
def test_e046_coins_per_mamodo_and_partner(coins, gain):
    # 自分の場の魔物とパートナーの数と同じ回数、コインを投げる。オモテが出た回数×1、自分のMPをふやす
    g, _ = mk(book("M-001", "E-046"), book("M-001"))
    st = g.state
    g.rng = Rng(*coins)
    st.players[0].mp = 1
    add_slot(g, 0, "M-040", partner="P-026")
    to_battle(g, 0)
    events = use_event(g)
    assert len([e for e in events if e["type"] == "coin_flipped"]) == 3
    assert st.players[0].mp == 1 + gain


def test_e046_no_mamodo_flips_nothing():
    g, _ = mk(book("M-001", "E-046"), book("M-001"))
    st = g.state
    st.players[0].mp = 1
    to_battle(g, 0)
    st.players[0].slots = []
    events = use_event(g)
    assert not [e for e in events if e["type"] == "coin_flipped"] and st.players[0].mp == 1


@pytest.mark.parametrize("heads", [True, False])
def test_m056_coin_mp_plus_3_own_turn_only(heads):
    # 《武者震い》MPを1へらす→自分のバトルフェイズに、コインを投げてオモテなら、自分のMPを3ふやす
    g, _ = mk(book("M-056"), book("M-001"))
    st = g.state
    g.rng = Rng(HEADS if heads else TAILS)
    st.players[0].mp = 1
    to_battle(g, 0)
    submit(g, ability(0, st.players[0].slots[0]))
    assert st.players[0].mp == (3 if heads else 0)


def test_m056_not_in_opponent_turn():
    g, _ = mk(book("M-001"), book("M-056"))
    st = g.state
    st.players[1].mp = 3
    to_battle(g, 0)
    submit(g, {"type": "pass", "player": 0})
    assert code(g, ability(1, st.players[1].slots[0])) == "ability.timing"     # 自分のターンのみ


def test_m067_mp_plus_4_next_own_start_phase():
    # 《プレゼント運び》このカードを捨て札にする→【スタンバイ】次の自分のターンのスタートフェイズに、自分のMPを4ふやす
    g, _ = mk(book("M-001"), book("M-001"))
    st = g.state
    um = add_slot(g, 0, "M-067")
    st.players[0].mp = 0
    to_battle(g, 0)
    submit(g, ability(0, um))
    assert um not in st.players[0].slots and st.players[0].mp == 0
    end_turn(g)                                                                # 相手のターン
    mp_before = st.players[0].mp
    end_turn(g)                                                                # 自分のターン
    assert st.players[0].mp == mp_before + 4


FLIP_MP = 2   # エンドフェイズの強制めくり(魔本 1 枚)で増える MP


@pytest.mark.parametrize("mp, after", [(1, 3 + FLIP_MP), (0, 2 + FLIP_MP), (2, 2 + FLIP_MP)])
def test_pr011_end_phase_mp(mp, after):
    # 《元気ハツラツ》このカードが場にある→この効果は、自分のエンドフェイズに自分のMPが1以下なら使える。自分のMPを2ふやす
    # 判定は強制めくりの前(エンドフェイズの効果の解決時,E-038 と同じ)
    g, _ = mk(book("PR-011"), book("M-001"))
    st = g.state
    to_battle(g, 0)
    st.players[0].mp = mp
    submit(g, {"type": "pass", "player": 0})
    submit(g, {"type": "pass", "player": 1})
    assert st.turn_player == 1 and st.players[0].mp == after


def test_pr011_not_in_opponent_end_phase():
    g, _ = mk(book("M-001"), book("PR-011"))
    st = g.state
    to_battle(g, 0)
    st.players[1].mp = 0
    submit(g, {"type": "pass", "player": 0})
    submit(g, {"type": "pass", "player": 1})
    assert st.players[1].mp == 0


@pytest.mark.parametrize("opp_mp, mine, theirs", [(3, 2, 2), (0, 1, 0)])
def test_ex027_steal_one_mp_only_when_reduced(opp_mp, mine, theirs):
    # 《魔鏡あつめ》使用を宣言する→自分のバトルフェイズに、相手のMPを1へらす。そうしたなら、自分のMPを1ふやす
    g, _ = mk(book("Ex-027"), book("M-001"))
    st = g.state
    st.players[0].mp, st.players[1].mp = 1, opp_mp
    to_battle(g, 0)
    submit(g, ability(0, st.players[0].slots[0]))
    assert (st.players[0].mp, st.players[1].mp) == (mine, theirs)


def test_ex027_not_when_blocked_by_p021():
    g, _ = mk(book("Ex-027"), book("M-033"))
    st = g.state
    st.players[0].mp, st.players[1].mp = 1, 3
    to_battle(g, 0)
    submit(g, {"type": "pass", "player": 0})                                   # 相手の行動:P-021 を使う
    st.players[1].slots[0].partner = "P-021"
    partner_ability(g, st.players[1].slots[0], player=1)
    submit(g, ability(0, st.players[0].slots[0]))
    assert (st.players[0].mp, st.players[1].mp) == (1, 3)


def test_ex027_own_turn_only_and_once_per_turn():
    g, _ = mk(book("M-001"), book("Ex-027"))
    st = g.state
    st.players[1].mp = 3
    to_battle(g, 0)
    submit(g, {"type": "pass", "player": 0})
    assert code(g, ability(1, st.players[1].slots[0])) == "ability.timing"     # 自分のターンのみ


# ---------------------------------------------------------------- 本來的費用

@pytest.mark.parametrize("partner, mamodo, spell, cost", [
    ("Ex-007", "M-001", "S-029", 3), ("Ex-010", "M-021", "S-038", 3),
    ("Ex-011", "M-050", "S-096", 2), ("Ex-012", "M-011", "S-018", 2),
])
def test_family_base_cost_zero_next_battle(partner, mamodo, spell, cost):
    # このカードを捨て札にする→【スタンバイ】このターン中の次のバトルで、自分の「X」の術1つの、本来のコストを0にする
    g, _ = mk(book(mamodo, spell, spell), book("M-040"))
    st = g.state
    st.players[0].mp = 5
    st.players[0].slots[0].partner = partner
    to_battle(g, 0)
    partner_ability(g, st.players[0].slots[0])
    submit(g, {"type": "pass", "player": 1})
    attack(g, 2)
    assert st.players[0].mp == 5
    pass_effects(g)
    finish_damage(g)
    attack(g, 3)                                                               # 次のバトルだけ
    assert st.players[0].mp == 5 - cost


def test_family_base_cost_lost_when_next_battle_uses_other_family():
    g, _ = mk(book("M-001", "S-018", "S-029"), book("M-040"))
    st = g.state
    st.players[0].mp = 10
    st.players[0].slots[0].partner = "Ex-007"
    add_slot(g, 0, "M-011")
    to_battle(g, 0)
    partner_ability(g, st.players[0].slots[0])
    submit(g, {"type": "pass", "player": 1})
    attack(g, 2, slot=st.players[0].slots[1])                                 # フェインの術
    assert st.players[0].mp == 8
    pass_effects(g)
    finish_damage(g)
    attack(g, 3, slot=st.players[0].slots[0])                                 # ガッシュの術:もう 0 にならない
    assert st.players[0].mp == 5


def test_family_base_cost_zero_on_defense_keeps_extra_cost():
    # Ex-011:防御でも使える;追加コストは0にならない(Ex-011 の旧ルール公式 FAQ)
    g, _ = mk(book("M-001", "S-001"), book("M-050", "S-097"))
    st = g.state
    st.players[0].mp, st.players[1].mp = 10, 3
    st.players[1].slots[0].partner = "Ex-011"
    to_battle(g, 0)
    submit(g, {"type": "pass", "player": 0})
    partner_ability(g, st.players[1].slots[0], player=1)
    battle_in(g, 2)
    submit(g, {"type": "declare_defense", "player": 1, "page": 2})
    assert st.pending is not None and st.pending.player == 1                  # 追加コスト 0 / 2
    choose(g, 2)
    assert st.players[1].mp == 1


def test_ex035_brago_base_cost_minus_5():
    # 《いきなさい》…自分の「ブラゴ」の術1つの本来のコストを－5する(0より小さくはならない)
    g, _ = mk(book("M-005", "S-011"), book("M-040"))
    st = g.state
    st.players[0].mp = 5
    st.players[0].slots[0].partner = "Ex-035"
    to_battle(g, 0)
    partner_ability(g, st.players[0].slots[0])
    submit(g, {"type": "pass", "player": 1})
    attack(g, 2)
    assert st.players[0].mp == 5


def test_pr010_zakeru_cost_minus_1_and_plus_2000():
    # 【ステイ】このターン中、自分の「ガッシュ・ベル」の術「ザケル」すべての、本来のコストは1少なくなり、魔力が+2000される
    g, _ = mk(book("M-001", "PR-010", "S-029"), book("M-001"))
    st = g.state
    st.players[0].mp = 10
    to_battle(g, 0)
    use_event(g)
    assert spell_cost(g, 0, 9, g.db["S-112"]) == 3                             # 「ザケルガ」は対象外
    submit(g, {"type": "pass", "player": 1})
    attack(g, 3)                                                               # ザケル:コスト 3 → 2
    assert st.players[0].mp == 8
    pass_effects(g)
    finish_damage(g)
    assert showdown(g)["attacker_total"] == 4000 + 3000 + 2000


# ---------------------------------------------------------------- 魔物效果攻擊

def test_m069_mamodo_attack():
    # 《カンフー》MPを2へらす→合計魔力6000で攻撃(相手の魔本に2ダメージ)する
    g, _ = mk(book("M-069"), book("M-040"))
    st = g.state
    st.players[0].mp = 4
    to_battle(g, 0)
    pos1 = st.players[1].pos
    mamodo_attack(g, st.players[0].slots[0])
    assert st.players[0].mp == 2
    no_defense_pass(g)
    finish_damage(g)
    assert showdown(g)["attacker_total"] == 6000 and st.players[1].pos == pos1 + 4
    assert code(g, {"type": "declare_attack", "player": 0, "mode": "mamodo",
                    "slot_uid": st.players[0].slots[0].uid}) == "attack.used"


def test_m068_mamodo_attack_twice_per_turn():
    # 《連続パンチ》MPを1へらす→この効果は、1ターンに2回まで使える。合計魔力6000で攻撃(相手の魔本に1ダメージ)する
    g, _ = mk(book("M-068"), book("M-040"))
    st = g.state
    st.players[0].mp = 5
    to_battle(g, 0)
    pos1 = st.players[1].pos
    danny = st.players[0].slots[0]
    for _ in range(2):
        mamodo_attack(g, danny)
        no_defense_pass(g)
        finish_damage(g)
    assert st.players[0].mp == 3 and st.players[1].pos == pos1 + 4
    assert code(g, {"type": "declare_attack", "player": 0, "mode": "mamodo",
                    "slot_uid": danny.uid}) == "attack.used"


def test_m068_snapshot_used_only_after_second_attack():
    from gash.api.views import snapshot
    g, _ = mk(book("M-068"), book("M-040"))
    st = g.state
    st.players[0].mp = 5
    to_battle(g, 0)
    danny = st.players[0].slots[0]

    def used():
        return snapshot(g, None)["players"][0]["slots"][0]["mamodo_attack_used"]

    for expected in (False, "turn"):
        mamodo_attack(g, danny)
        no_defense_pass(g)
        finish_damage(g)
        assert used() == expected


# ---------------------------------------------------------------- 戰術

@pytest.mark.parametrize("heads", [True, False])
def test_s108_coin_plus_2000(heads):
    # 相手の魔本にダメージ。コインを投げてオモテなら、この術の魔力を+2000する
    g, _ = mk(book("M-001", "S-108"), book("M-040"))
    st = g.state
    g.rng = Rng(HEADS if heads else TAILS)
    st.players[0].mp = 5
    to_battle(g, 0)
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    events = submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    assert [e["source"] for e in events if e["type"] == "coin_flipped"] == ["S-108"]
    no_defense_pass(g)
    finish_damage(g)
    assert showdown(g)["attacker_total"] == 4000 + 1000 + (2000 if heads else 0)


@pytest.mark.parametrize("heads", [True, False])
def test_s109_counter_coin_at_win(heads):
    # 【カウンター】魔力勝負で勝ったとき、コインを投げてオモテなら、相手の魔本にダメージ
    g, _ = mk(book("M-012", "Ex-038"), book("M-001", "S-109"))
    st = g.state
    g.rng = Rng(HEADS if heads else TAILS)
    st.players[0].mp, st.players[1].mp = 10, 10
    to_battle(g, 0)
    pos0 = st.players[0].pos
    battle_in(g, 2)
    events = submit(g, {"type": "declare_defense", "player": 1, "page": 2})
    assert not [e for e in events if e["type"] == "coin_flipped"]             # 宣言時には投げない
    pass_effects(g)
    finish_damage(g)
    assert showdown(g)["winner"] == "defender"
    assert [e["source"] for e in g.events if e["type"] == "coin_flipped" and e["source"] != "setup"] == ["S-109"]
    assert st.players[0].pos == pos0 + (2 if heads else 0)


def test_s110_no_spells_after_damage():
    # 相手の魔本にダメージ。相手の魔本か魔物にダメージをあたえたとき、このターン中、相手は術を使えない
    g, _ = mk(book("M-001", "S-110", "S-001"), book("M-001", "S-003"))
    st = g.state
    st.players[0].mp, st.players[1].mp = 10, 10
    to_battle(g, 0)
    attack(g, 2)
    pass_effects(g)
    finish_damage(g)
    battle_in(g, 3)
    page = st.players[1].open_pages()[0]                                       # めくられた後のページの「ザケル」
    assert code(g, {"type": "declare_defense", "player": 1, "page": page}) == "spell.restricted"


@pytest.mark.parametrize("heads", [True, False])
def test_s111_coin_cannot_protect(heads):
    # 相手の魔本にダメージ。コインを投げてオモテなら、相手は、この術のダメージを「かばう」ことができない
    g, _ = mk(book("M-001", "S-111"), book("M-040"))
    st = g.state
    g.rng = Rng(HEADS if heads else TAILS)
    st.players[0].mp = 10
    to_battle(g, 0)
    add_slot(g, 1, "M-002")
    attack(g, 2)
    pass_effects(g)
    assert (st.pending is None or st.pending.kind != "protect") is heads


def test_s112_turn_page_when_protected():
    # 相手の魔本にダメージ。この術のダメージを「かばわれた」とき、相手の魔本を1枚めくる
    g, _ = mk(book("M-001", "S-112"), book("M-040"))
    st = g.state
    st.players[0].mp = 10
    to_battle(g, 0)
    guard = add_slot(g, 1, "M-002")
    pos1 = st.players[1].pos
    attack(g, 2)
    pass_effects(g)
    assert st.pending.kind == "protect"
    choose(g, guard.uid)
    finish_damage(g)
    assert guard.injured and st.players[1].pos == pos1 + 2


def test_s112_no_extra_page_when_not_protected():
    g, _ = mk(book("M-001", "S-112"), book("M-040"))
    st = g.state
    st.players[0].mp = 10
    to_battle(g, 0)
    pos1 = st.players[1].pos
    attack(g, 2)
    pass_effects(g)
    finish_damage(g)
    assert st.players[1].pos == pos1 + 2 * 2


# ---------------------------------------------------------------- NPC 自我對戰

SELFPLAY_BOOKS = (
    ("PR-002", "S-107", "S-108", "S-109", "S-110", "S-111", "S-112", "Ex-013", "Ex-014", "Ex-020", "Ex-041",
     "PR-004", "PR-011", "Ex-001", "Ex-007", "PR-010", "E-046", "E-048", "E-049", "Ex-023", "M-064", "PR-003",
     "Ex-027", "Ex-002", "Ex-008", "M-068", "M-069", "Ex-036", "M-056", "Ex-033", "M-067", "Ex-042"),
    ("Ex-005", "Ex-017", "Ex-018", "Ex-011", "M-050", "S-096", "Ex-006", "Ex-019", "Ex-012", "M-011", "S-018",
     "Ex-028", "Ex-040", "Ex-035", "M-005", "S-011", "Ex-004", "Ex-016", "Ex-010", "M-021", "S-038", "Ex-029",
     "Ex-030", "Ex-042", "Ex-038", "Ex-039", "Ex-009", "M-012", "E-046", "E-049", "E-048", "Ex-023"),
)


@pytest.mark.slow
@pytest.mark.parametrize("levels", [("normal", "normal"), ("normal", "dummy"), ("dummy", "normal")])
@pytest.mark.parametrize("seed", [1, 2, 3])
def test_npc_selfplay_with_batch_cards(levels, seed):
    import random

    from gash import npc
    from gash.engine.awaiting import awaited_player
    from gash.engine.engine import new_game
    from gash.engine.state import GAME_OVER
    books = [list(b) for b in SELFPLAY_BOOKS]
    g = new_game(books[0], seed=seed, decks=(books[0], books[1]))
    rngs = [random.Random(f"{seed}:{p}") for p in (0, 1)]
    for _ in range(3000):
        if g.state.phase == GAME_OVER:
            break
        p = awaited_player(g)
        assert npc.submit_ranked(g, p, npc.decide(g, p, levels[p], rngs[p])) is not None
    assert g.state.phase == GAME_OVER
