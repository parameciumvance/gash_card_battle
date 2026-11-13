"""關閉房間(online-room「關閉房間」,close-rooms):自由調查、NPC 房、沒人加入的朋友房可關閉;
對局中的朋友房、牌桌、觀戰者不行。"""
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from gash.api import tables as tables_mod
from gash.api.app import app, store

client = TestClient(app)


@pytest.fixture(autouse=True)
def fresh_tables():
    tables_mod.TABLES.reset()
    yield
    tables_mod.TABLES.reset()


def close(code, token, status=200, c=client):
    res = c.post(f"/api/rooms/{code}/close", headers={"X-Player-Token": token})
    assert res.status_code == status, res.text
    return res.json()


def error_code(res_json):
    return res_json["detail"]["code"]


def gone(code, token):
    return client.get(f"/api/rooms/{code}/state", headers={"X-Player-Token": token}).status_code == 404


def test_close_local_room():
    r = client.post("/api/rooms", json={"mode": "local"}).json()
    token = r["player_tokens"][0]
    close(r["code"], token)
    assert gone(r["code"], token) and r["code"] not in store.rooms


def test_close_npc_room_stops_driver():
    r = client.post("/api/rooms", json={"mode": "npc"}).json()
    close(r["code"], r["player_token"])
    assert r["code"] not in store.rooms


def test_close_online_room_before_opponent_joins():
    r = client.post("/api/rooms", json={"mode": "online"}).json()
    close(r["code"], r["player_token"])
    res = client.post(f"/api/rooms/{r['code']}/join")
    assert res.status_code == 404                                            # 房號失效


def test_close_started_online_room_rejected():
    a = client.post("/api/rooms", json={"mode": "online", "seed": 5}).json()
    b = client.post(f"/api/rooms/{a['code']}/join").json()
    for token in (a["player_token"], b["player_token"]):
        assert error_code(close(a["code"], token, status=409)) == "room.close_started"
    assert a["code"] in store.rooms                                         # 對局繼續


def test_close_table_room_rejected():
    host = client.post("/api/tables/2/sit", json={"name": "小明", "expect": "empty", "timer_seconds": 60}).json()
    assert error_code(close(host["code"], host["player_token"], status=409)) == "room.close_table"
    assert host["code"] in store.rooms


def test_close_by_spectator_or_bad_token():
    r = client.post("/api/rooms", json={"mode": "local"}).json()
    spectator = store.rooms[r["code"]].spectator_token
    assert error_code(close(r["code"], spectator, status=403)) == "room.close_spectator"
    close(r["code"], "bogus", status=401)
    assert r["code"] in store.rooms


def test_close_unknown_room():
    close("ZZZZZ", "bogus", status=404)


def test_close_disconnects_websockets_with_4404():
    with TestClient(app) as c:
        r = c.post("/api/rooms", json={"mode": "local"}).json()
        token = r["player_tokens"][0]
        with c.websocket_connect(f"/api/rooms/{r['code']}/ws?token={token}") as ws:
            ws.receive_json()                                                # welcome
            close(r["code"], token, c=c)
            with pytest.raises(WebSocketDisconnect) as exc:
                while True:
                    ws.receive_json()
            assert exc.value.code == 4404
