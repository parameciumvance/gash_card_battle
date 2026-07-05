"""視角過濾測試(online-battle 核心):同一局面對 viewer=0/1/spectator/all
產出不同視圖,斷言私密資訊不外洩。"""

from gash.api.views import filter_event, filter_events, snapshot
from gash.engine.cards import DATA_DIR, card_db
from gash.engine.deck import load_deck
from gash.engine.engine import new_game, submit
from gash.engine.state import MamodoSlot


def mk():
    deck = load_deck(DATA_DIR / "decks/level1.json", card_db())
    g = new_game(deck.pages, seed=1)
    g.state.turn_player = 0
    return g


def test_opponent_open_pages_hidden():
    g = mk()
    for viewer, expect_p0, expect_p1 in [
        (0, True, False), (1, False, True),
        ("spectator", False, False), ("all", True, True),
    ]:
        s = snapshot(g, viewer)
        for p, expect in [(0, expect_p0), (1, expect_p1)]:
            entries = s["players"][p]["open_pages"]
            assert entries, "翻開頁列表(頁碼)對所有視角都存在"
            has_cards = any("card" in e for e in entries)
            assert has_cards == expect, f"viewer={viewer} p={p}"
            if not expect:
                assert all(set(e) == {"page"} for e in entries)  # 只有頁碼,無費用


def test_public_info_visible_to_all():
    g = mk()
    for viewer in (0, 1, "spectator"):
        s = snapshot(g, viewer)
        assert s["players"][0]["mp"] == 2
        assert s["players"][0]["slots"][0]["top"] == "M-001"  # 場上魔物公開
        assert s["players"][1]["pos"] == 2                     # 魔本進度公開


def test_pending_options_only_for_decider():
    g = mk()
    # M-011 檢視對手魔本並選擇 → options 含對手魔本內容,只能給決策者
    fein = MamodoSlot(uid=g.state.next_uid(), stack=["M-011"])
    g.state.players[0].slots.append(fein)
    submit(g, {"type": "flip_pages", "player": 0, "count": 0})
    submit(g, {"type": "use_field_ability", "player": 0, "zone": "mamodo",
               "slot_uid": fein.uid})
    assert g.state.pending is not None and g.state.pending.player == 0
    s0 = snapshot(g, 0)
    s1 = snapshot(g, 1)
    ssp = snapshot(g, "spectator")
    assert "options" in s0["pending"]
    assert "options" not in s1["pending"] and "options" not in ssp["pending"]
    assert s1["pending"]["kind"] == "m011_pick"  # 「誰在決策」是公開的


def test_book_revealed_event_filtered():
    g = mk()
    fein = MamodoSlot(uid=g.state.next_uid(), stack=["M-011"])
    g.state.players[0].slots.append(fein)
    submit(g, {"type": "flip_pages", "player": 0, "count": 0})
    events = submit(g, {"type": "use_field_ability", "player": 0, "zone": "mamodo",
                        "slot_uid": fein.uid})
    reveal = next(e for e in events if e["type"] == "book_revealed")
    assert "cards" in filter_event(reveal, 0)          # 檢視者可見
    assert "cards" not in filter_event(reveal, 1)      # 被檢視者不知道對方看到什麼順序細節
    assert "cards" not in filter_event(reveal, "spectator")
    assert "cards" in filter_event(reveal, "all")


def test_choice_required_event_filtered():
    g = mk()
    tp = 0
    submit(g, {"type": "flip_pages", "player": tp, "count": 0})
    submit(g, {"type": "declare_attack", "player": tp, "page": 3})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    submit(g, {"type": "no_defense", "player": 1})
    submit(g, {"type": "pass", "player": tp})
    events = submit(g, {"type": "pass", "player": 1})
    choice = next(e for e in events if e["type"] == "choice_required")
    assert choice["player"] == 1
    assert "item" in filter_event(choice, 1) or "options" in filter_event(choice, 1)
    stripped = filter_event(choice, 0)
    assert "options" not in stripped and "item" not in stripped
    assert stripped["kind"] == "protect"  # 事件本身(誰在決策)公開


def test_filter_events_keeps_order_and_seq():
    g = mk()
    submit(g, {"type": "flip_pages", "player": 0, "count": 2})
    out = filter_events(g.events, "spectator")
    seqs = [e["seq"] for e in out]
    assert seqs == sorted(seqs)
    assert len(out) == len(g.events)  # 事件都在(內容可能裁剪),序號連續可對齊
