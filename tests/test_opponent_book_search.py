"""檢視對手魔書的效果不以對象為使用條件(card-effects「檢視對手魔書的效果不以對象為使用條件」):
M-011 / E-016 / E-017 照樣檢視,沒有對象就不棄、不扣 MP;使用前不因對手魔書內容停用。
檢視要等檢視者結束:有對象由玩家選(唯一一張也要選),沒有對象停在「結束檢視」。"""
import pytest

from gash.api.views import snapshot
from gash.engine.engine import IllegalCommand, submit

from .test_level2 import DB, book, mk, to_battle


def revealed(events, viewer):
    return any(e["type"] == "book_revealed" and e["viewer"] == viewer for e in events)


def end_review(g, player):
    """沒有可選的卡:停在結束檢視,選項附整本未離開頁的卡面;結束後效果完成。"""
    p = g.state.pending
    assert p.kind == "end_book_review" and p.player == player
    assert [o["label"] for o in p.options] == ["end_review"]
    opp = g.state.players[1 - player]
    assert p.options[0]["cards"] == [{"page": pg, "card": opp.card_at(pg)}
                                     for pg in range(1, 33) if pg not in opp.consumed_pages]
    with pytest.raises(IllegalCommand):                                     # 檢視中對手不能行動
        submit(g, {"type": "pass", "player": 1 - player})
    submit(g, {"type": "choose", "player": player, "value": None})
    assert g.state.pending is None


def no_book_cards(kind_fill):
    """對手魔書:第 1 頁魔物(已在場上),其餘全是 kind_fill。"""
    return ["M-001"] + [kind_fill] * 31


def test_m011_usable_without_mamodo_in_opponent_book():
    g, _ = mk(book("M-011"), no_book_cards("S-029"))
    fein = g.state.players[0].slots[0]
    to_battle(g, 0)
    discard_before = list(g.state.players[1].discard)
    events = submit(g, {"type": "use_field_ability", "player": 0, "zone": "mamodo", "slot_uid": fein.uid})
    assert revealed(events, 0)
    end_review(g, 0)
    assert g.state.players[1].discard == discard_before                     # 沒有卡被棄
    assert "M-011" in g.state.players[0].used_per_game                    # 算使用過(一場一次)


def test_e016_usable_without_spell_in_opponent_book():
    opp = ["M-001"] + ["E-003"] * 30 + ["S-029"]                            # 戰術只在最後一頁
    g, _ = mk(book("M-001", "E-016"), opp)
    g.state.players[0].mp = 10
    to_battle(g, 0)
    events = submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    assert revealed(events, 0)
    end_review(g, 0)
    assert g.state.players[1].discard == []
    assert g.state.players[0].mp == 10 - DB["E-016"].cost                   # 只付自己的費用,不因棄卡減少
    assert g.state.players[0].events_used_this_turn == 1                         # 使用照常成立


def test_e017_not_disabled_and_usable_without_event_in_opponent_book():
    g, _ = mk(book("M-001", "E-017"), no_book_cards("S-029"))
    g.state.players[0].mp = 10
    to_battle(g, 0)
    entry = next(e for e in snapshot(g, 0)["players"][0]["open_pages"] if e.get("card") == "E-017")
    assert entry["condition_ok"] is True                                    # 使用前不透露對手魔書內容
    events = submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    assert revealed(events, 0)
    end_review(g, 0)
    assert g.state.players[1].discard == []
    assert g.state.players[0].mp == 10 - DB["E-017"].cost


def test_single_target_still_chosen_by_player():
    # 唯一的對象也由玩家在網格選(不自動選):選了就結束檢視
    g, _ = mk(book("M-001", "E-017"), book("M-001", "E-003"))
    g.state.players[0].mp = 10
    to_battle(g, 0)
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    p = g.state.pending
    assert p.kind == "pick_opponent_book_card" and [o["value"] for o in p.options] == [2]
    submit(g, {"type": "choose", "player": 0, "value": 2})
    assert g.state.pending is None and "E-003" in g.state.players[1].discard
