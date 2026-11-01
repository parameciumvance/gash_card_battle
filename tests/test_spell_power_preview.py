"""戰術的預估合計魔力(battle-api「戰術的預估合計魔力快照」)。

Run: python -m pytest tests/test_spell_power_preview.py -q
"""
from gash.api.views import snapshot
from gash.engine.engine import side_breakdown, submit
from tests.test_level2 import book, mk, to_battle


def users(g, viewer, player, page):
    entry = next(e for e in snapshot(g, viewer)["players"][player]["open_pages"] if e["page"] == page)
    return entry.get("users")


def test_attack_spell_preview_matches_actual_battle():
    g, _ = mk(book("M-001", "S-004", "S-025"), book("M-001"))
    to_battle(g, 0)
    [u] = users(g, 0, 0, 2)                                         # S-004:ガッシュ・ベル的攻擊戰術(+2000)
    assert u["power"] == 6000
    assert [(i["kind"], i["source"], i["amount"]) for i in u["power_breakdown"]] == [
        ("mamodo", "M-001", 4000), ("spell", "S-004", 2000)]
    submit(g, {"type": "declare_attack", "player": 0, "page": 2, "slot_uid": u["slot_uid"]})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    assert side_breakdown(g, g.state.battle, "attack")[0] == u["power"]


def test_preview_includes_static_bonus():
    g, _ = mk(book("M-004", "S-006"), book("M-001"))
    g.state.players[0].slots[0].partner = "P-002"                   # M-004:有搭檔時魔力 +1000
    to_battle(g, 0)
    [u] = users(g, 0, 0, 2)
    assert u["power"] == 3000 + 1000 + 2000


def test_defense_spell_and_ad_on_opponents_turn():
    g, _ = mk(book("M-001"), book("M-001", "S-001", "S-025"))
    to_battle(g, 0)
    [ad] = users(g, 1, 1, 2)                                        # S-001(AD):非回合玩家以防禦計算
    assert ad["power"] == 6000
    assert [i["kind"] for i in ad["power_breakdown"]] == ["mamodo", "spell"]
    [d] = users(g, 1, 1, 3)                                         # S-025(コマンド的防禦戰術)
    assert "power" in d


def test_nonbattle_spell_has_no_preview():
    g, _ = mk(book("M-001", "S-026"), book("M-001"))
    to_battle(g, 0)
    assert all("power" not in u for u in users(g, 0, 0, 2))


def test_opponent_and_spectator_have_no_preview():
    g, _ = mk(book("M-001", "S-004"), book("M-001"))
    to_battle(g, 0)
    assert users(g, 1, 0, 2) is None
    assert users(g, "spectator", 0, 2) is None
    assert users(g, "all", 0, 2)[0]["power"] == 6000
