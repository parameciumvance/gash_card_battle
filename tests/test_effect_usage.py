"""效果的使用次數、ジャマー對魔物效果攻擊 / 防禦、E-038 的時機(effect-usage-fixes)。

規則頁「１つの効果は、１ターンに１回だけ使うことができます」;官方規則書第 42 頁「無効にする」包括取消
戰鬥中使用的攻擊與防禦;規則頁「エンドフェイズ」效果解決在強制翻頁之前。
"""
from gash.api.views import snapshot
from gash.engine.engine import submit
from tests.test_level2 import book, mk, to_battle
from tests.test_level3 import (
    ability, add_slot, attack, battle_in, choose, code, end_turn, finish_damage, no_defense_pass, pass_effects,
    use_event,
)


def _armor(p0_book=("M-028",), p1=("M-001",)):
    g, _ = mk(book(*p0_book), book(*p1))
    st = g.state
    armor = st.players[0].slots[0]
    armor.stack.append("M-027")
    st.players[0].mp = st.players[1].mp = 10
    to_battle(g, 0)
    return g, armor


def mamodo_attack(g, slot):
    submit(g, {"type": "declare_attack", "player": 0, "mode": "mamodo", "slot_uid": slot.uid})
    return submit(g, {"type": "battle_in_response", "player": 1, "allow": True})


# ---------------------------------------------------------------- 每回合 1 次

def test_mamodo_attack_once_per_turn():
    g, armor = _armor()
    mamodo_attack(g, armor)
    no_defense_pass(g)
    finish_damage(g)
    assert g.state.battle is None and g.state.action_player == 0
    assert code(g, {"type": "declare_attack", "player": 0, "mode": "mamodo", "slot_uid": armor.uid}) == "attack.used"


def test_mamodo_attack_available_next_own_turn():
    g, armor = _armor()
    mamodo_attack(g, armor)
    no_defense_pass(g)
    finish_damage(g)
    end_turn(g)
    end_turn(g)
    mamodo_attack(g, armor)
    assert g.state.battle is not None


def test_m039_attack_and_defense_counted_separately():
    g, _ = mk(book("M-039"), book("M-001", "S-001", "S-001", "S-001", "S-001"))
    st = g.state
    danny = st.players[0].slots[0]
    st.players[0].mp = st.players[1].mp = 10
    to_battle(g, 0)
    mamodo_attack(g, danny)                                                    # 《格闘》
    no_defense_pass(g)
    finish_damage(g)
    assert code(g, {"type": "declare_attack", "player": 0, "mode": "mamodo", "slot_uid": danny.uid}) == "attack.used"
    end_turn(g)                                                                # 對手的回合:《ガード》仍可用
    battle_in(g, st.players[1].pos, player=1)
    submit(g, {"type": "declare_defense", "player": 0, "mode": "mamodo", "slot_uid": danny.uid})
    assert st.battle.data.get("defense_fixed_power") == 6500


def test_mamodo_defense_once_per_turn():
    g, _ = mk(book("M-001", "S-001", "S-002"), book("M-039"))
    st = g.state
    danny = st.players[1].slots[0]
    st.players[0].mp = st.players[1].mp = 10
    to_battle(g, 0)
    battle_in(g, 2)
    submit(g, {"type": "declare_defense", "player": 1, "mode": "mamodo", "slot_uid": danny.uid})
    pass_effects(g)
    finish_damage(g)
    battle_in(g, 3)
    assert code(g, {"type": "declare_defense", "player": 1, "mode": "mamodo",
                    "slot_uid": danny.uid}) == "defense.used"


# ---------------------------------------------------------------- M-026 無效魔物效果攻擊 / 防禦

def test_m026_negates_mamodo_attack():
    g, armor = _armor(p1=("M-026",))
    st = g.state
    pos1 = st.players[1].pos
    mamodo_attack(g, armor)
    assert st.pending.kind == "jammer_negate" and st.pending.player == 1 and st.pending.source == "M-026"
    events = choose(g, True)
    assert st.battle.attack_negated and st.players[1].mp == 8 and st.players[0].mp == 9
    assert [e for e in events if e["type"] == "effect_negated"][0]["negated"] == "M-027"
    no_defense_pass(g)
    finish_damage(g)
    assert st.players[1].pos == pos1                                           # 攻擊無效:沒有傷害
    assert code(g, {"type": "declare_attack", "player": 0, "mode": "mamodo", "slot_uid": armor.uid}) == "attack.used"


