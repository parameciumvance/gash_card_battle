"""第 3 賽季效果第 2 批:限制、無效、傷害與負傷(card-effects「第 3 賽季卡片的開放」)。依日文效果文逐卡驗證可觀察的結果。

限制 E-047、Ex-015、Ex-044、P-038、P-042、P-043、PR-005、PR-009;無效 M-055、M-057、P-040;
傷害與保護 Ex-024、Ex-031、Ex-043、Ex-047、M-054;負傷與回復 M-059、PR-008;棄掉 Ex-021、M-061、M-066;MP Ex-048。
"""

import pytest

from gash.engine.cards import pending_cards
from gash.engine.engine import _start_damage, mamodo_effect_block, remove_restrictions, slot_power, submit
from gash.engine.state import DUR_TURN, Modifier
from tests.test_level2 import HEADS, TAILS, Rng, book, mk, to_battle
from tests.test_level3 import (
    ability, add_slot, attack, battle_in, choose, code, end_turn, events_of, finish_damage, pass_effects, use_event,
)

BATCH = ("E-047", "Ex-015", "Ex-021", "Ex-024", "Ex-031", "Ex-043", "Ex-044", "Ex-047", "Ex-048",
         "M-054", "M-055", "M-057", "M-059", "M-061", "M-066", "P-038", "P-040", "P-042", "P-043",
         "PR-005", "PR-008", "PR-009")


def opp_attacks(g, page, defend_page=None):
    """玩家 1 宣告攻擊、玩家 0 迎戰並(不)防禦,停在戰鬥中效果的時機(攻方先)。"""
    battle_in(g, page, player=1)
    if defend_page is None:
        submit(g, {"type": "no_defense", "player": 0})
    else:
        submit(g, {"type": "declare_defense", "player": 0, "page": defend_page})


def mamodo_attack(g, slot, player=0):
    submit(g, {"type": "declare_attack", "player": player, "mode": "mamodo", "slot_uid": slot.uid})
    submit(g, {"type": "battle_in_response", "player": 1 - player, "allow": True})


def damage_slot(g, player, slot, source_player):
    """戰鬥外對 player 的 slot 造成 1 次效果傷害(走一般的傷害管線)。"""
    return _start_damage(g, [], [{"kind": "slot", "player": player, "slot_uid": slot.uid, "amount": 1}],
                         {"cause": "effect", "source": "X", "source_player": source_player, "amount": 1})


def labels(g):
    return [o["label"] for o in g.state.pending.options]


# ---------------------------------------------------------------- 開放

def test_batch_size():
    assert len(set(BATCH)) == 22


def test_batch_cards_are_open():
    assert not set(BATCH) & pending_cards()


# ---------------------------------------------------------------- E-047

def test_e047_blocks_only_chosen_mamodo_spells():
    # 【ステイ】相手の魔物1体を選ぶ。このターン中、相手はその魔物の術を使えない。
    g, _ = mk(book("M-001", "E-047", "S-001"), book("M-001", "S-029"))
    st = g.state
    st.players[0].mp = 5
    to_battle(g, 0)
    a = st.players[1].slots[0]
    b = add_slot(g, 1, "M-002")
    st.players[1].mp = 10
    use_event(g, 2)
    assert st.pending.player == 0
    choose(g, a.uid)
    assert mamodo_effect_block(g, 1, a) is None                              # 魔物效果不受影響
    submit(g, {"type": "pass", "player": 1})
    battle_in(g, 3)
    assert code(g, {"type": "declare_defense", "player": 1, "page": 2, "slot_uid": a.uid}) == "spell.restricted"
    submit(g, {"type": "declare_defense", "player": 1, "page": 2, "slot_uid": b.uid})   # 其他魔物可以
    assert g.state.battle.defense_spell == "S-029"


# ---------------------------------------------------------------- Ex-015

def _ex015_attack(defend_page=None):
    g, _ = mk(book("Ex-003", "Ex-015"), book("M-001", "S-001"))
    st = g.state
    st.players[0].mp, st.players[1].mp = 5, 5
    to_battle(g, 0)
    attack(g, 2, defend_page=defend_page)
    pass_effects(g)
    finish_damage(g)
    return g


def test_ex015_win_blocks_opponent_until_end_of_next_turn():
    # 【ステイ】次のターンのエンドフェイズまで、相手は「魔物の効果」や術を使えない。
    g = _ex015_attack()
    st = g.state
    st.players[1].mp = 10
    end_turn(g)
    assert st.turn_player == 1
    assert code(g, {"type": "declare_attack", "player": 1, "page": 2}) == "spell.restricted"


