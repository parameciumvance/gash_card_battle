"""效果的使用可否(battle-api「效果的使用可否快照」)。

Run: python -m pytest tests/test_disabled_reasons.py -q
"""
import pytest

from gash.api.views import snapshot
from gash.engine.effects.primitives import add_modifier
from gash.engine.engine import IllegalCommand, submit
from gash.engine.state import DUR_TURN, MAMODO_LOCKED, NO_MAMODO_EFFECTS, NO_PARTNER_EFFECTS
from tests.test_level2 import book, mk, to_battle


def block(g, viewer=0, player=0, field="ability_block"):
    return snapshot(g, viewer)["players"][player]["slots"][0].get(field, "absent")


def restrict(g, p, flag, slot=None):
    add_modifier(g, [], kind="restriction", source="E-024" if slot else "E-025", owner=1 - p,
                 duration=DUR_TURN, target_player=p, target_slot=slot.uid if slot else None, flag=flag)


def test_battle_only_effect_outside_battle():
    g, _ = mk(book("M-001"), book("M-001"))
    to_battle(g, 0)
    assert block(g) == "timing_battle"


def test_only_owner_sees_block():
    g, _ = mk(book("M-042"), book("M-001"))
    to_battle(g, 0)
    assert block(g, viewer=0) is None
    assert block(g, viewer="all") is None
    assert block(g, viewer=1) == "absent"
    assert block(g, viewer="spectator") == "absent"


def test_usable_even_when_not_my_action():
    g, _ = mk(book("M-001"), book("M-042"))
    to_battle(g, 0)
    g.state.players[1].mp = 5
    assert g.state.action_player == 0
    assert block(g, viewer=1, player=1) is None                # 時機與行動權無關


def test_mp_and_used():
    g, _ = mk(book("M-042"), book("M-001"))
    to_battle(g, 0)
    ps = g.state.players[0]
    ps.mp = 0
    assert block(g) == "mp"
    with pytest.raises(IllegalCommand) as e:
        submit(g, {"type": "use_field_ability", "player": 0, "zone": "mamodo", "slot_uid": ps.slots[0].uid})
    assert e.value.code == "ability.mp"
    ps.mp = 5
    ps.used_abilities.add("mamodo:M-042")
    assert block(g) == "used"


def test_own_turn_only():
    g, _ = mk(book("M-001"), book("M-018"))
    to_battle(g, 0)
    g.state.players[1].mp = 5
    assert block(g, viewer=1, player=1) == "own_turn"


def test_condition_and_per_game():
    g, _ = mk(book("M-030"), book("M-001"))
    ps = g.state.players[0]
    ps.pos = 30
    to_battle(g, 0)
    assert block(g) == "condition"
    ps.pos = 32
    assert block(g) is None
    ps.used_per_game.add("M-030")
    assert block(g) == "per_game"


@pytest.mark.parametrize("flag,code", [(NO_MAMODO_EFFECTS, "mamodo_restricted"), (MAMODO_LOCKED, "mamodo_locked")])
def test_mamodo_effect_blocked(flag, code):
    g, _ = mk(book("M-042"), book("M-001"))
    to_battle(g, 0)
    slot = g.state.players[0].slots[0]
    restrict(g, 0, flag, slot if flag == MAMODO_LOCKED else None)
    assert block(g) == code
    with pytest.raises(IllegalCommand) as e:
        submit(g, {"type": "use_field_ability", "player": 0, "zone": "mamodo", "slot_uid": slot.uid})
    assert e.value.code == f"ability.{code}"


def test_partner_block():
    g, _ = mk(book("M-001"), book("M-001"))
    to_battle(g, 0)
    g.state.players[0].slots[0].partner = "P-001"
    assert block(g, field="partner_ability_block") is None
    restrict(g, 0, NO_PARTNER_EFFECTS)
    assert block(g, field="partner_ability_block") == "partner_restricted"
    assert block(g, viewer=1, field="partner_ability_block") == "absent"


def test_no_ability_is_null():
    g, _ = mk(book("M-002"), book("M-001"))
    to_battle(g, 0)
    assert block(g) is None
    assert block(g, field="partner_ability_block") is None


def test_borrowed_block():
    g, _ = mk(book("M-001"), book("M-001"))
    to_battle(g, 0)
    assert snapshot(g, 0)["players"][0]["borrowed_block"] is None   # 沒有借用
    add_modifier(g, [], kind="borrow_partner", source="E-010", owner=0, duration=DUR_TURN,
                 data={"card": "P-001"})
    g.state.players[0].mp = 5
    assert snapshot(g, 0)["players"][0]["borrowed_block"] is None
    assert "borrowed_block" not in snapshot(g, 1)["players"][0]
    restrict(g, 0, NO_PARTNER_EFFECTS)
    assert snapshot(g, 0)["players"][0]["borrowed_block"] == "partner_restricted"
    with pytest.raises(IllegalCommand) as e:
        submit(g, {"type": "use_borrowed_effect", "player": 0})
    assert e.value.code == "ability.partner_restricted"
