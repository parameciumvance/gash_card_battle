"""使用中頁揭露:宣告攻防術對所有視角可見,歸屬正確,戰鬥結束恢復保密。"""

from gash.api.views import snapshot
from gash.engine.deck import load_deck
from gash.engine.engine import new_game, submit
from tests.test_engine import deck_pages  # 既有測試牌組


def mk(seed=1):
    return new_game(deck_pages(), seed=seed)


def entry_of(view, p, page):
    return next((e for e in view["players"][p]["open_pages"] if e["page"] == page), None)


def declare(g):
    """回合玩家以第 3 頁 S-001 宣告攻擊;回傳 (攻方, 防方)。"""
    tp = g.state.turn_player
    dp = 1 - tp
    submit(g, {"type": "flip_pages", "player": tp, "count": 0})
    submit(g, {"type": "declare_attack", "player": tp, "page": 3})
    return tp, dp


def test_declared_attack_page_visible_to_all_viewers():
    g = mk()
    tp, dp = declare(g)
    for viewer in (dp, "spectator"):
        e = entry_of(snapshot(g, viewer), tp, 3)
        assert e["card"] == "S-001" and e.get("in_use") is True
    # 持有者本人視角亦帶 in_use 標記
    assert entry_of(snapshot(g, tp), tp, 3).get("in_use") is True


def test_other_open_pages_stay_hidden_during_battle():
    g = mk()
    tp, dp = declare(g)
    view = snapshot(g, dp)
    e2 = entry_of(view, tp, 2)  # 攻方另一翻開頁(第 2 頁)
    assert e2 is not None and "card" not in e2 and "in_use" not in e2


def test_defense_page_attributed_to_defender_only():
    g = mk()
    tp, dp = declare(g)
    submit(g, {"type": "battle_in_response", "player": dp, "allow": True})
    submit(g, {"type": "declare_defense", "player": dp, "page": 2})  # S-025 為 D 術
    view = snapshot(g, "spectator")
    atk = entry_of(view, tp, 3)
    dfn = entry_of(view, dp, 2)
    assert atk["card"] == "S-001" and atk.get("in_use") is True
    assert dfn["card"] == "S-025" and dfn.get("in_use") is True
    # 歸屬正確:攻方的第 2 頁不因防方用第 2 頁而洩漏
    assert "card" not in entry_of(view, tp, 2)


def test_reveal_ends_with_battle():
    g = mk()
    tp, dp = declare(g)
    submit(g, {"type": "battle_in_response", "player": dp, "allow": True})
    submit(g, {"type": "no_defense", "player": dp})
    submit(g, {"type": "pass", "player": tp})
    submit(g, {"type": "pass", "player": dp})
    if g.state.pending is not None:  # 保護詢問
        submit(g, {"type": "choose", "player": g.state.pending.player, "value": None})
    assert g.state.battle is None
    view = snapshot(g, dp)
    e = entry_of(view, tp, 3)
    # 戰鬥結束:頁若仍翻開,恢復僅頁碼
    if e is not None:
        assert "card" not in e and "in_use" not in e
