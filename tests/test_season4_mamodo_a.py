"""第 4 賽季魔物與搭檔第 1 批(card-effects「第 4 賽季魔物與搭檔第 1 批」、game-engine「MP 增加的限制」,
season4-mamodo-a)。依日文效果文。
"""
import pytest

from gash.engine.cards import pending_cards
from gash.engine.effects.primitives import add_restriction
from gash.engine.engine import submit
from gash.engine.state import DUR_TURN, NO_MAMODO_EFFECTS
from tests.test_level2 import HEADS, TAILS, Rng, book, mk, to_battle
from tests.test_level3 import ability, add_slot, battle_in, choose, code, finish_damage, pass_effects

BATCH = ("Ex-052", "Ex-055", "M-071", "M-072", "M-076", "P-044", "P-050", "M-078", "M-082", "M-083",
         "P-046", "M-080", "M-081", "Ex-061", "P-045")


def test_batch_open():
    assert not set(BATCH) & pending_cards()


def setup(b0=("M-001",), b1=("M-001",), mp=10):
    g, _ = mk(book(*b0), book(*b1))
    st = g.state
    st.players[0].mp = st.players[1].mp = mp
    to_battle(g, 0)
    return g


def use(g, page=2, player=0):
    return submit(g, {"type": "use_book_card", "player": player, "page": page})


def mamodo_attack(g, slot, player=0):
    return submit(g, {"type": "declare_attack", "player": player, "mode": "mamodo", "slot_uid": slot.uid})


def end_turn(g):
    st = g.state
    tp = st.turn_player
    while st.turn_player == tp:
        if st.pending is not None:
            choose(g, st.pending.options[0]["value"])
            continue
        submit(g, {"type": "pass", "player": st.action_player})
    if st.phase == "start":
        to_battle(g, st.turn_player)


# ---------------------------------------------------------------- Ex-052 / Ex-055

@pytest.mark.parametrize("mamodo, partner, power, damage", [
    ("Ex-052", "P-028", 7000, 1),   # 「リィエン」
    ("Ex-055", "P-025", 6500, 2),   # 「ゴルドー」
])
def test_partner_conditioned_mamodo_attack(mamodo, partner, power, damage):
    g = setup()
    st = g.state
    slot = st.players[0].slots[0]
    slot.stack = [mamodo]
    assert code(g, {"type": "declare_attack", "player": 0, "mode": "mamodo", "slot_uid": slot.uid}) \
        == "attack.condition"
    slot.partner = partner
    pos1 = st.players[1].pos
    mamodo_attack(g, slot)
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    assert st.players[0].mp == 9 and st.battle.data["attack_fixed_power"] == power
    submit(g, {"type": "no_defense", "player": 1})
    pass_effects(g)
    finish_damage(g)
    assert st.players[1].pos == pos1 + 2 * damage


# ---------------------------------------------------------------- M-071

def _m071(defense_page=None, b1=("M-001",)):
    g = setup(("M-071", "S-008"), b1)
    st = g.state
    battle_in(g, 2)
    if defense_page is None:
        submit(g, {"type": "no_defense", "player": 1})
    else:
        submit(g, {"type": "declare_defense", "player": 1, "page": defense_page})
    return g


def test_m071_gains_mp_when_attack_loses():
    # 自分がこの魔物で攻撃したバトルの魔力勝負で負けたとき、自分のMPを3ふやす
    from gash.engine.engine import side_breakdown
    g = setup(("M-071", "S-008"), ("M-001", "S-001"))
    st = g.state
    battle_in(g, 2)
    submit(g, {"type": "declare_defense", "player": 1, "page": 2})
    st.battle.data.setdefault("defense_spell_power", []).append(
        {"kind": "spell_bonus", "source": "test", "amount": side_breakdown(g, st.battle, "attack")[0]})
    mp = st.players[0].mp
    pass_effects(g)
    finish_damage(g)
    assert st.players[0].mp == mp + 3


def test_m071_tie_counts_as_loss():
    from gash.engine.engine import side_breakdown
    g = setup(("M-071", "S-008"), ("M-001", "S-001"))
    st = g.state
    battle_in(g, 2)
    submit(g, {"type": "declare_defense", "player": 1, "page": 2})
    diff = side_breakdown(g, st.battle, "attack")[0] - side_breakdown(g, st.battle, "defense")[0]
    st.battle.data.setdefault("defense_spell_power", []).append({"kind": "spell_bonus", "source": "t", "amount": diff})
    mp = st.players[0].mp
    pass_effects(g)
    finish_damage(g)
    assert st.players[0].mp == mp + 3