def test_ex015_no_effect_when_defender_wins():
    g = _ex015_attack(defend_page=2)                                           # 1500 + 3000 < 4000 + 2000
    st = g.state
    assert [e for e in g.events if e["type"] == "showdown"][-1]["winner"] == "defender"
    assert not any(m.kind == "restriction" for m in st.modifiers)


# ---------------------------------------------------------------- Ex-021

def test_ex021_power_then_discard_at_end_phase():
    # 自分の魔物1体を選ぶ。●【ステイ】このターン中、その魔物の魔力を+5000する。
    # ●【スタンバイ】このターンのエンドフェイズに、その魔物を捨て札にする。
    g, _ = mk(book("M-001", "Ex-021"), book("M-001"))
    st = g.state
    to_battle(g, 0)
    gash = st.players[0].slots[0]
    other = add_slot(g, 0, "M-050")
    use_event(g)
    assert st.pending.player == 0
    choose(g, gash.uid)
    assert slot_power(g, 0, gash) == 9000
    submit(g, {"type": "pass", "player": 1})
    events = submit(g, {"type": "pass", "player": 0})
    assert "M-001" in st.players[0].discard and st.players[0].slots == [other]
    kinds = [e["type"] for e in events]
    assert kinds.index("mamodo_discarded") < kinds.index("pages_flipped")       # 強制翻頁之前


# ---------------------------------------------------------------- Ex-024

def test_ex024_damage_can_be_protected():
    # この効果は、相手の魔物が2体以上いるときに使える。相手の魔物1体を選び、ダメージをあたえる。(FAQ:かばえる)
    g, _ = mk(book("M-001", "Ex-024"), book("M-001"))
    st = g.state
    st.players[0].mp = 8
    to_battle(g, 0)
    a = st.players[1].slots[0]
    b = add_slot(g, 1, "M-050")
    use_event(g)
    choose(g, a.uid)
    assert st.pending.kind == "protect" and st.pending.player == 1
    assert b.uid in [o["value"] for o in st.pending.options]
    choose(g, None)
    assert a.injured and not b.injured


def test_ex024_needs_two_opponent_mamodo():
    g, _ = mk(book("M-001", "Ex-024"), book("M-001"))
    g.state.players[0].mp = 8
    to_battle(g, 0)
    assert code(g, {"type": "use_book_card", "player": 0, "page": 2}) == "event.condition"


# ---------------------------------------------------------------- Ex-031

def _pati_defends(spell="S-002", mamodo="M-001"):
    g, _ = mk(book(mamodo, spell), book("Ex-031"))
    st = g.state
    st.players[0].mp, st.players[1].mp = 10, 3
    to_battle(g, 0)
    return g, st.players[1].slots[0]


def test_ex031_reduces_spell_attack_damage():
    # 《かわいい攻撃だこと》MPを1へらす→【ステイ】このバトル中、相手の術による攻撃のダメージを-1する。
    g, pati = _pati_defends()
    st = g.state
    pos1 = st.players[1].pos
    attack(g, 2)
    submit(g, {"type": "pass", "player": 0})
    submit(g, ability(1, pati))
    assert st.players[1].mp == 2
    pass_effects(g)
    finish_damage(g)
    assert st.players[1].pos == pos1 + 2                                       # 2 → 1


def test_ex031_not_against_mamodo_effect_attack():
    g, pati = _pati_defends(mamodo="M-027")
    mamodo_attack(g, g.state.players[0].slots[0])
    submit(g, {"type": "no_defense", "player": 1})
    submit(g, {"type": "pass", "player": 0})
    assert code(g, ability(1, pati)) == "ability.condition"


def test_ex031_not_in_own_attack():
    g, _ = mk(book("Ex-031", "Ex-043"), book("M-001"))
    st = g.state
    st.players[0].mp = 10
    to_battle(g, 0)
    attack(g, 2)
    assert code(g, ability(0, st.players[0].slots[0])) == "ability.condition"


# ---------------------------------------------------------------- Ex-043

def _ex043_after_opponent_turn(opp_book, opp_page=2):
    """回合 1:玩家 0 不行動;回合 2:玩家 1 以傷害 1 的戰術攻擊;回合 3:玩家 0 以 Ex-043 攻擊
    (強制翻頁與受到的傷害使玩家 0 翻開第 6、7 頁)。"""
    g, _ = mk(book("Ex-031", "S-029", "S-029", "S-029", "S-029", "Ex-043"), book(*opp_book))
    st = g.state
    st.players[0].mp, st.players[1].mp = 10, 10
    to_battle(g, 0)
    end_turn(g)
    opp_attacks(g, opp_page)
    pass_effects(g)
    finish_damage(g)
    end_turn(g)
    assert st.turn_player == 0
    pos1 = st.players[1].pos
    attack(g, 6)
    pass_effects(g)
    finish_damage(g)
    showdown = [e for e in g.events if e["type"] == "showdown"][-1]
    return showdown["attacker_total"], (st.players[1].pos - pos1) // 2


