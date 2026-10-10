"""戰術的使用魔物與搭檔卡的裝備對象(game-engine「非戰鬥戰術的使用魔物」「搭檔卡的裝備對象」、
battle-api「戰術頁的可使用魔物」)。"""
import dataclasses

import pytest

from gash.api.views import snapshot
from gash.engine.cards import card_db
from gash.engine.effects.primitives import add_modifier
from gash.engine.engine import IllegalCommand, new_game, submit
from gash.engine.state import DUR_TURN, MAMODO_LOCKED, MamodoSlot
from gash.npc.candidates import candidates

DB = card_db()


def book(*pages):
    b = list(pages)
    while len(b) < 32:
        b.append("S-029")
    return b[:32]


def mk(book0, book1=None, db=None):
    book1 = book1 or book("M-001")
    g = new_game(book0, seed=0, db=db or DB, decks=(list(book0), list(book1)))
    g.state.turn_player = 0
    return g


def give(g, p, number, partner=None):
    s = MamodoSlot(uid=g.state.next_uid(), stack=[number], partner=partner)
    g.state.players[p].slots.append(s)
    return s


def lock(g, p, slot):
    add_modifier(g, [], kind="restriction", source="E-024", owner=1 - p, duration=DUR_TURN,
                 target_player=p, target_slot=slot.uid, flag=MAMODO_LOCKED)


def to_battle(g):
    submit(g, {"type": "flip_pages", "player": 0, "count": 0})


def code(g, command):
    with pytest.raises(IllegalCommand) as e:
        submit(g, command)
    return e.value.code


# ---------------------------------------------------------------- 非戰鬥戰術的使用魔物

def test_nonbattle_spell_paid_by_chosen_user():
    # 指令戰術 S-026 的費用暫改為 2;P-005 讓スギナ使用的戰術費用為 0 → 兩隻使用時費用不同
    db = dict(DB)
    db["S-026"] = dataclasses.replace(DB["S-026"], cost=2)
    for chosen, paid in (("gash", 2), ("sugina", 0)):
        g = mk(book("M-001", "S-026"), db=db)
        gash = g.state.players[0].slots[0]
        sugina = give(g, 0, "M-008")
        add_modifier(g, [], kind="spell_cost_zero", source="P-005", owner=0, duration=DUR_TURN,
                     target_player=0, data={"mamodo": "スギナ"})
        g.state.players[0].mp = 5
        to_battle(g)
        user = gash if chosen == "gash" else sugina
        submit(g, {"type": "use_book_card", "player": 0, "page": 2, "slot_uid": user.uid})
        assert g.state.players[0].mp == 5 - paid


def test_nonbattle_spell_user_must_be_able():
    g = mk(book("M-023", "S-041"))
    gash = give(g, 0, "M-001")
    g.state.players[0].mp = 5
    to_battle(g)
    assert code(g, {"type": "use_book_card", "player": 0, "page": 2, "slot_uid": gash.uid}) == "spell.no_mamodo"


def test_nonbattle_spell_locked_user_rejected():
    # E-024「その魔物の…術を使えない」:非戰鬥戰術也不能由被封鎖的魔物使用
    g = mk(book("M-023", "S-041"))
    pokkerio = g.state.players[0].slots[0]
    g.state.players[0].mp = 5
    to_battle(g)
    lock(g, 0, pokkerio)
    assert code(g, {"type": "use_book_card", "player": 0, "page": 2, "slot_uid": pokkerio.uid}) == "spell.mamodo_locked"
    assert code(g, {"type": "use_book_card", "player": 0, "page": 2}) == "spell.mamodo_locked"
    assert g.state.players[0].mp == 5


def test_nonbattle_spell_without_user_skips_locked():
    g = mk(book("M-023", "S-041"))
    first = g.state.players[0].slots[0]
    give(g, 0, "M-023")
    g.state.players[0].mp = 5
    to_battle(g)
    lock(g, 0, first)
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})          # 由未被封鎖的另一隻使用
    assert "S-041" in g.state.players[0].used_nonbattle_spells


# ---------------------------------------------------------------- 快照的可使用魔物

def _page(snap, player, page):
    return next(e for e in snap["players"][player]["open_pages"] if e["page"] == page)


