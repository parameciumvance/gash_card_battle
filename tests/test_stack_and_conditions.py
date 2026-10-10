"""疊放繼承負傷、選不到對象的非戰鬥戰術不能使用、快照的 condition_ok
(card-effects「疊放魔物(變身後)」「選不到對象的非戰鬥戰術不能使用」、battle-api「魔書中卡片的使用條件」)。"""
import pytest

from gash.api.views import snapshot
from gash.engine.engine import IllegalCommand, submit
from tests.test_spell_user import book, give, mk, to_battle


def code(g, command):
    with pytest.raises(IllegalCommand) as e:
        submit(g, command)
    return e.value.code


def page_of(g, p, number):
    ps = g.state.players[p]
    return next(pg for pg in range(1, 33) if ps.card_at(pg) == number and pg not in ps.consumed_pages)


# ---------------------------------------------------------------- 疊放繼承負傷

@pytest.mark.parametrize("injured", [True, False])
def test_stack_from_open_page_keeps_injury(injured):
    g = mk(book("M-006", "M-007"))
    base = g.state.players[0].slots[0]
    base.injured = injured
    to_battle(g)
    submit(g, {"type": "play_card", "player": 0, "page": 2})
    assert base.stack == ["M-006", "M-007"] and base.injured is injured


def test_stack_from_book_by_e012_keeps_injury():
    g = mk(book("M-006", "E-012", "S-029", "S-029", "S-029", "S-029", "S-029", "S-029", "M-007"))
    base = g.state.players[0].slots[0]
    base.injured = True
    g.state.players[0].mp = 10
    to_battle(g)
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    assert base.stack == ["M-006", "M-007"] and base.injured is True


def test_stack_by_s048_keeps_injury():
    g = mk(book("M-028", "S-048", "M-027"))
    base = g.state.players[0].slots[0]
    base.injured = True
    g.state.players[0].mp = 5
    to_battle(g)
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    assert base.stack == ["M-028", "M-027"] and base.injured is True


# ---------------------------------------------------------------- S-048 的使用條件

def test_s048_rejected_without_armor_in_book():
    g = mk(book("M-028", "S-048"))
    g.state.players[0].mp = 5
    to_battle(g)
    assert code(g, {"type": "use_book_card", "player": 0, "page": 2}) == "spell.condition"
    assert g.state.players[0].mp == 5
    assert "S-048" not in g.state.players[0].used_nonbattle_spells


def test_s048_rejected_without_base_on_field():
    # 場上只有 M-027(バルトロ 家族,能使用 S-048),沒有 M-028:選不到疊放的對象
    g = mk(book("M-027", "S-048", "M-027"))
    g.state.players[0].mp = 5
    to_battle(g)
    assert code(g, {"type": "use_book_card", "player": 0, "page": 2}) == "spell.condition"
    assert g.state.players[0].mp == 5


# ---------------------------------------------------------------- S-043 的使用條件與分裂

def robnos(field, book_pages, mp=10):
    """field:場上魔物卡號(第一隻為魔書第 1 頁);book_pages:魔書第 3 頁起的卡;第 2 頁為 S-043。"""
    g = mk(book(field[0], "S-043", *book_pages))
    for top in field[1:]:
        give(g, 0, top)
    g.state.players[0].mp = mp
    to_battle(g)
    return g


def test_s043_rejected_when_no_mode_possible():
    g = robnos(["M-025"], ["M-024"])                                        # 魔書只有 1 張 M-024
    assert code(g, {"type": "use_book_card", "player": 0, "page": 2}) == "spell.condition"
    assert g.state.players[0].mp == 10


def test_s043_split_needs_field_space():
    g = robnos(["M-025", "M-001", "M-002"], ["M-024", "M-024"])             # 棄掉 M-025 後剩 2 隻,放不下 2 隻
    assert code(g, {"type": "use_book_card", "player": 0, "page": 2}) == "spell.condition"


def test_s043_split_player_chooses_two_pages():
    g = robnos(["M-025"], ["M-024", "M-024", "M-024"])                      # 第 3、4、5 頁
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    p = g.state.pending
    assert p.kind == "pick_mamodo_in_own_book" and p.player == 0
    assert sorted(o["value"] for o in p.options) == [3, 4, 5]
    with pytest.raises(IllegalCommand) as e:
        submit(g, {"type": "choose", "player": 0, "value": 9})
    assert e.value.code == "choose.invalid" and g.state.pending is not None
    submit(g, {"type": "choose", "player": 0, "value": 5})
    assert sorted(o["value"] for o in g.state.pending.options) == [3, 4]
    submit(g, {"type": "choose", "player": 0, "value": 3})
    ps = g.state.players[0]
    assert g.state.pending is None
    assert [s.top for s in ps.slots] == ["M-024", "M-024"] and "M-025" in ps.discard
    assert 4 not in ps.consumed_pages                                         # 未選的那張留在魔書


def test_s043_full_field_lists_fuse_only():
    # 場上 M-024 ×2 + M-025:分裂後放不下 2 隻,只列合體(場上最多 3 隻,兩種模式不會同時可行)
    g = robnos(["M-024", "M-024"], ["M-025", "M-024", "M-024"])
    give(g, 0, "M-025")
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})          # 唯一模式「合體」與唯一的 M-025 都自動選擇
    ps = g.state.players[0]
    assert g.state.pending is None
    assert [s.top for s in ps.slots].count("M-024") == 0 and ps.discard.count("M-024") == 2
    assert 4 not in ps.consumed_pages and 5 not in ps.consumed_pages      # 沒有執行分裂:魔書的 M-024 還在


def test_s043_fuse_only_when_book_has_complete():
    g = robnos(["M-024", "M-024"], ["S-029"])                               # 魔書沒有 M-025
    assert code(g, {"type": "use_book_card", "player": 0, "page": 2}) == "spell.condition"


# ---------------------------------------------------------------- 快照的 condition_ok

def _entry(g, viewer, number):
    return next(e for e in snapshot(g, viewer)["players"][0]["open_pages"] if e.get("card") == number
                or (viewer != 0 and e["page"] == 2))


def test_snapshot_condition_ok():
    g = mk(book("M-028", "S-048"))
    to_battle(g)
    assert _entry(g, 0, "S-048")["condition_ok"] is False
    g2 = mk(book("M-028", "S-048", "M-027"))
    to_battle(g2)
    assert _entry(g2, 0, "S-048")["condition_ok"] is True
    g3 = mk(book("M-001", "E-021"))
    to_battle(g3)
    assert _entry(g3, 0, "E-021")["condition_ok"] is False                   # 場上只有 1 隻
    give(g3, 0, "M-004")
    assert _entry(g3, 0, "E-021")["condition_ok"] is True
    assert "condition_ok" not in _entry(g3, 1, None)
