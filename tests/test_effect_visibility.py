"""效果資訊醒目顯示的引擎與快照部分(battle-api「魔力明細快照」「費用明細快照」「傷害被防止事件的來源」
「失效中的常駐效果快照」「一次性時點的效果被擋下事件」)。"""
from gash.api.views import snapshot
from gash.engine.effects.primitives import add_modifier, schedule_standby
from gash.engine.engine import submit
from gash.engine.state import DUR_TURN
from tests.test_level2 import _run_attack_to_damage, book, mk, to_battle
from tests.test_level3 import _attack_m053, add_slot, attack, pass_effects


def events_of(events, type_):
    return [e for e in events if e["type"] == type_]


def slot_view(g, viewer, player, uid):
    return next(s for s in snapshot(g, viewer)["players"][player]["slots"] if s["uid"] == uid)


def page_entry(g, viewer, player, page):
    return next(e for e in snapshot(g, viewer)["players"][player]["open_pages"] if e["page"] == page)


def item(kind, source, amount):
    return {"kind": kind, "source": source, "amount": amount}


def run_effects(g):
    """雙方在戰鬥中效果的時機 pass,收集事件,直到出現決策或戰鬥結束。"""
    st, out = g.state, []
    while st.battle is not None and st.pending is None:
        out += submit(g, {"type": "pass", "player": st.battle.data["effect_turn"]})
    return out


# ---------------------------------------------------------------- damage_prevented 的來源

def test_immunity_source_m031():
    g, _ = mk(book("M-001", "S-001"), book("M-031"))
    st = g.state
    st.players[0].mp = 10
    to_battle(g, 0)
    kyclops = st.players[1].slots[0]
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    _run_attack_to_damage(g, 0, 1)
    events = submit(g, {"type": "choose", "player": 1, "value": kyclops.uid})
    assert events_of(events, "damage_prevented")[0]["source"] == "M-031"


def test_immunity_source_m053():
    g, brago = _attack_m053("S-001")
    events = submit(g, {"type": "choose", "player": 1, "value": brago.uid})
    assert events_of(events, "damage_prevented")[0]["source"] == "M-053"


def test_no_damage_modifier_source():
    # M-013 / M-015 類:戰鬥中這隻魔物不受傷害
    g, _ = mk(book("M-001", "S-001"), book("M-001"))
    st = g.state
    st.players[0].mp = 10
    to_battle(g, 0)
    target = st.players[1].slots[0]
    add_modifier(g, [], kind="no_damage", source="M-013", owner=1, duration=DUR_TURN,
                 target_player=1, target_slot=target.uid)
    attack(g, 2)
    pass_effects(g)
    events = submit(g, {"type": "choose", "player": 1, "value": target.uid})
    assert events_of(events, "damage_prevented")[0]["source"] == "M-013"


def test_full_immune_source():
    # S-037 類:自己的魔書與所有魔物本回合不受傷害
    g, _ = mk(book("M-001", "S-001"), book("M-001"))
    st = g.state
    st.players[0].mp = 10
    to_battle(g, 0)
    add_modifier(g, [], kind="full_immune", source="S-037", owner=1, duration=DUR_TURN, target_player=1)
    attack(g, 2)
    events = run_effects(g)
    if st.pending is not None:
        events += submit(g, {"type": "choose", "player": 1, "value": None})
    assert events_of(events, "damage_prevented")[0]["source"] == "S-037"


def test_guard_immune_source_s079():
    g, _ = mk(book("M-001", "S-005"), book("M-042", "S-079"))
    st = g.state
    wonrei = st.players[1].slots[0]
    st.players[0].mp, st.players[1].mp = 10, 10
    to_battle(g, 0)
    attack(g, 2, defend_page=2)
    pass_effects(g)
    events = submit(g, {"type": "choose", "player": 1, "value": wonrei.uid})
    prevented = events_of(events, "damage_prevented")[0]
    assert prevented["reason"] == "guard" and prevented["source"] == "S-079"


# ---------------------------------------------------------------- 魔力明細

def test_power_breakdown_static_bonus():
    g, _ = mk(book("M-003"), book("M-001"))
    gash = g.state.players[0].slots[0]
    gash.injured = True
    for viewer in (0, 1, "spectator"):
        view = slot_view(g, viewer, 0, gash.uid)
        assert view["power"] == 5000
        assert view["power_breakdown"] == [item("mamodo", "M-003", 4000), item("static", "M-003", 1000)]