def test_snapshot_users_follow_engine_compat():
    g = mk(book("M-001", "S-001", "S-005"))
    gash = g.state.players[0].slots[0]
    zeon = give(g, 0, "M-029")
    to_battle(g)
    lock(g, 0, zeon)
    snap = snapshot(g, 0)
    zakeru = _page(snap, 0, 2)["users"]
    assert [u["slot_uid"] for u in zakeru] == [gash.uid, zeon.uid]
    assert all(isinstance(u["cost"], int) for u in zakeru)
    assert [u["locked"] for u in zakeru] == [False, True]
    assert [u["slot_uid"] for u in _page(snap, 0, 3)["users"]] == [gash.uid]   # 「バオウ・ザケルガ」≠「ザケル」
    for viewer in (1, "spectator"):
        other = snapshot(g, viewer)
        assert all("users" not in e for e in other["players"][0]["open_pages"])
        assert "any_page_spells" not in other["players"][0]


# ---------------------------------------------------------------- 搭檔卡的裝備對象

def test_partner_attached_to_chosen_mamodo():
    g = mk(book("M-024", "P-015"))
    first = g.state.players[0].slots[0]
    second = give(g, 0, "M-024")
    to_battle(g)
    submit(g, {"type": "play_card", "player": 0, "page": 2, "slot_uid": second.uid})
    assert second.partner == "P-015" and first.partner is None


def test_partner_goes_to_first_free_mamodo():
    g = mk(book("M-024", "P-015"))
    first = g.state.players[0].slots[0]
    first.partner = "P-001"                                                  # 已有搭檔(佔位)
    second = give(g, 0, "M-024")
    to_battle(g)
    submit(g, {"type": "play_card", "player": 0, "page": 2})
    assert second.partner == "P-015"


def test_partner_explicit_target_rejections():
    g = mk(book("M-024", "P-015"))
    first = g.state.players[0].slots[0]
    first.partner = "P-001"
    gash = give(g, 0, "M-001")
    to_battle(g)
    assert code(g, {"type": "play_card", "player": 0, "page": 2, "slot_uid": first.uid}) == "play.partner_exists"
    assert code(g, {"type": "play_card", "player": 0, "page": 2, "slot_uid": gash.uid}) == "play.no_mamodo"


def test_npc_candidates_cover_each_partner_target():
    g = mk(book("M-024", "P-015"))
    first = g.state.players[0].slots[0]
    second = give(g, 0, "M-024")
    to_battle(g)
    plays = [c for c in candidates(g, 0) if c["type"] == "play_card" and c["page"] == 2]
    assert {c.get("slot_uid") for c in plays} == {first.uid, second.uid}


# ---------------------------------------------------------------- P-015 任意頁戰術

def test_any_page_spells_listed_while_standby_active():
    pages = ["M-024", "P-015"] + ["S-029"] * 17 + ["S-042"]                  # 第 20 頁:ビライツ
    g = mk(book(*pages))
    first = g.state.players[0].slots[0]
    second = give(g, 0, "M-024")
    g.state.players[0].mp = 10
    to_battle(g)
    assert "any_page_spells" not in snapshot(g, 0)["players"][0] or not snapshot(g, 0)["players"][0]["any_page_spells"]
    submit(g, {"type": "play_card", "player": 0, "page": 2, "slot_uid": first.uid})
    submit(g, {"type": "pass", "player": 1})
    submit(g, {"type": "use_field_ability", "player": 0, "zone": "partner", "slot_uid": first.uid})
    listed = snapshot(g, 0)["players"][0]["any_page_spells"]
    assert [e["page"] for e in listed] == [20] and listed[0]["card"] == "S-042"
    assert [u["slot_uid"] for u in listed[0]["users"]] == [first.uid, second.uid]
    submit(g, {"type": "pass", "player": 1})
    submit(g, {"type": "declare_attack", "player": 0, "page": 20, "slot_uid": second.uid})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})     # 戰鬥開始時消耗待命
    assert g.state.battle.attack_slot == second.uid                            # 以指定的分身體使用
    assert not snapshot(g, 0)["players"][0]["any_page_spells"]                # 待命用掉後不再列出