def test_ex043_bonus_after_opponent_used_thunder():
    # 直前のターンに、相手が「雷」属性の術を使っていれば、この術の魔力を+4000、ダメージを+2する。
    assert _ex043_after_opponent_turn(("M-001", "S-001")) == (3500 + 2000 + 4000, 3)


def test_ex043_no_bonus_without_thunder():
    assert _ex043_after_opponent_turn(("M-050", "Ex-017")) == (3500 + 2000, 1)


def test_ex043_negated_thunder_spell_still_counts():
    from gash.engine.engine import _record_spell_attr
    g, _ = mk(book("Ex-031", "Ex-043"), book("M-001"))
    st = g.state
    st.turn_no = 5
    _record_spell_attr(g, 1, g.db["S-001"])                                    # 宣告即算(之後被無效也算)
    st.turn_no = 6
    st.players[0].mp = 10
    to_battle(g, 0)
    attack(g, 2)
    assert st.battle.data["attack_damage_delta"] == 2


# ---------------------------------------------------------------- Ex-044

def test_ex044_coin_per_opponent_mamodo():
    # 【ステイ】相手の魔物1体を選ぶ。コインを投げてオモテなら、次のターンのエンドフェイズまで、相手は、
    # その魔物の「魔物の効果」や術を使えない。これを相手の場の魔物すべてについておこなう。
    g, _ = mk(book("Ex-032", "Ex-044"), book("M-001"))
    st = g.state
    st.players[0].mp = 5
    to_battle(g, 0)
    a = st.players[1].slots[0]
    b = add_slot(g, 1, "M-050")
    g.rng = Rng(HEADS, TAILS)
    events = submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    assert len(events_of(events, "coin_flipped")) == 2
    assert mamodo_effect_block(g, 1, a) == "mamodo_locked" and mamodo_effect_block(g, 1, b) is None
    end_turn(g)
    assert mamodo_effect_block(g, 1, a) == "mamodo_locked"                     # 到下一回合結束階段


# ---------------------------------------------------------------- Ex-047

def _ex047(opp_extra="M-050"):
    g, _ = mk(book("M-001", "Ex-047", "S-001"), book("M-001", "S-029"))
    st = g.state
    st.players[0].mp = 10
    to_battle(g, 0)
    a = st.players[1].slots[0]
    b = add_slot(g, 1, opp_extra) if opp_extra else None
    use_event(g, 2)
    choose(g, a.uid)
    submit(g, {"type": "pass", "player": 1})
    return g, a, b


def test_ex047_forces_protect_with_chosen_mamodo():
    # 【ステイ】相手の魔物1体を選ぶ。このターン中、相手の魔本か相手の魔物がダメージをうけるとき、
    # 相手は、可能な限りその魔物ででダメージを「かばう」。
    g, a, b = _ex047()
    st = g.state
    pos1 = st.players[1].pos
    attack(g, 3)
    pass_effects(g)
    assert st.pending is None and st.battle is None                            # 不詢問保護
    assert a.injured and st.players[1].pos == pos1
    assert any(e["type"] == "protect_forced" for e in g.events)


def test_ex047_injured_chosen_mamodo_still_protects():
    g, a, b = _ex047()
    a.injured = True
    attack(g, 3)
    pass_effects(g)
    assert "M-001" in g.state.players[1].discard


def test_ex047_does_not_prevent_defense():
    g, a, b = _ex047()
    st = g.state
    st.players[1].mp = 10
    attack(g, 3, defend_page=2)
    assert st.battle.defense_spell == "S-029"


def test_ex047_chosen_mamodo_itself_damaged_asks_normally():
    g, a, b = _ex047()
    st = g.state
    damage_slot(g, 1, a, source_player=0)
    assert st.pending.kind == "protect" and b.uid in [o["value"] for o in st.pending.options]


