"""攻防效果的宣告時確定(game-engine「戰鬥流程五步驟」、card-effects「攻防效果的宣告時確定」)。

規則頁「バトル ②防御 ※重要」:攻撃や防御の効果で対象を選ぶとき・コインを投げるときは宣言時。
效果文明寫其他時機(「ダメージをあたえたとき」「効果の使用の最後に」)時依效果文。
"""

from gash.engine.engine import submit
from tests.test_level2 import HEADS, TAILS, Rng, book, mk, to_battle
from tests.test_level3 import ability, add_slot, events_of, no_protect, pass_effects


def coins(events):
    return [e for e in events if e["type"] == "coin_flipped" and e.get("source") != "setup"]


def declare(g, page, slot=None):
    """玩家 0 宣告攻擊並由玩家 1 迎戰,回傳宣告(戰鬥開始)時的事件。"""
    cmd = {"type": "declare_attack", "player": 0, "page": page}
    if slot is not None:
        cmd["slot_uid"] = slot.uid
    submit(g, cmd)
    return submit(g, {"type": "battle_in_response", "player": 1, "allow": True})


def no_defense(g):
    submit(g, {"type": "no_defense", "player": 1})


# ---------------------------------------------------------------- 選對手魔物(S-058 / S-057)

def _s058(*opp_extra):
    g, _ = mk(book("M-051", "S-058"), book("M-001"))
    for n in opp_extra:
        add_slot(g, 1, n)
    g.state.players[0].mp = 10
    to_battle(g, 0)
    return g


def test_s058_target_chosen_at_declaration():
    g = _s058("M-002")
    st = g.state
    a, b = st.players[1].slots
    declare(g, 2)
    assert st.pending is not None and st.pending.kind == "injure_instead_target" and st.pending.player == 0
    assert st.battle.step == "defense"                                       # 防禦宣告之前
    submit(g, {"type": "choose", "player": 0, "value": b.uid})
    no_defense(g)
    pass_effects(g)
    no_protect(g)
    assert st.pending is None and b.injured and not a.injured                # 獲勝時不再詢問


def test_s058_target_gone_before_resolution():
    g = _s058("M-002")
    st = g.state
    a, b = st.players[1].slots
    pos1 = st.players[1].pos
    declare(g, 2)
    submit(g, {"type": "choose", "player": 0, "value": b.uid})
    st.players[1].slots.remove(b)                                            # 選定的魔物在結算前離場
    no_defense(g)
    pass_effects(g)
    assert st.pending is None and not a.injured and st.players[1].pos == pos1 and st.battle is None


def test_s057_standby_target_chosen_at_declaration():
    g, _ = mk(book("M-001", "S-057", "S-001"), book("M-001"))
    st = g.state
    add_slot(g, 1, "M-002")
    g.rng = Rng(HEADS)
    st.players[0].mp = 10
    to_battle(g, 0)
    gash = st.players[0].slots[0]
    submit(g, {"type": "use_book_card", "player": 0, "page": 2, "slot_uid": gash.uid})
    submit(g, {"type": "pass", "player": 1})
    declare(g, 3)
    assert st.pending is not None and st.pending.kind == "injure_instead_target"


# ---------------------------------------------------------------- 全部魔物(S-036 / S-101)

def test_s101_only_mamodo_present_at_declaration():
    g, _ = mk(book("M-033", "S-101"), book("M-001"))
    st = g.state
    st.players[0].mp = 10
    to_battle(g, 0)
    declare(g, 2)
    late = add_slot(g, 1, "M-002")                                          # 宣告後才出現的魔物
    no_defense(g)
    pass_effects(g)
    while st.pending is not None:
        kind = st.pending.kind
        submit(g, {"type": "choose", "player": 1, "value": 0 if kind == "damage_order" else None})
    assert st.players[1].slots[0].injured and not late.injured


# ---------------------------------------------------------------- 擲幣(S-069)

def test_s069_coin_at_declaration():
    g, _ = mk(book("M-038", "S-069"), book("M-001"))
    st = g.state
    g.rng = Rng(HEADS)                                                       # 之後再擲就會是反面
    st.players[0].mp = 10
    to_battle(g, 0)
    pos1 = st.players[1].pos
    events = declare(g, 2)
    assert [e["source"] for e in coins(events)] == ["S-069"]
    no_defense(g)
    pass_effects(g)
    no_protect(g)
    assert st.players[1].pos == pos1 + 2 * 1
    assert len(coins(g.events)) == 1