def test_m071_no_mp_when_attack_wins():
    g = _m071()
    st = g.state
    mp = st.players[0].mp
    pass_effects(g)
    finish_damage(g)
    assert st.players[0].mp == mp


def test_m071_other_mamodo_attack_does_not_count():
    g = setup(("M-001", "S-001"), ("M-001", "S-001"))
    st = g.state
    add_slot(g, 0, "M-071")
    battle_in(g, 2, st.players[0].slots[0])
    submit(g, {"type": "declare_defense", "player": 1, "page": 2})
    st.battle.data.setdefault("defense_spell_power", []).append({"kind": "spell_bonus", "source": "t", "amount": 99999})
    mp = st.players[0].mp
    pass_effects(g)
    finish_damage(g)
    assert st.players[0].mp == mp


# ---------------------------------------------------------------- M-072

def test_m072_gains_mp_per_coin_thrown():
    # 自分がコイン1個を投げるごとに、自分のMPを1ふやす
    g = setup(("M-001", "Ex-100"))
    st = g.state
    add_slot(g, 0, "M-072")
    g.rng = Rng(TAILS, TAILS)
    mp = st.players[0].mp
    use(g)
    assert st.players[0].mp == mp + 2


def test_m072_reflip_counts():
    g = setup(("M-001", "Ex-100"))
    st = g.state
    add_slot(g, 0, "M-072")
    add_slot(g, 0, "M-012")
    g.rng = Rng(TAILS, TAILS, TAILS)
    mp = st.players[0].mp
    use(g)
    assert st.pending.kind == "coin_confirm"
    choose(g, 0)                                                            # M-012 重擲第 1 枚
    while st.pending is not None:
        choose(g, None)
    assert st.players[0].mp == mp + 3


def test_m072_blocked_by_mamodo_effect_restriction():
    g = setup(("M-001", "Ex-100"))
    st = g.state
    add_slot(g, 0, "M-072")
    add_restriction(g, [], source="E-025", owner=1, target_player=0, flag=NO_MAMODO_EFFECTS, duration=DUR_TURN)
    g.rng = Rng(TAILS, TAILS)
    mp = st.players[0].mp
    use(g)
    assert st.players[0].mp == mp


# ---------------------------------------------------------------- M-076 / P-044

def test_m076_caps_opponent_start_phase_mp():
    # 相手が、相手のスタートフェイズに「ふやせるMPの数」は2までとなる
    g, _ = mk(book("M-001"), book("M-076"))
    st = g.state
    st.turn_no = 3
    mp = st.players[0].mp
    submit(g, {"type": "flip_pages", "player": 0, "count": 3})
    assert st.players[0].mp == mp + 2


def test_m076_does_not_cap_own_start_phase():
    g, _ = mk(book("M-076"), book("M-001"))
    st = g.state
    st.turn_no = 3
    mp = st.players[0].mp
    submit(g, {"type": "flip_pages", "player": 0, "count": 3})
    assert st.players[0].mp == mp + 6


def test_p044_blocks_opponent_mp_gain_next_turn():
    # 次のターン中、相手はＭＰをふやせない(FAQ:スタートフェイズとエンドフェイズも含む)
    g = setup(("M-001",), ("M-001",))
    st = g.state
    st.players[0].slots[0].stack = ["M-076"]                                # バランシャ
    st.players[0].slots[0].partner = "P-044"
    submit(g, ability(0, st.players[0].slots[0], zone="partner"))
    assert "P-044" in st.players[0].discard
    while st.turn_player == 0:
        submit(g, {"type": "pass", "player": st.action_player})
    mp = st.players[1].mp
    submit(g, {"type": "flip_pages", "player": 1, "count": 2})
    assert st.players[1].mp == mp
    while st.turn_player == 1:
        if st.pending is not None:
            choose(g, st.pending.options[0]["value"])
            continue
        submit(g, {"type": "pass", "player": st.action_player})
    assert st.players[1].mp == mp                                           # 結束階段的強制翻頁也不增加


