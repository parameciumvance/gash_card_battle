"""local-test-mode:金手指端點——僅本機模式開放,可讀寫 book/mp 並留下 cheat_applied 事件。"""

from fastapi.testclient import TestClient

from gash.api.app import app

client = TestClient(app)


def create_local():
    res = client.post("/api/rooms", json={"mode": "local"})
    assert res.status_code == 200
    return res.json()


def create_online():
    res = client.post("/api/rooms", json={"mode": "online", "seed": 1})
    assert res.status_code == 200
    room = res.json()
    j = client.post(f"/api/rooms/{room['code']}/join")
    assert j.status_code == 200
    room["player_tokens"] = [room["player_token"], j.json()["player_token"]]
    return room


def test_online_room_forbidden():
    r = create_online()
    token = r["player_tokens"][0]
    code = r["code"]
    assert client.get(f"/api/rooms/{code}/debug-state",
                      headers={"X-Player-Token": token}).status_code == 403
    assert client.post(f"/api/rooms/{code}/debug-state", headers={"X-Player-Token": token},
                       json={"players": [{"book": ["M-001"] * 32, "mp": 0},
                                         {"book": ["M-001"] * 32, "mp": 0}]}).status_code == 403


def test_local_room_read_write():
    r = create_local()
    code = r["code"]
    token = r["player_tokens"][0]
    got = client.get(f"/api/rooms/{code}/debug-state", headers={"X-Player-Token": token})
    assert got.status_code == 200
    players = got.json()["players"]
    assert len(players) == 2
    assert len(players[0]["book"]) == 32

    players[0]["book"][4] = "S-017"
    players[0]["mp"] = 99
    posted = client.post(f"/api/rooms/{code}/debug-state", headers={"X-Player-Token": token},
                         json={"players": players})
    assert posted.status_code == 200, posted.text
    assert posted.json()["players"][0]["book"][4] == "S-017"
    assert posted.json()["players"][0]["mp"] == 99

    again = client.get(f"/api/rooms/{code}/debug-state", headers={"X-Player-Token": token}).json()
    assert again["players"][0]["book"][4] == "S-017"
    assert again["players"][0]["mp"] == 99

    events = client.get(f"/api/rooms/{code}/events?since=0",
                        headers={"X-Player-Token": token}).json()["events"]
    assert any(e["type"] == "cheat_applied" for e in events)


def test_unknown_card_rejected():
    r = create_local()
    code, token = r["code"], r["player_tokens"][0]
    players = client.get(f"/api/rooms/{code}/debug-state",
                        headers={"X-Player-Token": token}).json()["players"]
    players[0]["book"][0] = "X-999"
    res = client.post(f"/api/rooms/{code}/debug-state", headers={"X-Player-Token": token},
                      json={"players": players})
    assert res.status_code == 422
    assert res.json()["detail"]["code"] == "debug_state.unknown_card"


def test_bad_book_length_rejected():
    r = create_local()
    code, token = r["code"], r["player_tokens"][0]
    players = client.get(f"/api/rooms/{code}/debug-state",
                        headers={"X-Player-Token": token}).json()["players"]
    players[0]["book"] = players[0]["book"][:31]
    res = client.post(f"/api/rooms/{code}/debug-state", headers={"X-Player-Token": token},
                      json={"players": players})
    assert res.status_code == 422
    assert res.json()["detail"]["code"] == "debug_state.bad_book"
