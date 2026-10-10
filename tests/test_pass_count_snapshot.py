"""快照的連續 pass 次數(battle-api「連續 pass 次數快照」)。"""
from gash.api.views import snapshot
from gash.engine.engine import submit
from tests.test_spell_user import book, mk, to_battle

VIEWERS = (0, 1, "spectator")


def passes(g):
    return {snapshot(g, v)["consecutive_passes"] for v in VIEWERS}


def test_pass_counts_for_all_viewers():
    g = mk(book("M-001"))
    to_battle(g)
    assert passes(g) == {0}
    submit(g, {"type": "pass", "player": 0})
    assert passes(g) == {1}


def test_action_resets_count():
    g = mk(book("M-001"), book("M-001", "M-004"))
    to_battle(g)
    submit(g, {"type": "pass", "player": 0})
    submit(g, {"type": "play_card", "player": 1, "page": 2})
    assert passes(g) == {0}


def test_new_turn_resets_count():
    g = mk(book("M-001"))
    to_battle(g)
    submit(g, {"type": "pass", "player": 0})
    submit(g, {"type": "pass", "player": 1})
    assert g.state.turn_player == 1 and passes(g) == {0}


def test_battle_effect_pass_not_counted():
    g = mk(book("M-001", "S-001"))
    g.state.players[0].mp = 5
    to_battle(g)
    gash = g.state.players[0].slots[0]
    submit(g, {"type": "declare_attack", "player": 0, "page": 2, "slot_uid": gash.uid})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    submit(g, {"type": "no_defense", "player": 1})
    assert g.state.battle.step == "effects"
    turn = g.state.battle.data["effect_turn"]
    submit(g, {"type": "pass", "player": turn})
    assert g.state.battle is not None and passes(g) == {0}
