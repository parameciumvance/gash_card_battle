"""對戰中人數(online-room「對戰中人數」):以房間的 WebSocket 連線計數。"""

from contextlib import ExitStack

import pytest
from fastapi.testclient import TestClient

from gash.api.app import app, store
from tests.test_npc_room import SEED_PLAYER_FIRST


@pytest.fixture(autouse=True)
def isolated_rooms():
    """只計算本測試建立的房間;結束後還原其他測試留下的房間。"""
    saved = dict(store.rooms)
    store.rooms.clear()
    yield
    store.rooms.clear()
    store.rooms.update(saved)


@pytest.fixture
def c():
    with TestClient(app) as client:
        yield client


def online(c):
    res = c.get("/api/online")
    assert res.status_code == 200
    return res.json()


def connect(stack, c, code, token):
    """在 stack 中開一條連線;斷言失敗時也會關閉,TestClient 才不會卡在等待中的連線。"""
    ws = stack.enter_context(c.websocket_connect(f"/api/rooms/{code}/ws?token={token}"))
    assert ws.receive_json()["type"] == "welcome"   # 收到 welcome 時連線已登記
    return ws


def online_room(c):
    r = c.post("/api/rooms", json={"mode": "online", "seed": 7}).json()
    j = c.post(f"/api/rooms/{r['code']}/join").json()
    spectator = r["spectate_url"].split("token=")[1]
    return r["code"], r["player_token"], j["player_token"], spectator


def test_players_and_spectators_counted(c):
    code, t0, t1, spec = online_room(c)
    with ExitStack() as stack:
        for token in (t0, t1, spec, spec):
            connect(stack, c, code, token)
        assert online(c) == {"count": 4}


def test_same_seat_counted_once(c):
    code, t0, _, _ = online_room(c)
    with ExitStack() as stack:
        connect(stack, c, code, t0)
        connect(stack, c, code, t0)
        assert online(c)["count"] == 1


def test_npc_not_counted(c):
    r = c.post("/api/rooms", json={"mode": "npc", "seed": SEED_PLAYER_FIRST, "npc_level": "dummy"}).json()
    with ExitStack() as stack:
        connect(stack, c, r["code"], r["player_token"])
        assert online(c) == {"count": 1}


def test_waiting_creator_counted(c):
    r = c.post("/api/rooms", json={"mode": "online"}).json()
    with ExitStack() as stack:
        connect(stack, c, r["code"], r["player_token"])
        state = c.get(f"/api/rooms/{r['code']}/state", headers={"X-Player-Token": r["player_token"]}).json()
        assert state["room"]["started"] is False
        assert online(c) == {"count": 1}


def test_rooms_without_connections_not_counted(c):
    c.post("/api/rooms", json={"mode": "local"})
    online_room(c)
    assert len(store.rooms) == 2
    assert online(c) == {"count": 0}


def test_disconnect_no_longer_counted(c):
    code, t0, t1, _ = online_room(c)
    with ExitStack() as outer:
        connect(outer, c, code, t0)
        with ExitStack() as inner:
            connect(inner, c, code, t1)
            assert online(c)["count"] == 2
        assert online(c)["count"] == 1
    assert online(c)["count"] == 0


def test_response_has_no_room_info(c):
    code, t0, _, _ = online_room(c)
    with ExitStack() as stack:
        connect(stack, c, code, t0)
        res = c.get("/api/online")
        assert set(res.json()) == {"count"}
        assert code not in res.text
