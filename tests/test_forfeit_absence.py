"""棄權與對手沒有回應(online-room「棄權」「對手沒有回應」「雙方都沒有回應」)。
時間相關的規則直接呼叫檢查函式並傳入時刻,不實際等待。

Run: python -m pytest tests/test_forfeit_absence.py -q
"""
import asyncio

import pytest
from fastapi.testclient import TestClient

from gash.api import tables as tables_mod
from gash.api.app import _fire_due_timeouts, app, check_absence, store
from gash.engine.awaiting import awaited_player
from gash.engine.state import GAME_OVER

client = TestClient(app)


def run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def fresh_tables():
    tables_mod.TABLES.reset()
    yield
    tables_mod.TABLES.reset()


def online(timer=30):
    a = client.post("/api/rooms", json={"mode": "online", "timer_seconds": timer, "seed": 5}).json()
    b = client.post(f"/api/rooms/{a['code']}/join").json()
    return a["code"], {0: a["player_token"], 1: b["player_token"]}


def post(code, path, token, body=None, status=200):
    res = client.post(f"/api/rooms/{code}/{path}", headers={"X-Player-Token": token}, json=body or {})
    assert res.status_code == status, res.text
    return res.json()


def room_meta(code, token):
    return client.get(f"/api/rooms/{code}/state", headers={"X-Player-Token": token}).json()


def time_out(code, times=1):
    """讓目前等待的玩家逾時 times 次;回傳每次逾時的玩家。"""
    room = store.rooms[code]
    who = []
    for _ in range(times):
        who.append(awaited_player(room.game))
        room.deadline = 1.0
        run(_fire_due_timeouts(now=2.0))
    return who


# ---------------------------------------------------------------- 棄權

def test_forfeit_ends_game_for_opponent():
    code, tok = online()
    body = post(code, "forfeit", tok[0])
    assert body["state"]["phase"] == GAME_OVER
    assert body["state"]["winner"] == 1 and body["state"]["end_reason"] == "forfeit"
    assert any(e["type"] == "game_ended" for e in body["events"])
    post(code, "forfeit", tok[1], status=409)                                 # 已結束
    post(code, "forfeit", store.rooms[code].spectator_token, status=403)


def test_forfeit_allowed_on_opponents_turn_and_in_npc_room_not_local():
    code, tok = online()
    waiting = 1 - awaited_player(store.rooms[code].game)
    assert post(code, "forfeit", tok[waiting])["state"]["winner"] == 1 - waiting
    npc = client.post("/api/rooms", json={"mode": "npc"}).json()
    assert post(npc["code"], "forfeit", npc["player_token"])["state"]["end_reason"] == "forfeit"
    local = client.post("/api/rooms", json={"mode": "local"}).json()
    post(local["code"], "forfeit", local["player_tokens"][0], status=409)


def test_forfeit_before_start_rejected():
    a = client.post("/api/rooms", json={"mode": "online"}).json()
    post(a["code"], "forfeit", a["player_token"], status=409)


# ---------------------------------------------------------------- 對手沒有回應(計時房)

def test_two_consecutive_timeouts_mark_unresponsive():
    code, tok = online()
    p = awaited_player(store.rooms[code].game)
    assert time_out(code, 2) == [p, p]                                        # 開始階段 → 非戰鬥中都是回合玩家
    run(check_absence(now=10.0))
    assert room_meta(code, tok[1 - p])["room"]["unresponsive"] == [p == 0, p == 1]


def test_one_timeout_is_not_unresponsive_and_own_action_resets():
    code, tok = online()
    p = awaited_player(store.rooms[code].game)
    time_out(code, 1)
    run(check_absence(now=10.0))
    assert room_meta(code, tok[1 - p])["room"]["unresponsive"] == [False, False]
    post(code, "commands", tok[p], {"command": {"type": "pass"}})             # 自己行動:歸零
    time_out(code, 1)                                                          # 輪到對手
    run(check_absence(now=10.0))
    assert room_meta(code, tok[p])["room"]["unresponsive"] == [False, False]


def test_end_when_opponent_unresponsive():
    code, tok = online()
    p = awaited_player(store.rooms[code].game)
    post(code, "absence", tok[1 - p], {"action": "end"}, status=409)          # 對手有回應時不行
    time_out(code, 2)
    run(check_absence(now=10.0))
    post(code, "absence", tok[p], {"action": "end"}, status=409)              # 沒回應的人自己不行
    body = post(code, "absence", tok[1 - p], {"action": "end"})
    assert body["state"]["winner"] == 1 - p and body["state"]["end_reason"] == "absent"


def opponent_acts_until_timeouts(code, tok, p, count):
    """沒回應的 p 輪到時讓他逾時,輪到對手時對手自己送安全指令,直到 p 再逾時 count 次。"""
    from gash.engine.awaiting import default_command
    room = store.rooms[code]
    done = 0
    for _ in range(40):
        if done == count:
            return
        if awaited_player(room.game) == p:
            time_out(code, 1)
            done += 1
        else:
            command = default_command(room.game)
            command.pop("player", None)
            post(code, "commands", tok[1 - p], {"command": command})
    raise AssertionError("沒回應的一方沒有輪到")


def test_keep_waiting_then_ask_again():
    code, tok = online()
    p = awaited_player(store.rooms[code].game)
    time_out(code, 2)
    run(check_absence(now=10.0))
    post(code, "absence", tok[1 - p], {"action": "wait"})
    assert room_meta(code, tok[1 - p])["room"]["unresponsive"] == [False, False]
    opponent_acts_until_timeouts(code, tok, p, 1)
    run(check_absence(now=20.0))
    assert room_meta(code, tok[1 - p])["room"]["unresponsive"][p] is False   # 繼續等之後只逾時 1 次:還不問
    opponent_acts_until_timeouts(code, tok, p, 1)
    run(check_absence(now=30.0))
    assert room_meta(code, tok[1 - p])["room"]["unresponsive"][p] is True    # 再逾時 2 次:再問一次


def test_both_unresponsive_closes_room_and_table():
    host = client.post("/api/tables/3/sit", json={"name": "甲", "expect": "empty", "timer_seconds": 30}).json()
    client.post("/api/tables/3/sit", json={"name": "乙", "expect": "waiting"})
    code = host["code"]
    room = store.rooms[code]
    for _ in range(12):                                                        # 雙方都一直逾時
        if room.game.state.phase == GAME_OVER:
            break
        time_out(code, 1)
    run(check_absence(now=10.0))
    assert code not in store.rooms
    assert client.get("/api/tables").json()["tables"][2]["state"] == "empty"


# ---------------------------------------------------------------- 對手沒有回應(不計時房)

class FakeSocket:
    async def send_json(self, _msg):
        pass

    async def close(self, code=1000):
        pass


def test_untimed_absent_awaited_player():
    code, tok = online(timer=None)
    room = store.rooms[code]
    p = awaited_player(room.game)
    room.sockets.append((FakeSocket(), 1 - p))                                # 只有對手連線
    run(check_absence(now=1000.0))
    run(check_absence(now=1030.0))
    assert room_meta(code, tok[1 - p])["room"]["unresponsive"] == [False, False]
    run(check_absence(now=1061.0))
    assert room_meta(code, tok[1 - p])["room"]["unresponsive"][p] is True


def test_untimed_both_absent_closes_room():
    code, _ = online(timer=None)
    run(check_absence(now=1000.0))
    run(check_absence(now=1061.0))
    assert code not in store.rooms
