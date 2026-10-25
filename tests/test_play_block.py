"""魔書中卡片的放出可否(battle-api「魔書中卡片的放出可否」):快照的 play_block / targets 與 play_card 指令一致。"""
import pytest

from gash.api.views import snapshot
from gash.engine.engine import IllegalCommand, submit
from tests.test_spell_user import book, give, mk, to_battle


def code(g, command):
    with pytest.raises(IllegalCommand) as e:
        submit(g, command)
    return e.value.code


def entry(g, viewer, page=2):
    return next(e for e in snapshot(g, viewer)["players"][0]["open_pages"] if e["page"] == page)


def play(page=2, **extra):
    return {"type": "play_card", "player": 0, "page": page, **extra}


def test_spell_only_mamodo_blocked():
    g = mk(book("M-045", "M-046"))
    to_battle(g)
    assert entry(g, 0)["play_block"] == "spell_only"
    assert code(g, play()) == "play.spell_only"


def test_field_full_blocked():
    g = mk(book("M-001", "M-004"))
    give(g, 0, "M-006")
    give(g, 0, "M-009")
    to_battle(g)
    assert entry(g, 0)["play_block"] == "field_full"
    assert code(g, play()) == "play.field_full"


def test_stack_without_base_blocked_until_base_present():
    g = mk(book("M-001", "M-007"))
    to_battle(g)
    assert entry(g, 0)["play_block"] == "no_base"
    assert code(g, play()) == "play.no_base"
    give(g, 0, "M-006")
    assert entry(g, 0)["play_block"] is None
    submit(g, play())
    assert g.state.players[0].slots[-1].stack == ["M-006", "M-007"]


def test_same_name_mamodo_blocked():
    g = mk(book("M-001", "M-002"))
    to_battle(g)
    assert entry(g, 0)["play_block"] == "same_name"
    assert code(g, play()) == "play.same_name"


def test_playable_mamodo_has_null_block():
    g = mk(book("M-001", "M-004"))
    to_battle(g)
    assert entry(g, 0)["play_block"] is None


def test_partner_targets_follow_treated_as_name():
    # M-047 疊在ガッシュ・ベル上(卡面 related_mamodo 是「金色のガッシュベル」),仍視為ガッシュ・ベル
    g = mk(book("M-001", "P-001"))
    gash = g.state.players[0].slots[0]
    gash.stack.append("M-047")
    to_battle(g)
    e = entry(g, 0)
    assert e["play_block"] is None and e["targets"] == [gash.uid]
    submit(g, play(slot_uid=gash.uid))
    assert gash.partner == "P-001"


def test_partner_blocks():
    g = mk(book("M-004", "P-001"))
    to_battle(g)
    e = entry(g, 0)
    assert e["play_block"] == "no_mamodo" and e["targets"] == []
    assert code(g, play()) == "play.no_mamodo"
    give(g, 0, "M-001", partner="P-010")
    e = entry(g, 0)
    assert e["play_block"] == "partner_exists" and e["targets"] == []
    assert code(g, play()) == "play.partner_exists"


def test_fields_only_for_owner():
    g = mk(book("M-045", "M-046"))
    give(g, 1, "M-038", partner="P-024")      # P-024:對手看得到翻開的頁
    to_battle(g)
    opp = entry(g, 1)
    assert opp.get("card") == "M-046"
    assert "play_block" not in opp and "targets" not in opp
    assert "play_block" not in entry(g, "spectator")