def test_ex047_overrides_p027():
    # FAQ:相手が「ヒゲ」を使った場合も、「ナオミちゃん」で指定した魔物でかばう
    g, _ = mk(book("M-001", "Ex-047", "S-001"), book("M-041"))
    st = g.state
    st.players[0].mp, st.players[1].mp = 10, 10
    zoboron = st.players[1].slots[0]
    zoboron.partner = "P-027"
    a = add_slot(g, 1, "M-050")
    to_battle(g, 0)
    use_event(g, 2)
    choose(g, a.uid)
    submit(g, {"type": "pass", "player": 1})
    gash = st.players[0].slots[0]
    attack(g, 3)
    submit(g, {"type": "pass", "player": 0})
    submit(g, ability(1, zoboron, zone="partner"))                             # ヒゲ:指定ガッシュ
    pass_effects(g)
    assert st.pending is None and a.injured and not gash.injured


# ---------------------------------------------------------------- Ex-048

def _ex048(mp0, mp1, partner=None):
    g, _ = mk(book("M-001", "Ex-048"), book("M-001"))
    st = g.state
    st.players[0].slots[0].partner = partner
    st.players[0].mp, st.players[1].mp = mp0, mp1
    to_battle(g, 0)
    return g


def test_ex048_sets_both_to_four():
    # 自分と相手のMPを4にする。※MPが5以上のとき、この効果は「MPをへらす」効果としてあつかう。
    g = _ex048(3, 9)
    use_event(g)
    st = g.state
    assert (st.players[0].mp, st.players[1].mp) == (4, 4)
    assert st.turn_no in st.players[0].opp_mp_reduced_turns                     # 「減少對手 MP」的效果
    assert st.players[1].mp_reduced_by_opponent == 5


def test_ex048_lower_opponent_mp_raised():
    g = _ex048(9, 1)
    use_event(g)
    st = g.state
    assert (st.players[0].mp, st.players[1].mp) == (4, 4)
    assert st.turn_no not in st.players[0].opp_mp_reduced_turns


def test_ex048_opponent_guard_blocks_reduction():
    g = _ex048(3, 9)
    st = g.state
    st.modifiers.append(Modifier(kind="mp_guard", source="P-021", owner=1, duration=DUR_TURN,
                                 created_turn=st.turn_no, target_player=1))
    use_event(g)
    assert (st.players[0].mp, st.players[1].mp) == (4, 9)


def test_ex048_p020_blocks_own_increase_in_battle_phase():
    g = _ex048(3, 9, partner="P-020")
    use_event(g)
    assert (g.state.players[0].mp, g.state.players[1].mp) == (2, 4)


# ---------------------------------------------------------------- M-054

def _m054(heads, other_attacks=False):
    g, _ = mk(book("M-054", "S-001"), book("M-001", "S-029"))
    st = g.state
    st.players[0].mp, st.players[1].mp = 10, 10
    to_battle(g, 0)
    gash = st.players[0].slots[0]
    other = add_slot(g, 0, "M-001")
    g.rng = Rng(HEADS if heads else TAILS)
    submit(g, ability(0, gash))
    submit(g, {"type": "pass", "player": 1})
    battle_in(g, 2, slot=other if other_attacks else gash)
    return g


def test_m054_heads_undefendable():
    # 《突っ込め!》MPを1へらす→【スタンバイ】コインを投げてオモテなら、このターン中の次のバトルで、
    # 自分がこの魔物の術で攻撃したとき、相手は防御できない。
    g = _m054(True)
    assert code(g, {"type": "declare_defense", "player": 1, "page": 2}) == "defense.undefendable"


def test_m054_tails_defendable():
    g = _m054(False)
    submit(g, {"type": "declare_defense", "player": 1, "page": 2})
    assert g.state.battle.defense_spell == "S-029"


def test_m054_only_this_mamodo():
    g = _m054(True, other_attacks=True)
    submit(g, {"type": "declare_defense", "player": 1, "page": 2})
    assert g.state.battle.defense_spell == "S-029"


def test_m054_own_turn_only():
    g, _ = mk(book("M-001", "S-001"), book("M-054"))
    st = g.state
    st.players[1].mp = 5
    to_battle(g, 0)
    assert code(g, ability(1, st.players[1].slots[0])) in ("ability.timing", "priority.other")


# ---------------------------------------------------------------- M-055

def _m055(coins=(), opp_slots=1):
    g, _ = mk(book("M-055", "S-008"), book("M-001"))
    st = g.state
    st.players[0].mp = 10
    to_battle(g, 0)
    for _ in range(opp_slots - 1):
        add_slot(g, 1, "M-050")
    submit(g, ability(0, st.players[0].slots[0]))
    submit(g, {"type": "pass", "player": 1})
    g.rng = Rng(*coins)
    battle_in(g, 2)
    return g