def test_p044_not_active_this_turn():
    g = setup(("M-076",), ("M-001", "E-009"))
    st = g.state
    st.players[0].slots[0].partner = "P-044"
    submit(g, ability(0, st.players[0].slots[0], zone="partner"))
    mp = st.players[0].mp
    from gash.engine.engine import gain_mp
    gain_mp(g, [], 1, 2, "test", by=1)
    assert st.players[1].mp == 12                                           # 這回合不受影響


# ---------------------------------------------------------------- P-050

def test_p050_steals_mp():
    # 相手のＭＰを2へらす。そうしたなら、へらした数と同じ数、自分のＭＰをふやす
    g = setup(("M-001",), ("M-001",))
    st = g.state
    st.players[0].slots[0].stack = ["M-082"]
    st.players[0].slots[0].partner = "P-050"
    st.players[1].mp = 1
    submit(g, ability(0, st.players[0].slots[0], zone="partner"))
    assert st.players[1].mp == 0 and st.players[0].mp == 11


# ---------------------------------------------------------------- M-078

def test_m078_partner_not_discarded_by_opponent_effect():
    # この魔物につけられたパートナーは、相手の効果では捨て札にならない
    from gash.engine.effects.tree import OpponentPartneredMamodo
    g = setup(("M-001",), ("M-078",))
    st = g.state
    st.players[1].slots[0].partner = "P-046"
    assert OpponentPartneredMamodo(discard=True).options(g, {"player": 0}) == []


# ---------------------------------------------------------------- M-082

def test_m082_forbids_protect_with_chosen_mamodo():
    # 相手の魔物1体を選ぶ。このターン中、相手は、その魔物で「かばう」ことができない
    from gash.engine.engine import _eligible_protectors
    g = setup(("M-082",), ("M-001",))
    st = g.state
    a = st.players[1].slots[0]
    b = add_slot(g, 1, "M-017")
    submit(g, ability(0, st.players[0].slots[0]))
    assert st.pending.kind == "pick_opponent_mamodo" and st.pending.player == 0
    choose(g, b.uid)
    assert st.players[0].mp == 8
    protectors = [s.uid for _, s in _eligible_protectors(g, {"kind": "book", "player": 1})]
    assert b.uid not in protectors and a.uid in protectors


# ---------------------------------------------------------------- M-083

def test_m083_stacks_on_nyarlat_and_plays_shion_from_any_page():
    # 自分の「ニャルラト」に重ねる。《絆のリボン》MPを1へらす→自分の魔本の好きなページから、パートナーカード「詞音」1枚を選び、場に出す
    from gash.engine.engine import play_block
    g = setup(("M-001",))
    st = g.state
    assert play_block(g, 0, "M-083") == "no_base"
    nyarlat = st.players[0].slots[0]
    nyarlat.stack = ["Ex-002", "M-083"]
    st.players[0].book[19] = "Ex-008"                                      # 第 20 頁(未翻開)
    submit(g, ability(0, nyarlat))
    assert st.players[0].mp == 9 and nyarlat.partner == "Ex-008"
    assert 20 in st.players[0].consumed_pages


def test_m083_needs_shion_in_book():
    g = setup(("M-001",))
    st = g.state
    st.players[0].slots[0].stack = ["Ex-002", "M-083"]
    assert code(g, ability(0, st.players[0].slots[0])) == "ability.condition"


# ---------------------------------------------------------------- P-046 / M-080

def test_p046_negates_event_and_discards_only_partner():
    # 《博士はなんでも知っている》このカードを捨て札にする→相手が直前に使ったイベントカード1つを無効にする
    g = setup(("M-001", "E-009"), ("M-001",))
    st = g.state
    kid = add_slot(g, 1, "M-078", partner="P-046")
    use(g)
    assert st.pending.kind == "jammer_negate" and st.pending.player == 1
    choose(g, "P-046")
    assert not any(m.source == "E-009" for m in st.modifiers)
    kid = st.slot_by_uid(1, kid.uid)                                        # 還原快照後重新取
    assert kid is not None and kid.partner is None and "P-046" in st.players[1].discard
    assert "M-078" not in st.players[1].discard


