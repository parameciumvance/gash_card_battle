"""非回合玩家可用行動的快照(battle-api「非回合玩家可用行動的快照」)。

魔書以 test_level2.book 建立,空頁補 S-029(賈修的攻防戰術):非回合玩家的魔物不是賈修時,這些頁不能用來防禦。
"""
import copy

import pytest

from gash.api.views import snapshot
from gash.engine.engine import submit
from tests.test_level2 import book, mk, to_battle


def idle(g, viewer=1):
    return snapshot(g, viewer).get("idle")


def nonbattle_opponent_turn(book1):
    """玩家 0 的回合,戰鬥階段非戰鬥中;玩家 0 pass 後輪到玩家 1(非回合玩家)。"""
    g, _ = mk(book("M-001"), book1)
    g.state.players[1].mp = 10
    to_battle(g, 0)
    submit(g, {"type": "pass", "player": 0})
    assert g.state.action_player == 1 and g.state.pending is None
    return g


def battle_in(book1):
    """玩家 0 以 S-029 宣告攻擊,等待玩家 1 的進入戰鬥確認。"""
    g, _ = mk(book("M-001"), book1)
    g.state.players[0].mp = g.state.players[1].mp = 10                    # 雙方 MP 足夠,可用與否只看卡片
    to_battle(g, 0)
    submit(g, {"type": "declare_attack", "player": 0, "page": 2, "slot_uid": g.state.players[0].slots[0].uid})
    assert g.state.battle_in is not None
    return g


def test_nonbattle_without_actions_auto_pass():
    g = nonbattle_opponent_turn(book("M-004"))
    assert idle(g) == {"has_actions": False, "auto": {"type": "pass"}}


def test_nonbattle_with_usable_event():
    g = nonbattle_opponent_turn(book("M-004", "E-031"))                    # E-031:費用 0,對手回合也能用
    assert idle(g) == {"has_actions": True, "auto": None}


def test_battle_in_with_insertable_event():
    g = battle_in(book("M-004", "E-031"))
    assert idle(g) == {"has_actions": True, "auto": None}


def test_battle_in_without_actions_auto_enters_battle():
    g = battle_in(book("M-004"))
    assert idle(g) == {"has_actions": False, "auto": {"type": "battle_in_response", "allow": True}}


def to_defense(book1):
    g = battle_in(book1)
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    assert g.state.battle is not None and g.state.battle.step == "defense" and g.state.pending is None
    return g


def test_defense_without_any_defense_auto_no_defense():
    g = to_defense(book("M-004"))                                         # S-029 不是ティオ能用的戰術
    assert idle(g) == {"has_actions": False, "auto": {"type": "no_defense"}}


def test_defense_with_spell():
    g = to_defense(book("M-001"))                                         # 賈修可以用 S-029 防禦
    assert idle(g)["has_actions"] is True


def test_defense_with_mamodo_effect_only():
    g = to_defense(book("M-039"))                                         # M-039:魔物效果防禦
    assert idle(g)["has_actions"] is True


def test_effects_step_without_actions():
    g = to_defense(book("M-004"))
    submit(g, {"type": "no_defense", "player": 1})
    st = g.state
    while st.battle and st.battle.step == "effects" and st.pending is None and st.battle.data["effect_turn"] == 0:
        submit(g, {"type": "pass", "player": 0})
    assert st.battle and st.battle.data["effect_turn"] == 1
    assert idle(g) == {"has_actions": False, "auto": {"type": "pass"}}


@pytest.mark.parametrize("viewer", [0, "spectator"])
def test_others_cannot_see(viewer):
    g = nonbattle_opponent_turn(book("M-004"))
    assert idle(g, viewer) is None


def test_local_all_view_sees_awaited_non_turn_player():
    g = nonbattle_opponent_turn(book("M-004"))
    assert idle(g, "all") == {"has_actions": False, "auto": {"type": "pass"}}


def test_turn_player_has_no_idle():
    g, _ = mk(book("M-001"), book("M-004"))
    to_battle(g, 0)
    assert g.state.action_player == 0
    assert idle(g, 0) is None and idle(g, "all") is None


def test_check_does_not_touch_real_game():
    g = nonbattle_opponent_turn(book("M-004", "E-031"))
    before = copy.deepcopy(g.state)
    rng_before = g.rng.getstate()
    idle(g)
    assert g.state == before and g.rng.getstate() == rng_before