def test_m055_heads_damages_chosen_mamodo():
    # 《撃砕の構え》…コインを投げる。オモテなら、その術は、相手の魔本にダメージをあたえるのではなく、
    # 相手の魔物1体を選び、その魔物にダメージをあたえる。ウラなら、その術は無効になる。
    g = _m055((HEADS,), opp_slots=2)
    st = g.state
    assert st.pending.kind == "pick_effect" and st.pending.player == 0
    assert labels(g) == ["coin_redirect_damage", "skip"]
    choose(g, "use")
    assert st.pending.player == 0                                              # 攻擊方選魔物
    target = st.players[1].slots[1]
    choose(g, target.uid)
    assert st.battle.step == "defense"
    pos1 = st.players[1].pos
    submit(g, {"type": "no_defense", "player": 1})
    pass_effects(g)
    finish_damage(g)
    assert target.injured and st.players[1].pos == pos1


def test_m055_tails_negates_spell():
    g = _m055((TAILS,))
    st = g.state
    choose(g, "use")
    assert st.battle.attack_negated
    pos1 = st.players[1].pos
    submit(g, {"type": "no_defense", "player": 1})
    pass_effects(g)
    assert st.players[1].pos == pos1 and not st.players[1].slots[0].injured


def test_m055_skip_keeps_book_damage():
    g = _m055()
    st = g.state
    choose(g, None)
    pos1 = st.players[1].pos
    submit(g, {"type": "no_defense", "player": 1})
    pass_effects(g)
    finish_damage(g)
    assert st.players[1].pos == pos1 + 4
    assert not any(e["type"] == "coin_flipped" and e.get("source") == "M-055" for e in g.events)


def test_m055_not_offered_without_opponent_mamodo():
    g, _ = mk(book("M-055", "S-008"), book("M-001"))
    st = g.state
    st.players[0].mp = 10
    to_battle(g, 0)
    submit(g, ability(0, st.players[0].slots[0]))
    submit(g, {"type": "pass", "player": 1})
    st.players[1].slots.clear()
    battle_in(g, 2)
    assert st.pending is None and st.battle.step == "defense"


def test_m055_not_offered_for_other_mamodo():
    g, _ = mk(book("M-055", "S-008"), book("M-001"))
    st = g.state
    st.players[0].mp = 10
    to_battle(g, 0)
    submit(g, ability(0, st.players[0].slots[0]))
    submit(g, {"type": "pass", "player": 1})
    other = add_slot(g, 0, "M-033")
    battle_in(g, 2, slot=other)
    assert st.pending is None
    submit(g, {"type": "no_defense", "player": 1})
    pass_effects(g)
    finish_damage(g)
    assert not any(sb.kind == "on_attack" for sb in st.standby)               # 下一場戰鬥結束時消失


# ---------------------------------------------------------------- M-057

def _tio_defends(heads):
    g, _ = mk(book("M-001", "S-001"), book("M-057"))
    st = g.state
    st.players[0].mp, st.players[1].mp = 10, 5
    to_battle(g, 0)
    attack(g, 2)
    submit(g, {"type": "pass", "player": 0})
    g.rng = Rng(HEADS if heads else TAILS)
    submit(g, ability(1, st.players[1].slots[0]))
    return g


@pytest.mark.parametrize("heads", [True, False])
def test_m057_coin_negates_attack(heads):
    # 《護りの女神》MPを2へらす→コインを投げてオモテなら、このバトルの相手の攻撃1つを無効にする。
    g = _tio_defends(heads)
    st = g.state
    pos1 = st.players[1].pos
    assert st.players[1].mp == 3
    pass_effects(g)
    finish_damage(g)
    assert (st.players[1].pos == pos1) == heads


def test_m057_not_in_own_attack():
    g, _ = mk(book("M-057", "Ex-017"), book("M-001"))
    st = g.state
    st.players[0].mp = 10
    to_battle(g, 0)
    attack(g, 2)
    assert code(g, ability(0, st.players[0].slots[0])) == "ability.condition"


# ---------------------------------------------------------------- M-059

def _m059(*opp):
    g, _ = mk(book("M-059"), book(opp[0]))
    st = g.state
    to_battle(g, 0)
    add_slot(g, 0, "M-001")
    for number in opp[1:]:
        add_slot(g, 1, number)
    return g, st.players[0].slots[0]


