"""investigation-ux:自由調查時間固定玩家 1 先攻(game-engine「準備階段」)、保護決策的傷害內容
(battle-api「決策與戰鬥的公開脈絡」)。"""

from fastapi.testclient import TestClient

from gash.api.app import app, store
from gash.api.views import snapshot
from gash.engine.engine import new_game, submit
from tests.test_level2 import book, mk, to_battle

client = TestClient(app)


def test_local_room_player1_goes_first():
    for seed in range(8):
        body = client.post("/api/rooms", json={"mode": "local", "seed": seed}).json()
        room = store.get(body["room"]["code"])
        events = room.game.events
        assert room.game.state.turn_player == 0
        assert not [e for e in events if e["type"] == "coin_flipped" and e.get("source") == "setup"]
        assert [e for e in events if e["type"] == "first_player_set"] == [
            {**next(e for e in events if e["type"] == "first_player_set"), "player": 0, "reason": "local"}]


def test_other_modes_still_flip_for_first_player():
    seen = set()
    for seed in range(12):
        g = new_game(book("M-001"), seed=seed)
        assert [e for e in g.events if e["type"] == "coin_flipped" and e.get("source") == "setup"]
        seen.add(g.state.turn_player)
    assert seen == {0, 1}


def _book_damage(pos1=None):
    g, _ = mk(book("M-001", "S-005"), book("M-001"))
    st = g.state
    st.players[0].mp = 10
    if pos1 is not None:
        st.players[1].pos = pos1
    to_battle(g, 0)
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    submit(g, {"type": "no_defense", "player": 1})
    submit(g, {"type": "pass", "player": 0})
    submit(g, {"type": "pass", "player": 1})
    assert st.pending.kind == "protect"
    return g


def test_protect_pending_info_book_damage_public():
    g = _book_damage()
    infos = [snapshot(g, v)["pending"]["info"]["damage"] for v in (0, 1, "spectator")]
    assert infos[0] == infos[1] == infos[2]
    assert infos[0] == {"kind": "book", "player": 1, "amount": 3, "slot": None, "injured": False, "lethal": False}


def test_protect_pending_info_lethal():
    g = _book_damage(pos1=28)                                                 # 第 28 頁 + 3 點傷害 → 耗盡
    assert g.state.pending.info["damage"]["lethal"] is True


def test_protect_pending_info_mamodo_damage():
    from tests.test_level3 import add_slot
    g, _ = mk(book("M-051", "S-058"), book("M-001"))
    st = g.state
    st.players[0].mp = 10
    target = st.players[1].slots[0]
    target.injured = True
    add_slot(g, 1, "M-002")
    to_battle(g, 0)
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    submit(g, {"type": "choose", "player": 0, "value": target.uid})
    submit(g, {"type": "no_defense", "player": 1})
    submit(g, {"type": "pass", "player": 0})
    submit(g, {"type": "pass", "player": 1})
    assert st.pending.kind == "protect"
    assert st.pending.info["damage"] == {"kind": "slot", "player": 1, "amount": 1, "slot": target.uid,
                                         "injured": True, "lethal": False}