# ---------------------------------------------------------------- 二選一(S-070)

def test_s070_mode_and_target_chosen_at_declaration():
    g, _ = mk(book("M-038", "S-070"), book("M-001"))
    st = g.state
    a = st.players[1].slots[0]
    b = add_slot(g, 1, "M-002")
    st.players[0].mp = 10
    to_battle(g, 0)
    pos1 = st.players[1].pos
    declare(g, 2)
    assert st.pending.kind == "pick_effect" and st.pending.player == 0
    submit(g, {"type": "choose", "player": 0, "value": "mamodo"})
    assert st.pending.kind == "pick_opponent_mamodo"
    submit(g, {"type": "choose", "player": 0, "value": b.uid})
    assert st.battle.step == "defense"
    no_defense(g)
    pass_effects(g)
    no_protect(g)
    assert st.pending is None and b.injured and not a.injured and st.players[1].pos == pos1


# ---------------------------------------------------------------- S-021「効果の使用」の最後

def _s021(heads=(HEADS, TAILS), attacker_partner=None):
    g, _ = mk(book("M-001", "S-001"), book("M-013", "S-021"))
    st = g.state
    g.rng = Rng(*heads)
    if attacker_partner:
        st.players[0].slots[0].partner = attacker_partner
    st.players[0].mp, st.players[1].mp = 10, 10
    to_battle(g, 0)
    declare(g, 2)
    submit(g, {"type": "declare_defense", "player": 1, "page": 2})
    return g


def test_s021_negates_at_end_of_effects_step():
    g = _s021()
    st = g.state
    assert not st.battle.attack_negated                                      # 戰鬥中效果的時機期間仍有效
    pos1 = st.players[1].pos
    pass_effects(g)
    assert st.players[1].pos == pos1 and st.battle is None
    assert [e for e in g.events if e["type"] == "attack_negated" and e.get("source") == "S-021"]


def test_s021_no_negation_when_defense_negated():
    # 攻方以 P-017 使防禦無效:S-021 的無效也失效
    g = _s021(attacker_partner="P-017")
    st = g.state
    submit(g, ability(0, st.players[0].slots[0], zone="partner"))
    pass_effects(g)
    assert not [e for e in g.events if e["type"] == "attack_negated" and e.get("source") == "S-021"]


# ---------------------------------------------------------------- 效果文明寫時機:造成傷害時(回歸)

def test_s004_coin_when_damage_dealt():
    g, _ = mk(book("M-001", "S-004"), book("M-001"))
    st = g.state
    g.rng = Rng(TAILS)
    st.players[0].mp = 10
    to_battle(g, 0)
    events = declare(g, 2)
    assert coins(events) == []                                               # 宣告時不擲
    no_defense(g)
    pass_effects(g)
    no_protect(g)
    assert [e["source"] for e in coins(g.events)] == ["S-004"]


def test_s039_choice_when_damage_dealt():
    g, _ = mk(book("M-022", "S-039"), book("M-001"))
    st = g.state
    st.players[1].slots[0].partner = "P-001"
    add_slot(g, 1, "M-002", partner="P-002")
    st.players[0].mp = 10
    to_battle(g, 0)
    declare(g, 2)
    assert st.pending is None                                                # 宣告時不選


def test_npc_answers_declare_time_choices():
    # NPC 在宣告時的決策(選對手魔物、二選一)能送出被引擎接受的指令
    import random
    from gash import npc
    for spell, mamodo in (("S-058", "M-051"), ("S-070", "M-038")):
        g, _ = mk(book(mamodo, spell), book("M-001"))
        add_slot(g, 1, "M-002")
        g.state.players[0].mp = 10
        to_battle(g, 0)
        declare(g, 2)
        assert g.state.pending is not None and g.state.pending.player == 0
        ranked = npc.decide(g, 0, "normal", random.Random(0))
        cmd, _ = npc.submit_ranked(g, 0, ranked)
        assert cmd["type"] == "choose"