def test_power_breakdown_modifier_and_power_set():
    g, _ = mk(book("M-001"), book("M-001"))
    gash = g.state.players[0].slots[0]
    add_modifier(g, [], kind="power", source="E-001", owner=0, duration=DUR_TURN,
                 target_player=0, target_slot=gash.uid, amount=3000)
    view = slot_view(g, 0, 0, gash.uid)
    assert view["power_breakdown"] == [item("mamodo", "M-001", 4000), item("modifier", "E-001", 3000)]
    add_modifier(g, [], kind="power_set", source="P-011", owner=1, duration=DUR_TURN,
                 target_player=0, target_slot=gash.uid, data={"value": 0})
    view = slot_view(g, 0, 0, gash.uid)
    assert view["power"] == 0 and sum(i["amount"] for i in view["power_breakdown"]) == 0
    assert view["power_breakdown"][-1] == item("power_set", "P-011", -7000)


# ---------------------------------------------------------------- 費用明細

def test_event_cost_breakdown_m040():
    g, _ = mk(book("M-040"), book("M-001", "E-001"))
    to_battle(g, 0)
    entry = page_entry(g, 1, 1, 2)
    assert entry["cost"] == 1
    assert entry["cost_breakdown"] == [item("card", "E-001", 0), item("opponent_event", "M-040", 1)]


def test_spell_cost_breakdown_plain():
    g, _ = mk(book("M-001", "S-002"), book("M-001"))
    to_battle(g, 0)
    assert page_entry(g, 0, 0, 2)["cost_breakdown"] == [item("card", "S-002", 2)]


def test_spell_cost_breakdown_last_page():
    b = book("M-001")
    b[31] = "S-002"
    g, _ = mk(b, book("M-001"))
    to_battle(g, 0)
    g.state.players[0].pos = 32
    entry = page_entry(g, 0, 0, 32)
    assert entry["cost"] == 0
    assert entry["cost_breakdown"] == [item("card", "S-002", 2), item("last_page", None, -2)]


def test_spell_cost_breakdown_base_zero_s088():
    g, _ = mk(book("M-001", "S-002"), book("M-001"))
    to_battle(g, 0)
    schedule_standby(g, [], kind="spell_base_cost_zero", source="S-088", owner=0)
    assert page_entry(g, 0, 0, 2)["cost_breakdown"] == [item("card", "S-002", 2), item("base_zero", "S-088", -2)]


def test_spell_cost_breakdown_p005_and_m008():
    g, _ = mk(book("M-008", "S-014"), book("M-001"))
    to_battle(g, 0)
    schedule_standby(g, [], kind="spell_bonus", source="M-008", owner=0,
                     data={"mamodo": "スギナ", "power_delta": -1000, "cost_delta": -1, "optional": True})
    entry = page_entry(g, 0, 0, 2)
    assert entry["cost"] == 1
    assert entry["cost_breakdown"] == [item("card", "S-014", 2), item("cost_bonus", "M-008", -1)]
    add_modifier(g, [], kind="spell_cost_zero", source="P-005", owner=0, duration=DUR_TURN,
                 target_player=0, data={"mamodo": "スギナ"})
    entry = page_entry(g, 0, 0, 2)
    assert entry["cost"] == 0                                                 # 本来 0,再 -1 不低於 0
    assert entry["cost_breakdown"] == [item("card", "S-014", 2), item("base_zero", "P-005", -2),
                                       item("cost_bonus", "M-008", -1), item("cost_floor", None, 1)]


def test_cost_breakdown_hidden_with_card():
    g, _ = mk(book("M-001", "S-002"), book("M-001"))
    to_battle(g, 0)
    assert "cost_breakdown" not in page_entry(g, 1, 0, 2)


# ---------------------------------------------------------------- 失效中的常駐效果(blocked_effects)

def _restrict(g, target, flag, *, slot=None, source):
    from tests.test_level3 import restrict
    return restrict(g, target, flag, slot=slot, source=source)


def test_blocked_effects_mamodo_all_and_partner():
    from gash.engine.state import NO_MAMODO_EFFECTS, NO_PARTNER_EFFECTS
    g, _ = mk(book("M-031"), book("M-001"))
    st = g.state
    kyclops = st.players[0].slots[0]
    baago = add_slot(g, 0, "M-044", partner="P-030")
    assert slot_view(g, 1, 0, kyclops.uid)["blocked_effects"] == []
    _restrict(g, 0, NO_MAMODO_EFFECTS, source="E-025")
    _restrict(g, 0, NO_PARTNER_EFFECTS, source="E-008")
    for viewer in (0, 1, "spectator"):
        assert slot_view(g, viewer, 0, kyclops.uid)["blocked_effects"] == [{"card": "M-031", "by": ["E-025"]}]
        assert slot_view(g, viewer, 0, baago.uid)["blocked_effects"] == [{"card": "P-030", "by": ["E-008"]}]