def test_m026_skip_keeps_mamodo_attack():
    g, armor = _armor(p1=("M-026",))
    st = g.state
    pos1 = st.players[1].pos
    mamodo_attack(g, armor)
    choose(g, None)
    assert not st.battle.attack_negated and st.battle.step == "defense"
    no_defense_pass(g)
    finish_damage(g)
    assert st.players[1].pos == pos1 + 2 * 2


def test_m026_chain_restores_mamodo_attack():
    g, armor = _armor(p1=("M-026",))
    st = g.state
    add_slot(g, 0, "M-026")
    pos1 = st.players[1].pos
    mamodo_attack(g, armor)
    choose(g, True)
    assert st.pending.kind == "jammer_negate" and st.pending.player == 0
    choose(g, True)
    assert not st.battle.attack_negated
    no_defense_pass(g)
    finish_damage(g)
    assert st.players[1].pos == pos1 + 2 * 2


def test_m026_negates_mamodo_defense():
    g, _ = mk(book("M-026", "S-001"), book("M-039"))
    st = g.state
    gash = add_slot(g, 0, "M-001")
    st.players[0].mp = st.players[1].mp = 10
    to_battle(g, 0)
    battle_in(g, 2, gash)
    danny = st.players[1].slots[0]
    submit(g, {"type": "declare_defense", "player": 1, "mode": "mamodo", "slot_uid": danny.uid})
    assert st.pending.kind == "jammer_negate" and st.pending.player == 0
    choose(g, True)
    assert st.battle.defense_negated and st.battle.step == "effects"
    pass_effects(g)
    show = [e for e in g.events if e["type"] == "showdown"][-1]
    assert show["defender_total"] == 0 and show["winner"] == "attacker"


# ---------------------------------------------------------------- E-038 的時機

def test_e038_mp_before_forced_flip():
    g, _ = mk(book("M-001", "E-038"), book("M-001"))
    st = g.state
    st.players[0].mp = 5
    to_battle(g, 0)
    use_event(g)
    mp = st.players[0].mp
    submit(g, {"type": "pass", "player": 1})
    events = submit(g, {"type": "pass", "player": 0})
    kinds = [e["type"] for e in events if e["type"] in ("mp_changed", "pages_flipped")]
    assert kinds[:2] == ["mp_changed", "pages_flipped"]                        # MP +4 在強制翻頁之前
    assert st.players[0].mp == mp + 4 + 2


def test_e038_ordered_with_other_end_phase_effects():
    g, _ = mk(book("M-001", "E-029", "E-038"), book("M-001"))
    st = g.state
    st.players[0].mp = 20
    add_slot(g, 1, "M-004")
    to_battle(g, 0)
    use_event(g, 2)
    submit(g, {"type": "pass", "player": 1})
    use_event(g, 3)
    st.players[0].book[2] = "E-042"
    submit(g, {"type": "pass", "player": 1})
    use_event(g, 3)
    while st.pending is not None and st.pending.kind == "pick_mamodo_to_keep":
        choose(g, st.pending.options[0]["value"])
    submit(g, {"type": "pass", "player": 1})
    submit(g, {"type": "pass", "player": 0})
    assert st.pending.kind == "end_phase_order"
    assert {o["card"] for o in st.pending.options} == {"E-038", "E-042"}


# ---------------------------------------------------------------- 快照的已使用旗標

def test_snapshot_marks_used_effects():
    g, _ = mk(book("M-042"), book("M-001"))
    st = g.state
    st.players[0].mp = 5
    to_battle(g, 0)
    slot = st.players[0].slots[0]
    view = lambda: next(s for s in snapshot(g, 1)["players"][0]["slots"] if s["uid"] == slot.uid)
    assert view()["ability_used"] is False
    submit(g, ability(0, slot))
    assert view()["ability_used"] == "turn"


def test_snapshot_marks_mamodo_attack_used():
    g, armor = _armor()
    view = lambda: next(s for s in snapshot(g, 0)["players"][0]["slots"] if s["uid"] == armor.uid)
    assert view()["mamodo_attack_used"] is False
    mamodo_attack(g, armor)
    assert view()["mamodo_attack_used"] == "turn"


def test_snapshot_marks_per_game_used():
    g, _ = mk(book("M-011"), book("M-001"))
    st = g.state
    to_battle(g, 0)
    slot = st.players[0].slots[0]
    submit(g, ability(0, slot))
    while st.pending is not None:
        choose(g, None if st.pending.kind == "end_book_review" else st.pending.options[0]["value"])
    end_turn(g)
    end_turn(g)
    view = next(s for s in snapshot(g, 0)["players"][0]["slots"] if s["uid"] == slot.uid)
    assert view["ability_used"] == "game"