def test_m080_jammer_only_on_opponent_turn():
    # 《乱入》相手のバトルフェイズに、相手が直前に使ったイベントカード1つを無効にする
    g = setup(("M-001", "Ex-023"), ("M-001", "Ex-023"))
    st = g.state
    add_slot(g, 0, "M-080")
    add_slot(g, 1, "M-080")
    submit(g, {"type": "pass", "player": 0})
    use(g, player=1)                                                        # 玩家 0 的回合:不是玩家 1 的戰鬥階段
    if st.pending is not None and st.pending.kind == "pick_own_mamodo":
        choose(g, st.pending.options[0]["value"])
    assert st.pending is None or st.pending.kind != "jammer_negate"


def test_m080_jammer_on_opponent_battle_phase():
    g = setup(("M-001", "Ex-023"), ("M-001",))
    st = g.state
    bj = add_slot(g, 1, "M-080")
    use(g)
    if st.pending is not None and st.pending.kind == "pick_own_mamodo":
        choose(g, st.pending.options[0]["value"])
    assert st.pending.kind == "jammer_negate" and st.pending.player == 1
    choose(g, "M-080")
    assert not any(m.source == "Ex-023" for m in st.modifiers) and st.slot_by_uid(1, bj.uid) is None


def test_m080_battle_intrusion_negates_attack():
    # 《バトル乱入》このカードを捨て札にする→このバトルの、相手の攻撃1つを無効にする
    g = setup(("M-001", "S-001"), ("M-001",))
    st = g.state
    bj = add_slot(g, 1, "M-080")
    battle_in(g, 2)
    submit(g, {"type": "no_defense", "player": 1})
    submit(g, {"type": "pass", "player": 0})
    submit(g, ability(1, bj))
    assert st.battle.attack_negated and "M-080" in st.players[1].discard


def test_m080_battle_intrusion_not_outside_battle():
    g = setup(("M-001",), ("M-001",))
    st = g.state
    bj = add_slot(g, 0, "M-080")
    assert code(g, ability(0, bj)) == "ability.timing"


def test_m080_two_effects_counted_separately():
    # 2つの効果は別々:《バトル乱入》を使ったターンに出し直しても《乱入》は使える(atwiki 卡頁解說)
    from gash.engine.engine import _jammer_holder
    g = setup(("M-001",), ("M-001",))
    st = g.state
    st.players[1].used_abilities.add("mamodo:M-080")                        # 《バトル乱入》を使った
    add_slot(g, 1, "M-080")
    assert st.turn_player == 0 and st.battle is None                        # 玩家 1 的對手的戰鬥階段、非戰鬥中
    assert _jammer_holder(g, 1, "event") is not None


# ---------------------------------------------------------------- M-081

def test_m081_treated_as_zofis():
    from gash.engine.effects.primitives import family
    g = setup(("M-081",))
    assert family(g, g.state.players[0].slots[0]) == "ゾフィス"


def test_m081_locks_mamodo_effect_for_game_once():
    # 相手の魔物1体を選ぶ。このゲーム中、相手は、その魔物の「魔物の効果」を使えない。ゲーム中に1回だけ使える
    from gash.engine.engine import mamodo_effect_block, spell_block
    g = setup(("M-081",), ("M-001",))
    st = g.state
    target = st.players[1].slots[0]
    other = add_slot(g, 1, "M-017")
    submit(g, ability(0, st.players[0].slots[0]))
    choose(g, target.uid)
    assert mamodo_effect_block(g, 1, target) == "mamodo_locked"
    assert mamodo_effect_block(g, 1, other) is None and spell_block(g, 1, target) is None
    end_turn(g)
    end_turn(g)
    assert mamodo_effect_block(g, 1, target) == "mamodo_locked"            # このゲーム中
    assert code(g, ability(0, st.players[0].slots[0])) == "ability.per_game"   # ゲーム中に1回だけ


def test_m081_new_copy_not_locked():
    # FAQ A1:捨て札になり、新たに同じナンバーの魔物が場に出たとき、新たに出た魔物の効果は使えます
    from gash.engine.engine import mamodo_effect_block
    g = setup(("M-081",), ("M-001",))
    st = g.state
    target = st.players[1].slots[0]
    add_slot(g, 1, "M-017")
    submit(g, ability(0, st.players[0].slots[0]))
    choose(g, target.uid)
    st.players[1].slots.remove(target)
    fresh = add_slot(g, 1, "M-001")
    assert mamodo_effect_block(g, 1, fresh) is None


