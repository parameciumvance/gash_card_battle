"""既有常駐效果受「使えない」(card-effects「既有常駐效果受『使えない』」、game-engine「專用規則不是效果」
「常駐效果的『使えない』判斷時點」)。官方規則書第 42 頁:「このカードが場にある→」的效果會被「使えない」擋下。

魔物卡的效果以 E-025(全體)與 E-024(這隻)兩種限制驗證;搭檔卡以「パートナーの効果を使えない」驗證。
"""
import pytest

from gash.api.views import snapshot
from gash.engine.engine import (
    _detach_top, _discard_slot, event_cost, reveals_open_pages, slot_power, spell_use_limit, submit,
)
from gash.engine.effects.primitives import turn_back_pages
from gash.engine.state import MAMODO_LOCKED, NO_MAMODO_EFFECTS, NO_PARTNER_EFFECTS, NO_SPELLS
from tests.test_level2 import _run_attack_to_damage, book, mk, to_battle
from tests.test_level3 import _attack_m053, add_slot, attack, declare, pass_effects, restrict

HOW = ["all", "slot"]   # E-025「魔物の効果を使えない」/ E-024「その魔物の『魔物の効果』…を使えない」


def block(g, player, slot, how):
    if how == "all":
        return restrict(g, player, NO_MAMODO_EFFECTS, source="E-025")
    return restrict(g, player, MAMODO_LOCKED, slot=slot.uid, source="E-024")


def block_partner(g, player):
    return restrict(g, player, NO_PARTNER_EFFECTS, source="E-008")


def unblock(g, m):
    g.state.modifiers.remove(m)


def open_entry(g, viewer, player, page):
    return next(e for e in snapshot(g, viewer)["players"][player]["open_pages"] if e["page"] == page)


# ---------------------------------------------------------------- 時點型(發動當下判斷,不補發)

@pytest.mark.parametrize("how", HOW)
def test_m002_no_mp_at_start_phase_while_blocked(how):
    g, _ = mk(book("M-002"), book("M-001"))
    ps = g.state.players[0]
    assert ps.mp == 2
    block(g, 0, ps.slots[0], how)
    to_battle(g, 0)
    assert ps.mp == 2


def test_m006_no_spell_restriction_when_played_while_blocked():
    g, _ = mk(book("M-001", "M-006"), book("M-001"))
    to_battle(g, 0)
    block(g, 0, None, "all")
    submit(g, {"type": "play_card", "player": 0, "page": 2})
    assert not any(m.flag == NO_SPELLS and m.target_player == 1 for m in g.state.modifiers)


@pytest.mark.parametrize("how", HOW)
def test_m007_no_page_turn_when_stacked_while_blocked_and_not_later(how):
    g, _ = mk(book("M-006", "M-007"), book("M-001"))
    st = g.state
    to_battle(g, 0)
    m = block(g, 0, st.players[0].slots[0], how)
    pos1 = st.players[1].pos
    submit(g, {"type": "play_card", "player": 0, "page": 2})
    assert st.players[0].slots[0].stack == ["M-006", "M-007"]
    assert st.players[1].pos == pos1
    unblock(g, m)                                                            # 限制解除後不補翻
    submit(g, {"type": "pass", "player": st.action_player})
    assert st.players[1].pos == pos1


@pytest.mark.parametrize("how", HOW)
def test_m009_no_mp_when_discarded_while_blocked(how):
    g, _ = mk(book("M-001"), book("M-001"))
    kolulu = add_slot(g, 0, "M-009")
    to_battle(g, 0)
    block(g, 0, kolulu, how)
    mp = g.state.players[0].mp
    _discard_slot(g, [], 0, kolulu, reason="test")
    assert "M-009" in g.state.players[0].discard and g.state.players[0].mp == mp


def test_m025_no_effects_when_played_while_blocked():
    g, _ = mk(book("M-001", "M-025"), book("M-001"))
    st = g.state
    st.players[0].discard.append("M-024")
    to_battle(g, 0)
    block(g, 0, None, "all")
    mp = st.players[0].mp
    submit(g, {"type": "play_card", "player": 0, "page": 2})
    assert st.pending is None and st.players[0].mp == mp


