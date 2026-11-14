"""進入戰鬥確認時非回合玩家插入的 1 個行動(game-engine「進入戰鬥確認」):非戰鬥戰術與 E-010 借用的搭檔效果。

Run: python -m pytest tests/test_battle_in_insert.py -q
"""
from gash.engine.effects.primitives import add_modifier
from gash.engine.engine import submit
from gash.engine.state import DUR_TURN
from tests.test_level2 import book, mk, to_battle


def to_battle_in(g):
    """雙方 MP 10;玩家 0 以第 3 頁的香草戰術宣告攻擊,停在玩家 1 的進入戰鬥確認。"""
    for ps in g.state.players:
        ps.mp = 10
    to_battle(g, 0)
    submit(g, {"type": "declare_attack", "player": 0, "page": 3})
    assert g.state.battle_in is not None


def test_insert_nonbattle_spell():
    # PR-009 ラウザルク(攻防圖示的非戰鬥戰術):非回合玩家可在確認時插入使用
    g, _ = mk(book("M-001"), book("M-001", "PR-009"))
    to_battle_in(g)
    events = submit(g, {"type": "use_book_card", "player": 1, "page": 2})
    types = [e["type"] for e in events]
    assert "battle_in_voided" in types and "book_card_used" in types
    assert g.state.battle_in is None and g.state.battle is None
    assert g.state.action_player == 0                                     # 回到回合玩家,不強制攻擊
    assert 2 in g.state.players[1].used_nonbattle_pages


def test_insert_borrowed_partner_effect():
    # E-010 借用的搭檔效果也是使用效果的 1 個行動,與場上效果相同可以插入
    g, _ = mk(book("M-001"), book("M-001"))
    add_modifier(g, [], kind="borrow_partner", source="E-010", owner=1, duration=DUR_TURN,
                 data={"card": "Ex-007", "used": False})                 # 高嶺清麿:不限自己的回合
    to_battle_in(g)
    events = submit(g, {"type": "use_borrowed_effect", "player": 1})
    types = [e["type"] for e in events]
    assert "battle_in_voided" in types
    assert any(e["type"] == "ability_used" and e.get("zone") == "borrowed" for e in events)
    assert g.state.battle_in is None and g.state.battle is None
    assert g.state.action_player == 0