# ---------------------------------------------------------------- Ex-061

def _danny():
    g = setup(("M-039",), ("M-001",))
    st = g.state
    danny = st.players[0].slots[0]
    mamodo_attack(g, danny)
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    submit(g, {"type": "no_defense", "player": 1})
    pass_effects(g)
    finish_damage(g)
    assert code(g, {"type": "declare_attack", "player": 0, "mode": "mamodo", "slot_uid": danny.uid}) == "attack.used"
    return g, danny


def test_ex061_reuses_used_danny_effect_at_cost_zero():
    # 【スタンバイ】このターン中に１回、自分がこのターン中すでに使った「ダニー」の「魔物の効果」1つを、コスト0で使うことができる
    g, danny = _danny()
    st = g.state
    danny.partner = "Ex-061"
    submit(g, ability(0, danny, zone="partner"))
    submit(g, {"type": "pass", "player": 1})
    mp = st.players[0].mp
    mamodo_attack(g, danny)
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    assert st.battle is not None and st.players[0].mp == mp                  # 費用 0
    assert not any(sb.kind == "reuse_ability" for sb in st.standby)
    submit(g, {"type": "no_defense", "player": 1})
    pass_effects(g)
    finish_damage(g)
    assert code(g, {"type": "declare_attack", "player": 0, "mode": "mamodo", "slot_uid": danny.uid}) == "attack.used"


def test_ex061_standby_not_consumed_by_unused_effect():
    g = setup(("M-039",), ("M-001",))
    st = g.state
    danny = st.players[0].slots[0]
    danny.partner = "Ex-061"
    submit(g, ability(0, danny, zone="partner"))
    submit(g, {"type": "pass", "player": 1})
    mp = st.players[0].mp
    mamodo_attack(g, danny)                                                 # 第 1 次:照常付費
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    assert st.players[0].mp == mp - 1
    assert any(sb.kind == "reuse_ability" for sb in st.standby)


# ---------------------------------------------------------------- P-045

def _p045(user):
    """玩家 0 以 user 使用 S-026(指令,擲 1 次,非戰鬥);場上有 P-045 的ドンポッチョ。"""
    g = setup((user, "S-026"), ("M-001",))
    st = g.state
    don = st.players[0].slots[0] if user == "M-077" else add_slot(g, 0, "M-077")
    don.partner = "P-045"
    g.rng = Rng(TAILS)
    user_slot = st.players[0].slots[0]
    submit(g, {"type": "use_book_card", "player": 0, "page": 2, "slot_uid": user_slot.uid})
    return g


def test_p045_sets_heads_for_donpoccho_spell():
    # 自分が「ドンボッチョ」で使った術の効果で投げたコイン1個をオモテにする(FAQ:コマンドの術をドンポッチョが使うとき)
    g = _p045("M-077")
    st = g.state
    assert st.pending.kind == "coin_confirm"
    assert any(o.get("card") == "P-045" for o in st.pending.options)


def test_p045_not_for_other_mamodo_spell():
    g = _p045("M-001")
    st = g.state
    assert st.pending is None or not any(o.get("card") == "P-045" for o in st.pending.options)


# ---------------------------------------------------------------- 自我對戰

SELFPLAY_BOOKS = (
    ("M-039", "P-025", "Ex-055", "S-072", "M-072", "Ex-100", "M-082", "P-050", "Ex-061", "M-071", "S-008",
     "S-009", "M-078", "P-046", "E-009", "S-008", "M-080", "S-009", "M-081", "S-039", "E-046", "S-025",
     "S-008", "S-009", "S-039", "S-025", "S-008", "S-009", "E-030", "S-008", "S-009", "S-039"),
    ("M-001", "S-001", "M-076", "P-044", "S-002", "M-077", "P-045", "S-026", "S-025", "S-022", "M-012",
     "E-009", "M-002", "S-003", "M-003", "S-004", "Ex-002", "M-083", "Ex-008", "S-001", "S-002", "S-003",
     "E-030", "S-002", "S-003", "S-001", "S-002", "S-003", "S-025", "S-002", "S-003", "S-008"),
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
