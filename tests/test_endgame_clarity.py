"""終局的記錄與快照(game-engine「結束階段」、battle-api「強制翻頁落敗快照」)。

Run: python -m pytest tests/test_endgame_clarity.py -q
"""
from gash.api.views import snapshot
from gash.engine.engine import submit
from gash.engine.state import GAME_OVER
from tests.test_level2 import book, mk, to_battle


def _pass_out(g):
    """非戰鬥中雙方連續 pass,進入結束階段。"""
    batch = []
    batch += submit(g, {"type": "pass", "player": g.state.action_player})
    batch += submit(g, {"type": "pass", "player": g.state.action_player})
    return batch


def test_end_flip_on_last_page_loses_without_flipping():
    g, _ = mk(book("M-001"), book("M-001"))
    ps = g.state.players[0]
    ps.pos = 32
    to_battle(g, 0)
    ps.mp = 3
    events = _pass_out(g)
    assert g.state.phase == GAME_OVER
    assert g.state.winner == 1 and g.state.end_reason == "book_out"
    assert ps.mp == 3 and ps.pos == 32                       # 沒翻頁、沒加 MP
    assert not [e for e in events if e["type"] == "pages_flipped"]
    assert events[-1]["type"] == "game_ended"


def test_end_flip_with_page_left_flips_normally():
    g, _ = mk(book("M-001"), book("M-001"))
    ps = g.state.players[0]
    ps.pos = 30
    to_battle(g, 0)
    mp = ps.mp
    events = _pass_out(g)
    assert g.state.phase != GAME_OVER
    assert ps.pos == 32 and ps.mp == mp + 2
    assert [e for e in events if e["type"] == "pages_flipped" and e.get("forced")]


def _end_flip_loses(g):
    return {viewer: [snapshot(g, viewer)["players"][p]["end_flip_loses"] for p in (0, 1)]
            for viewer in (0, 1, "spectator")}


def test_snapshot_end_flip_loses_for_turn_player_on_last_page():
    g, _ = mk(book("M-001"), book("M-001"))
    g.state.players[0].pos = 32
    g.state.players[1].pos = 32
    to_battle(g, 0)
    assert _end_flip_loses(g) == {v: [True, False] for v in (0, 1, "spectator")}


def test_snapshot_end_flip_loses_false_with_page_left():
    g, _ = mk(book("M-001"), book("M-001"))
    g.state.players[0].pos = 30
    to_battle(g, 0)
    assert _end_flip_loses(g)[0] == [False, False]


def test_snapshot_end_flip_loses_false_with_skip_standby():
    g, _ = mk(book("M-030"), book("M-001"))
    ps = g.state.players[0]
    ps.pos = 32
    to_battle(g, 0)
    assert _end_flip_loses(g)[0] == [True, False]
    submit(g, {"type": "use_field_ability", "player": 0, "zone": "mamodo", "slot_uid": ps.slots[0].uid})
    assert _end_flip_loses(g) == {v: [False, False] for v in (0, 1, "spectator")}


def test_snapshot_end_flip_loses_false_after_game_over():
    g, _ = mk(book("M-001"), book("M-001"))
    g.state.players[0].pos = 32
    to_battle(g, 0)
    _pass_out(g)
    assert g.state.phase == GAME_OVER
    assert _end_flip_loses(g)[0] == [False, False]