def test_blocked_effects_single_lock_and_excluded_cards():
    from gash.engine.state import MAMODO_LOCKED, NO_MAMODO_EFFECTS
    g, _ = mk(book("M-031"), book("M-001"))
    st = g.state
    kyclops = st.players[0].slots[0]
    gash = add_slot(g, 0, "M-003")
    _restrict(g, 0, MAMODO_LOCKED, slot=kyclops.uid, source="E-024")
    assert slot_view(g, 0, 0, kyclops.uid)["blocked_effects"] == [{"card": "M-031", "by": ["E-024"]}]
    assert slot_view(g, 0, 0, gash.uid)["blocked_effects"] == []
    gofure = add_slot(g, 0, "M-006")
    rops = add_slot(g, 1, "M-038")
    _restrict(g, 0, NO_MAMODO_EFFECTS, source="E-025")
    _restrict(g, 1, NO_MAMODO_EFFECTS, source="E-025")
    assert slot_view(g, 0, 0, kyclops.uid)["blocked_effects"] == [{"card": "M-031", "by": ["E-024", "E-025"]}]
    assert slot_view(g, 0, 0, gofure.uid)["blocked_effects"] == []          # 出場時的效果已解決
    assert slot_view(g, 0, 1, rops.uid)["blocked_effects"] == []            # M-038「使えないときにも使える」


def test_block_sources_include_p031_family():
    from gash.engine.engine import effect_block_sources
    g, _ = mk(book("M-045"), book("M-001"))
    uma = g.state.players[0].slots[0]
    add_slot(g, 1, "M-001", partner="P-031")
    assert effect_block_sources(g, 0, uma, "M-045") == ["P-031"]


# ---------------------------------------------------------------- 一次性時點被擋下(effect_blocked)

def _blocked(events):
    return [{k: e[k] for k in ("card", "by", "when")} for e in events_of(events, "effect_blocked")]


def test_effect_blocked_on_play_and_start_phase():
    from gash.engine.state import NO_MAMODO_EFFECTS
    g, _ = mk(book("M-002", "M-007"), book("M-001"))
    st = g.state
    _restrict(g, 0, NO_MAMODO_EFFECTS, source="E-025")
    events = submit(g, {"type": "flip_pages", "player": 0, "count": 0})
    assert _blocked(events) == [{"card": "M-002", "by": ["E-025"], "when": "start_phase"}]
    gofure = add_slot(g, 0, "M-006")
    events = submit(g, {"type": "play_card", "player": 0, "page": 2})
    assert gofure.top == "M-007"
    assert _blocked(events) == [{"card": "M-007", "by": ["E-025"], "when": "play"}]


def test_effect_blocked_on_discard():
    from gash.engine.engine import _discard_slot
    from gash.engine.state import MAMODO_LOCKED
    g, _ = mk(book("M-001"), book("M-001"))
    kolulu = add_slot(g, 0, "M-009")
    to_battle(g, 0)
    _restrict(g, 0, MAMODO_LOCKED, slot=kolulu.uid, source="E-024")
    batch = []
    _discard_slot(g, batch, 0, kolulu, reason="test")
    assert _blocked(batch) == [{"card": "M-009", "by": ["E-024"], "when": "discard"}]


def test_effect_blocked_on_immunity_only_when_it_would_apply():
    from gash.engine.state import NO_MAMODO_EFFECTS
    for spell, expect in (("S-001", True), ("S-029", False)):              # 合計 6000 會免疫 / 7000 不會
        g, _ = mk(book("M-001", spell), book("M-031"))
        st = g.state
        st.players[0].mp = 10
        to_battle(g, 0)
        kyclops = st.players[1].slots[0]
        submit(g, {"type": "declare_attack", "player": 0, "page": 2})
        submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
        _run_attack_to_damage(g, 0, 1)
        _restrict(g, 1, NO_MAMODO_EFFECTS, source="E-025")
        events = submit(g, {"type": "choose", "player": 1, "value": kyclops.uid})
        assert kyclops.injured
        assert _blocked(events) == ([{"card": "M-031", "by": ["E-025"], "when": "damage"}] if expect else [])


def test_trigger_blocked_emits_nothing():
    from gash.engine.engine import _discard_slot
    from gash.engine.state import NO_PARTNER_EFFECTS
    g, _ = mk(book("M-001"), book("M-001"))
    add_slot(g, 0, "M-022", partner="P-013")
    victim = add_slot(g, 1, "M-004")
    to_battle(g, 0)
    _restrict(g, 0, NO_PARTNER_EFFECTS, source="E-008")
    batch = []
    _discard_slot(g, batch, 1, victim, reason="test")
    assert _blocked(batch) == [] and not events_of(batch, "pages_turned")