@pytest.mark.parametrize("how", HOW)
def test_m028_no_page_turn_when_armor_detached_while_blocked(how):
    g, _ = mk(book("M-028"), book("M-001"))
    st = g.state
    bartolo = st.players[0].slots[0]
    bartolo.stack.append("M-027")
    to_battle(g, 0)
    block(g, 0, bartolo, how)
    pos1 = st.players[1].pos
    _detach_top(g, [], 0, bartolo, reason="test")
    assert bartolo.stack == ["M-028"] and st.players[1].pos == pos1


def test_p013_no_page_turn_while_blocked():
    g, _ = mk(book("M-001"), book("M-001"))
    st = g.state
    add_slot(g, 0, "M-022", partner="P-013")
    victim = add_slot(g, 1, "M-004")
    to_battle(g, 0)
    block_partner(g, 0)
    pos1 = st.players[1].pos
    _discard_slot(g, [], 1, victim, reason="test")
    assert st.players[1].pos == pos1


def test_p019_no_mp_loss_while_blocked():
    g, _ = mk(book("M-001"), book("M-001"))
    st = g.state
    st.players[0].slots[0].partner = "P-019"
    to_battle(g, 0)
    block_partner(g, 0)
    st.players[1].mp, st.players[1].pos = 10, 6
    assert turn_back_pages(g, [], 1, 1, "E-005") == 1
    assert st.players[1].mp == 10


def test_p030_no_mp_while_blocked():
    g, _ = mk(book("M-044"), book("M-001", "E-024"))
    st = g.state
    st.players[0].slots[0].partner = "P-030"
    st.players[0].mp, st.players[1].mp = 0, 0
    to_battle(g, 0)
    block_partner(g, 0)
    submit(g, {"type": "pass", "player": 0})
    submit(g, {"type": "use_book_card", "player": 1, "page": 2})
    if st.pending is not None:
        submit(g, {"type": "choose", "player": 1, "value": st.pending.options[0]["value"]})
    assert st.players[0].mp == 0


# ---------------------------------------------------------------- 持續型(每次查詢時判斷)

@pytest.mark.parametrize("how", HOW)
def test_m003_bonus_off_while_blocked_and_back_after(how):
    g, _ = mk(book("M-003"), book("M-001"))
    gash = g.state.players[0].slots[0]
    gash.injured = True
    assert slot_power(g, 0, gash) == 5000
    m = block(g, 0, gash, how)
    assert slot_power(g, 0, gash) == 4000
    unblock(g, m)
    assert slot_power(g, 0, gash) == 5000


@pytest.mark.parametrize("how", HOW)
def test_m004_bonus_off_while_blocked(how):
    g, _ = mk(book("M-004"), book("M-001"))
    reycom = g.state.players[0].slots[0]
    reycom.partner = "P-002"
    block(g, 0, reycom, how)
    assert slot_power(g, 0, reycom) == 3000


@pytest.mark.parametrize("how", HOW)
def test_m014_bonus_off_for_all_while_blocked(how):
    g, _ = mk(book("M-014"), book("M-001"))
    tia = g.state.players[0].slots[0]
    other = add_slot(g, 0, "M-012")
    block(g, 0, tia, how)
    assert slot_power(g, 0, tia) == 2000 and slot_power(g, 0, other) == 1000


def test_m014_other_mamodo_locked_keeps_bonus():
    # 只限定別隻魔物的限制不影響 M-014 的效果
    g, _ = mk(book("M-014"), book("M-001"))
    tia = g.state.players[0].slots[0]
    other = add_slot(g, 0, "M-012")
    block(g, 0, other, "slot")
    assert slot_power(g, 0, tia) == 3000 and slot_power(g, 0, other) == 2000


@pytest.mark.parametrize("number,spell", [("M-023", "S-014"), ("M-036", "S-006")])
def test_attr_spell_compat_off_while_blocked(number, spell):
    g, _ = mk(book(number, spell), book("M-001"))
    st = g.state
    st.players[0].mp = 10
    to_battle(g, 0)
    uid = st.players[0].slots[0].uid
    assert [u["slot_uid"] for u in open_entry(g, 0, 0, 2)["users"]] == [uid]
    block(g, 0, None, "all")
    assert open_entry(g, 0, 0, 2)["users"] == []


