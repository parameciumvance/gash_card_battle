"""場上魔物的欄位(game-engine「場上魔物的欄位」、battle-api「魔物槽欄位快照」)。"""
from gash.api.views import snapshot
from gash.engine.effects.primitives import play_mamodo_from_book
from gash.engine.engine import _discard_slot, submit
from gash.engine.state import MamodoSlot
from tests.test_spell_user import book, mk, to_battle


def cols(g, p=0):
    return {s.top: s.column for s in g.state.players[p].slots}


def three(g):
    """玩家 0 依序放出第 2、3 頁的魔物:第 1 頁 M-001 在第 0 欄。"""
    to_battle(g)
    submit(g, {"type": "play_card", "player": 0, "page": 2})
    submit(g, {"type": "pass", "player": 1})
    submit(g, {"type": "play_card", "player": 0, "page": 3})
    submit(g, {"type": "pass", "player": 1})


def test_columns_assigned_left_to_right():
    g = mk(book("M-001", "M-004", "M-008"))
    three(g)
    assert cols(g) == {"M-001": 0, "M-004": 1, "M-008": 2}


def test_left_leaves_others_stay_and_new_fills_left():
    g = mk(book("M-001", "M-004", "M-008", "M-011"))
    three(g)
    ps = g.state.players[0]
    _discard_slot(g, [], 0, ps.slots[0], reason="damage")                 # 第 0 欄送墓
    assert cols(g) == {"M-004": 1, "M-008": 2}
    ps.pos = 4                                                              # 翻到第 4–5 頁
    submit(g, {"type": "play_card", "player": 0, "page": 4})                # 新魔物補最左空欄
    assert cols(g)["M-011"] == 0


def test_stack_keeps_column():
    g = mk(book("M-001", "M-006", "M-007"))
    to_battle(g)
    submit(g, {"type": "play_card", "player": 0, "page": 2})                # M-006 在第 1 欄
    submit(g, {"type": "pass", "player": 1})
    submit(g, {"type": "play_card", "player": 0, "page": 3})                # M-007 疊在 M-006 上
    assert cols(g) == {"M-001": 0, "M-007": 1}


def test_effect_placement_fills_leftmost_gap():
    g = mk(book("M-001", "M-004", "M-008", "S-029", "M-011"))
    three(g)
    ps = g.state.players[0]
    _discard_slot(g, [], 0, next(s for s in ps.slots if s.top == "M-004"), reason="damage")
    play_mamodo_from_book(g, [], 0, 5)
    assert cols(g) == {"M-001": 0, "M-011": 1, "M-008": 2}


def test_snapshot_has_column_for_all_viewers_and_fallback():
    g = mk(book("M-001", "M-004", "M-008"))
    three(g)
    ps = g.state.players[0]
    _discard_slot(g, [], 0, ps.slots[0], reason="damage")
    for viewer in (0, 1, "spectator"):
        assert sorted(s["column"] for s in snapshot(g, viewer)["players"][0]["slots"]) == [1, 2]
    ps.slots.append(MamodoSlot(uid=g.state.next_uid(), stack=["M-011"]))   # 直接建立、沒有欄位
    views = {s["top"]: s["column"] for s in snapshot(g, 0)["players"][0]["slots"]}
    assert views["M-011"] == 0