def test_m059_injures_without_protection():
    # 《破滅への誘い》このカードを捨て札にする→相手の「健康状態」の魔物1体を選び、「負傷状態」にする(この効果はダメージではない)
    g, zeon = _m059("M-001", "M-050")
    st = g.state
    a = st.players[1].slots[0]
    submit(g, ability(0, zeon))
    assert "M-059" in st.players[0].discard
    assert st.pending.player == 0
    choose(g, a.uid)
    assert a.injured and st.pending is None


def test_m059_injures_damage_immune_mamodo():
    g, zeon = _m059("M-051")
    submit(g, ability(0, zeon))
    assert g.state.players[1].slots[0].injured


def test_m059_needs_healthy_opponent_mamodo():
    g, zeon = _m059("M-001")
    g.state.players[1].slots[0].injured = True
    assert code(g, ability(0, zeon)) == "ability.condition"


# ---------------------------------------------------------------- M-061 / M-066

def test_m061_discards_all_partners_except_opponent_guarded():
    # 《心の解放》このカードを捨て札にする→【スタンバイ】このターンのエンドフェイズに、自分と相手のパートナーすべてを選び、捨て札にする。
    # M-066《恵は私が守る!》この魔物につけられたパートナーは、相手の効果では捨て札にならない。
    g, _ = mk(book("M-061"), book("M-066"))
    st = g.state
    to_battle(g, 0)
    own = add_slot(g, 0, "M-066", partner="P-001")                             # 自己的效果:照樣棄掉
    tio = st.players[1].slots[0]
    tio.partner = "P-002"
    other = add_slot(g, 1, "M-001", partner="P-003")
    submit(g, ability(0, st.players[0].slots[0]))
    assert other.partner == "P-003"                                            # 結束階段才棄
    submit(g, {"type": "pass", "player": 1})
    submit(g, {"type": "pass", "player": 0})
    assert tio.partner == "P-002" and other.partner is None and own.partner is None


def test_m066_partner_not_discarded_by_opponent_effect():
    g, _ = mk(book("M-001", "E-030"), book("M-066"))
    st = g.state
    st.players[1].slots[0].partner = "P-032"
    to_battle(g, 0)
    assert code(g, {"type": "use_book_card", "player": 0, "page": 2}) == "event.condition"


# ---------------------------------------------------------------- P-038

def test_p038_blocks_opponent_events_in_holders_battle_phase():
    # 《忌まわしい事件》このカードが場にある→自分のバトルフェイズに、相手はイベントカードを使えない。
    g, _ = mk(book("M-001", "S-029", "S-029", "E-047"), book("M-001"))
    st = g.state
    st.players[1].slots[0].partner = "P-038"
    to_battle(g, 0)
    end_turn(g)
    assert st.turn_player == 1
    submit(g, {"type": "pass", "player": 1})
    assert code(g, {"type": "use_book_card", "player": 0, "page": 4}) == "event.restricted"


def test_p038_own_turn_not_affected():
    g, _ = mk(book("M-001", "E-047"), book("M-001"))
    st = g.state
    st.players[1].slots[0].partner = "P-038"
    to_battle(g, 0)
    events = use_event(g)
    assert events_of(events, "book_card_used")


# ---------------------------------------------------------------- P-040

def test_p040_negates_opponent_spell():
    # 《術無効》このカードを捨て札にする→このバトルの、相手の術1つを無効にする。
    g, _ = mk(book("M-001", "S-001"), book("M-050"))
    st = g.state
    st.players[0].mp = 10
    st.players[1].slots[0].partner = "P-040"
    to_battle(g, 0)
    pos1 = st.players[1].pos
    attack(g, 2)
    submit(g, {"type": "pass", "player": 0})
    submit(g, ability(1, st.players[1].slots[0], zone="partner"))
    assert "P-040" in st.players[1].discard
    pass_effects(g)
    finish_damage(g)
    assert st.players[1].pos == pos1


# ---------------------------------------------------------------- P-042

def _p042(attack_with_danny=True):
    g, _ = mk(book("M-039", "S-001"), book("M-001"))
    st = g.state
    st.players[0].mp = 10
    st.players[1].slots[0].partner = "P-040"
    danny = st.players[0].slots[0]
    danny.partner = "P-042"
    gash = add_slot(g, 0, "M-001")
    to_battle(g, 0)
    submit(g, ability(0, danny, zone="partner"))
    submit(g, {"type": "pass", "player": 1})
    if attack_with_danny:
        mamodo_attack(g, danny)
    else:
        battle_in(g, 2, slot=gash)
    submit(g, {"type": "no_defense", "player": 1})
    submit(g, {"type": "pass", "player": 0})
    return g