def test_m024_bilaitz_once_while_both_blocked_twice_when_one_locked():
    g, _ = mk(book("M-024"), book("M-001"))
    first = g.state.players[0].slots[0]
    add_slot(g, 0, "M-024")
    bilaitz = g.db["S-042"]
    assert spell_use_limit(g, 0, bilaitz) == 2
    m = block(g, 0, first, "slot")
    assert spell_use_limit(g, 0, bilaitz) == 2                                # 另一隻的效果可用,仍算 2 隻
    unblock(g, m)
    block(g, 0, first, "all")
    assert spell_use_limit(g, 0, bilaitz) == 1


@pytest.mark.parametrize("how", HOW)
def test_m031_takes_damage_while_blocked(how):
    g, _ = mk(book("M-001", "S-001"), book("M-031"))
    st = g.state
    st.players[0].mp = 10
    to_battle(g, 0)
    kyclops = st.players[1].slots[0]
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    _run_attack_to_damage(g, 0, 1)
    block(g, 1, kyclops, how)
    submit(g, {"type": "choose", "player": 1, "value": kyclops.uid})
    assert kyclops.injured


@pytest.mark.parametrize("how", HOW)
def test_m051_takes_damage_while_blocked(how):
    g, _ = mk(book("M-051", "S-058"), book("M-051"))
    st = g.state
    st.players[0].mp = 10
    to_battle(g, 0)
    block(g, 1, st.players[1].slots[0], how)
    attack(g, 2)
    pass_effects(g)                                                          # S-058:負傷代替,唯一對象 M-051
    assert st.players[1].slots[0].injured


@pytest.mark.parametrize("how", HOW)
def test_m053_takes_one_damage_attack_while_blocked(how):
    g, brago = _attack_m053("S-001")
    block(g, 1, brago, how)
    submit(g, {"type": "choose", "player": 1, "value": brago.uid})
    assert brago.injured


@pytest.mark.parametrize("how", HOW)
def test_m040_cost_not_increased_while_blocked(how):
    g, _ = mk(book("M-040"), book("M-001", "E-024"))
    st = g.state
    assert event_cost(g, 1, g.db["E-024"]) == g.db["E-024"].cost + 1
    block(g, 0, st.players[0].slots[0], how)
    assert event_cost(g, 1, g.db["E-024"]) == g.db["E-024"].cost
    assert open_entry(g, 1, 1, 2)["cost"] == g.db["E-024"].cost


def test_p024_pages_hidden_while_blocked():
    g, _ = mk(book("M-038"), book("M-001"))
    st = g.state
    st.players[0].slots[0].partner = "P-024"
    to_battle(g, 0)
    assert reveals_open_pages(g, 0, 1)
    block_partner(g, 0)
    assert not reveals_open_pages(g, 0, 1)
    assert all("card" not in e for e in snapshot(g, 0)["players"][1]["open_pages"])


# ---------------------------------------------------------------- 專用規則與「使えないときにも使える」不受影響

def test_m029_zakeru_rule_not_blocked():
    g, _ = mk(book("M-029", "S-001"), book("M-001"))
    st = g.state
    st.players[0].mp = 10
    to_battle(g, 0)
    block(g, 0, None, "all")
    declare(g, 0, 2, st.players[0].slots[0])
    assert st.battle_in is not None


def test_m047_scheduled_detach_rule_not_blocked():
    g, _ = mk(book("M-001", "M-047"), book("M-001"))
    st = g.state
    to_battle(g, 0)
    block(g, 0, st.players[0].slots[0], "slot")
    submit(g, {"type": "play_card", "player": 0, "page": 2})
    assert st.players[0].slots[0].top == "M-047"
    assert any(m.kind == "scheduled_detach" and m.source == "M-047" for m in st.modifiers)


def test_m038_spell_usable_under_mamodo_and_spell_restrictions():
    g, _ = mk(book("M-038", "S-070"), book("M-001"))
    st = g.state
    st.players[0].mp = 10
    to_battle(g, 0)
    block(g, 0, None, "all")
    restrict(g, 0, NO_SPELLS, source="E-002")
    declare(g, 0, 2, st.players[0].slots[0])
    assert st.battle_in is not None
