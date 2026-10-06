"""決策選項標示位置(game-engine「中途決策(pending choice)」)。

目標為卡片的選項帶 zone / player 與定位欄位(slot / page / index),value 不變。
"""
import random

from gash import npc
from gash.engine.awaiting import awaited_player
from gash.engine.effects import tree
from gash.engine.engine import submit
from gash.engine.state import GAME_OVER, MamodoSlot
from tests.test_level2 import book, mk, slot_uid, to_battle
from tests.test_npc import deck


def card_options(pending):
    return [o for o in pending.options if "card" in o]


def test_same_partner_on_two_pages_marks_each_page():
    # M-021 搜窪塚泳太(P-011):第 4 頁與第 10 頁各一張 → 兩個選項各自標頁碼
    b0 = book("M-021", "S-029", "S-029", "P-011", "S-029", "S-029", "S-029", "S-029", "S-029", "P-011")
    g, _ = mk(b0, book("M-001"))
    g.state.players[0].mp = 5
    to_battle(g, 0)
    submit(g, {"type": "use_field_ability", "player": 0, "zone": "mamodo",
               "slot_uid": slot_uid(g, 0, "M-021")})
    pending = g.state.pending
    assert pending is not None
    assert [(o["zone"], o["player"], o["page"], o["value"], o["card"]) for o in pending.options] == \
        [("book", 0, 4, 4, "P-011"), ("book", 0, 10, 10, "P-011")]


def _s036_to_damage(g):
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    submit(g, {"type": "no_defense", "player": 1})
    submit(g, {"type": "pass", "player": 0})
    submit(g, {"type": "pass", "player": 1})


def test_damage_order_and_protect_mark_slots():
    g, _ = mk(book("M-005", "S-036"), book("M-001"))
    g.state.players[0].mp = 15
    opp = g.state.players[1]
    opp.slots.append(MamodoSlot(uid=g.state.next_uid(), stack=["M-001"]))
    to_battle(g, 0)
    _s036_to_damage(g)
    seen = set()
    while g.state.pending is not None and g.state.pending.kind in ("damage_order", "protect"):
        pending = g.state.pending
        seen.add(pending.kind)
        if pending.kind == "damage_order":
            for o in pending.options:
                item = o["item"]
                if item["kind"] == "slot":
                    assert (o["zone"], o["player"], o["slot"]) == ("slot", item["player"], item["slot_uid"])
                else:
                    assert "zone" not in o                       # 魔本項維持按鈕
            submit(g, {"type": "choose", "player": 1, "value": 0})
        else:
            uids = {s.uid for s in opp.slots}
            for o in card_options(pending):
                assert (o["zone"], o["player"]) == ("slot", 1)
                assert o["slot"] == o["value"] and o["slot"] in uids
            assert [o for o in pending.options if "card" not in o] == [{"value": None, "label": "no_protect"}]
            submit(g, {"type": "choose", "player": 1, "value": None})
    assert seen == {"damage_order", "protect"}


def test_discard_options_mark_index():
    g, _ = mk(book("M-021"), book("M-001"))
    ps = g.state.players[0]
    ps.discard.extend(["S-029", "P-011"])
    opts = tree.PlayablePartnerInDiscard().options(g, {"player": 0})
    assert [(o["zone"], o["player"], o["index"], o["value"], o["card"]) for o in opts] == \
        [("discard", 0, 1, 1, "P-011")]
    assert opts[0]["slot_uid"] == ps.slots[0].uid                 # 既有的附加欄位保留


def _check_locations(g, found):
    pending = g.state.pending
    if pending is None:
        return
    for o in pending.options:
        if "label" in o or ("item" in o and o["item"]["kind"] != "slot"):
            continue
        found.add((pending.kind, o.get("zone")))
        player = g.state.players[o["player"]]
        if o["zone"] == "slot":
            assert o["slot"] in {s.uid for s in player.slots}, (pending.kind, o)
        elif o["zone"] == "book":
            assert 1 <= o["page"] <= 32 and o["value"] == o["page"], (pending.kind, o)
            if "card" in o:
                assert player.card_at(o["page"]) == o["card"], (pending.kind, o)
        else:
            assert o["zone"] == "discard" and player.discard[o["index"]] == o["card"], (pending.kind, o)


def test_every_card_option_has_location_in_selfplay():
    """NPC 自我對戰中出現的每個卡片選項都帶正確的位置。"""
    found = set()
    for seed in (1, 2, 3):
        for decks in (("level1", "level2"), ("level2", "level1")):
            g = mk_game(decks, seed)
            rngs = [random.Random(f"{seed}:{p}") for p in (0, 1)]
            for _ in range(3000):
                if g.state.phase == GAME_OVER:
                    break
                _check_locations(g, found)
                p = awaited_player(g)
                assert npc.submit_ranked(g, p, npc.decide(g, p, "normal", rngs[p])) is not None
    assert found, "自我對戰沒有出現任何卡片選項"
    assert None not in {zone for _, zone in found}


def mk_game(decks, seed):
    from gash.engine.engine import new_game
    return new_game(deck(decks[0]), seed=seed, decks=(list(deck(decks[0])), list(deck(decks[1]))))