def test_p042_blocks_events_and_partner_effects_in_that_battle():
    # 《我が息子》…このターン中の次のバトルで、自分が「ダニー」の術や「魔物の効果」で攻撃するとき、
    # そのバトル中、相手はパートナーの効果やイベントカードを使えない。
    from gash.engine.engine import restricted
    from gash.engine.state import NO_EVENTS
    g = _p042()
    st = g.state
    assert restricted(g, 1, NO_EVENTS)                                         # 戰鬥中本來就沒有可用的事件卡
    assert code(g, ability(1, st.players[1].slots[0], zone="partner")) == "ability.partner_restricted"
    pass_effects(g)
    finish_damage(g)
    assert not restricted(g, 1, NO_EVENTS)                                     # 只限該場戰鬥


def test_p042_other_mamodo_attack_not_affected():
    g = _p042(attack_with_danny=False)
    st = g.state
    submit(g, ability(1, st.players[1].slots[0], zone="partner"))
    assert "P-040" in st.players[1].discard


# ---------------------------------------------------------------- P-043

def _p043(mode, attack_with_wonrei=True):
    g, _ = mk(book("M-069", "S-001"), book("M-001", "S-029"))
    st = g.state
    st.players[0].mp, st.players[1].mp = 10, 10
    wonrei = st.players[0].slots[0]
    wonrei.partner = "P-043"
    gash = add_slot(g, 0, "M-001")
    a = st.players[1].slots[0]
    b = add_slot(g, 1, "M-002")
    to_battle(g, 0)
    submit(g, ability(0, wonrei, zone="partner"))
    assert st.pending.player == 0
    choose(g, a.uid)
    submit(g, {"type": "pass", "player": 1})
    if attack_with_wonrei:
        mamodo_attack(g, wonrei)
        assert st.pending.kind == "pick_effect" and st.pending.player == 0
        assert labels(g) == ["opponent_no_defense_spell", "opponent_no_protect"]
        choose(g, mode)
    else:
        battle_in(g, 2, slot=gash)
    return g, a, b


def test_p043_no_protect_with_chosen():
    # 《攻撃の支援》…●相手は、選んだ魔物でダメージを「かばう」ことができない。
    g, a, b = _p043("no_protect")
    st = g.state
    submit(g, {"type": "no_defense", "player": 1})
    pass_effects(g)
    assert st.pending.kind == "protect"
    values = [o["value"] for o in st.pending.options]
    assert a.uid not in values and b.uid in values


def test_p043_no_defense_spell_of_chosen():
    # ●相手は、選んだ魔物の防御の術を使えない。
    g, a, b = _p043("no_defense_spell")
    assert code(g, {"type": "declare_defense", "player": 1, "page": 2, "slot_uid": a.uid}) == "spell.restricted"
    submit(g, {"type": "declare_defense", "player": 1, "page": 2, "slot_uid": b.uid})
    assert g.state.battle.defense_spell == "S-029"


def test_p043_other_mamodo_attack_not_asked():
    g, a, b = _p043(None, attack_with_wonrei=False)
    st = g.state
    assert st.pending is None
    submit(g, {"type": "declare_defense", "player": 1, "page": 2, "slot_uid": a.uid})
    assert st.battle.defense_spell == "S-029"


# ---------------------------------------------------------------- PR-005

def _pr005(injured=True):
    g, _ = mk(book("M-001", "PR-005", "S-001"), book("M-001", "S-029"))
    st = g.state
    st.players[0].mp, st.players[1].mp = 0, 10
    other = add_slot(g, 0, "M-050")
    other.injured = injured
    return g, other


def test_pr005_all_effects_in_chosen_order():
    # このカードは、自分のバトルフェイズの一番最初に使う。次の効果のすべてを、すきな順で使う。
    g, other = _pr005()
    st = g.state
    to_battle(g, 0)
    use_event(g)
    assert st.pending.kind == "pick_effect" and st.pending.player == 0
    assert labels(g) == ["heal_all_injured", "gain_mp_2", "restrict_both_effects_spells"]
    events = choose(g, "mp")
    assert labels(g) == ["heal_all_injured", "restrict_both_effects_spells"]
    events += choose(g, "restrict")
    assert st.pending is None and not other.injured and st.players[0].mp == 2
    kinds = [e["type"] for e in events]
    assert kinds.index("mp_changed") < kinds.index("modifier_added") < kinds.index("mamodo_healed")


def test_pr005_restricts_both_players():
    g, other = _pr005()
    st = g.state
    to_battle(g, 0)
    use_event(g)
    for value in ("heal", "mp"):
        choose(g, value)
    submit(g, {"type": "pass", "player": 1})
    st.players[0].mp = 10
    assert code(g, {"type": "declare_attack", "player": 0, "page": 3}) == "spell.restricted"


def test_pr005_no_injured_omits_heal():
    g, other = _pr005(injured=False)
    to_battle(g, 0)
    use_event(g)
    assert labels(g) == ["gain_mp_2", "restrict_both_effects_spells"]


def test_pr005_only_at_start_of_battle_phase():
    g, other = _pr005()
    st = g.state
    st.players[0].mp = 5
    st.players[0].slots[0].partner = "Ex-008"
    to_battle(g, 0)
    submit(g, ability(0, st.players[0].slots[0], zone="partner"))
    submit(g, {"type": "pass", "player": 1})
    assert code(g, {"type": "use_book_card", "player": 0, "page": 2}) == "event.condition"


# ---------------------------------------------------------------- PR-008

def _pr008(injured=True):
    g, _ = mk(book("PR-008"), book("M-001"))
    st = g.state
    st.players[0].mp = 5
    to_battle(g, 0)
    other = add_slot(g, 0, "M-001")
    other.injured = injured
    return g, other


@pytest.mark.parametrize("heads", [True, False])
def test_pr008_coin_heals(heads):
    # 《元気!》MPを1へらす→コインを投げてオモテなら、自分の「負傷状態」の魔物1体を選び、「健康状態」にする。
    g, other = _pr008()
    g.rng = Rng(HEADS if heads else TAILS)
    submit(g, ability(0, g.state.players[0].slots[0]))
    assert g.state.players[0].mp == 4 and other.injured != heads


def test_pr008_needs_injured_mamodo():
    g, other = _pr008(injured=False)
    assert code(g, ability(0, g.state.players[0].slots[0])) == "ability.condition"


# ---------------------------------------------------------------- PR-009

def _pr009():
    g, _ = mk(book("M-001", "PR-009", "S-001"), book("M-001"))
    st = g.state
    st.players[0].mp = 10
    to_battle(g, 0)
    tio = add_slot(g, 0, "M-050")
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    submit(g, {"type": "pass", "player": 1})
    return g, st.players[0].slots[0], tio


def test_pr009_cannot_use_gash_spells():
    # 【ステイ】次の自分のターンのエンドフェイズまで、●自分は、「ガッシュ・ベル」の術を使えない。
    g, gash, tio = _pr009()
    assert code(g, {"type": "declare_attack", "player": 0, "page": 3}) == "spell.restricted"


def test_pr009_book_and_gash_take_no_damage():
    # ●自分の魔本と自分の「ガッシュ・ベル」はダメージを受けない。
    g, gash, tio = _pr009()
    st = g.state
    pos0 = st.players[0].pos
    _start_damage(g, [], [{"kind": "book", "player": 0, "amount": 2}],
                  {"cause": "effect", "source": "X", "source_player": 1, "amount": 2})
    finish_damage(g)
    assert st.players[0].pos == pos0
    damage_slot(g, 0, gash, source_player=1)
    finish_damage(g)
    assert not gash.injured
    damage_slot(g, 0, tio, source_player=1)
    finish_damage(g)
    assert tio.injured


def test_pr009_removal_keeps_immunity():
    g, gash, tio = _pr009()
    st = g.state
    remove_restrictions(g, [], 0, {"spells"}, "self")
    st.players[0].mp = 10
    battle_in(g, 3)
    assert st.battle is not None
    damage_slot(g, 0, gash, source_player=1)
    finish_damage(g)
    assert not gash.injured


# ---------------------------------------------------------------- NPC 自我對戰

SELFPLAY_BOOKS = (
    ("M-054", "S-001", "PR-009", "M-057", "PR-008", "M-066", "P-040", "E-047", "Ex-021", "Ex-047", "S-002",
     "M-039", "P-042", "M-069", "P-043", "Ex-048", "PR-005", "Ex-024", "S-029", "Ex-017", "M-068", "Ex-042",
     "S-107", "S-108", "Ex-013", "Ex-041", "M-050", "S-096", "Ex-020", "E-046", "S-110", "Ex-039"),
    ("M-055", "S-008", "M-059", "M-061", "Ex-031", "Ex-043", "Ex-032", "Ex-044", "Ex-003", "Ex-015", "P-038",
     "Ex-040", "S-009", "S-010", "M-033", "E-047", "Ex-048", "PR-005", "Ex-024", "Ex-021", "S-011", "Ex-047",
     "M-051", "S-099", "S-100", "M-009", "Ex-035", "S-032", "S-033", "E-049", "Ex-023", "S-034"),
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
