"""battle-api / online-room 整合測試:房間流程、token 身分、視角過濾、WS 推送。"""

import json

from fastapi.testclient import TestClient

from gash.api.app import app, store

client = TestClient(app)


def create_online(timer=None, seed=5):
    res = client.post("/api/rooms", json={"mode": "online", "timer_seconds": timer, "seed": seed})
    assert res.status_code == 200
    return res.json()


def join(code):
    res = client.post(f"/api/rooms/{code}/join")
    assert res.status_code == 200
    return res.json()


def cmd(code, token, command, expect=200):
    res = client.post(f"/api/rooms/{code}/commands",
                      headers={"X-Player-Token": token}, json={"command": command})
    assert res.status_code == expect, res.text
    return res.json()


# ---------------------------------------------------------------- 房間流程

def test_create_and_join_starts_game():
    r = create_online()
    assert r["room"]["started"] is False
    assert "state" not in r
    j = join(r["code"])
    assert j["room"]["started"] is True
    st = j["state"]
    assert st["turn_no"] == 1
    for p in st["players"]:
        assert p["mp"] == 2 and len(p["slots"]) == 1


def test_join_full_room_rejected():
    r = create_online()
    join(r["code"])
    res = client.post(f"/api/rooms/{r['code']}/join")
    assert res.status_code == 409
    assert res.json()["detail"]["code"] == "room.full"


def test_unknown_room_404():
    assert client.get("/api/rooms/NOPE99/state",
                      headers={"X-Player-Token": "x"}).status_code == 404


def test_local_room_starts_immediately_full_view():
    res = client.post("/api/rooms", json={"mode": "local"})
    body = res.json()
    assert body["room"]["started"] is True
    assert len(body["player_tokens"]) == 2
    # 本機模式全視角:雙方翻開頁都有卡號
    for p in body["state"]["players"]:
        assert all("card" in e for e in p["open_pages"])


# ---------------------------------------------------------------- token 即身分

def test_token_identity_overrides_payload():
    r = create_online()
    j = join(r["code"])
    code = r["code"]
    t0, t1 = r["player_token"], j["player_token"]
    tp = j["state"]["turn_player"]
    tokens = {0: t0, 1: t1}
    # 回合玩家的 token + payload 冒名對手 → 仍以 token 身分處理(成功)
    body = cmd(code, tokens[tp], {"type": "flip_pages", "player": 1 - tp, "count": 1})
    assert body["state"]["players"][tp]["mp"] == 4
    # 非回合玩家的 token 翻頁 → 被拒(身分來自 token)
    res = client.post(f"/api/rooms/{code}/commands",
                      headers={"X-Player-Token": tokens[1 - tp]},
                      json={"command": {"type": "flip_pages", "count": 1}})
    assert res.status_code == 400
    assert res.json()["detail"]["code"] in ("priority.turn", "priority.other", "phase.invalid")


def test_spectator_cannot_command():
    r = create_online()
    join(r["code"])
    spec_token = r["spectate_url"].split("token=")[1]
    res = client.post(f"/api/rooms/{r['code']}/commands",
                      headers={"X-Player-Token": spec_token},
                      json={"command": {"type": "pass"}})
    assert res.status_code == 403


def test_bad_token_rejected():
    r = create_online()
    join(r["code"])
    res = client.get(f"/api/rooms/{r['code']}/state",
                     headers={"X-Player-Token": "bogus"})
    assert res.status_code == 401


# ---------------------------------------------------------------- 視角過濾(HTTP)

def test_opponent_hand_hidden_over_http():
    r = create_online()
    j = join(r["code"])
    code = r["code"]
    s0 = client.get(f"/api/rooms/{code}/state",
                    headers={"X-Player-Token": r["player_token"]}).json()["state"]
    assert all("card" in e for e in s0["players"][0]["open_pages"])
    assert all(set(e) == {"page"} for e in s0["players"][1]["open_pages"])
    # 觀戰視角:雙方皆隱藏
    spec_token = r["spectate_url"].split("token=")[1]
    ssp = client.get(f"/api/rooms/{code}/state",
                     headers={"X-Player-Token": spec_token}).json()["state"]
    for p in ssp["players"]:
        assert all(set(e) == {"page"} for e in p["open_pages"])
    # 己方完整魔本對本人可見;對手完整魔本 MUST NOT 在本人視角
    assert "book" in s0["players"][0] and len(s0["players"][0]["book"]) == 32
    assert "book" not in s0["players"][1]
    # 觀戰視角:雙方 book 皆不含
    for p in ssp["players"]:
        assert "book" not in p


def test_events_endpoint_filtered_and_incremental():
    r = create_online()
    j = join(r["code"])
    code, t1 = r["code"], j["player_token"]
    tp = j["state"]["turn_player"]
    token_tp = r["player_token"] if tp == 0 else t1
    n0 = client.get(f"/api/rooms/{code}/events",
                    headers={"X-Player-Token": t1}).json()["next"]
    cmd(code, token_tp, {"type": "flip_pages", "count": 0})
    body = client.get(f"/api/rooms/{code}/events", params={"since": n0},
                      headers={"X-Player-Token": t1}).json()
    assert body["next"] > n0
    assert all(e["seq"] >= n0 for e in body["events"])


# ---------------------------------------------------------------- WebSocket

def test_ws_welcome_and_push():
    with TestClient(app) as c:
        r = c.post("/api/rooms", json={"mode": "online", "seed": 7}).json()
        j = c.post(f"/api/rooms/{r['code']}/join").json()
        code = r["code"]
        tp = j["state"]["turn_player"]
        tokens = {0: r["player_token"], 1: j["player_token"]}
        with c.websocket_connect(f"/api/rooms/{code}/ws?token={tokens[1 - tp]}") as ws:
            hello = ws.receive_json()
            assert hello["type"] == "welcome"
            assert hello["next_seq"] == hello["state"]["event_count"]
            # 對手出招 → 收到推送(以自己視角過濾)
            c.post(f"/api/rooms/{code}/commands",
                   headers={"X-Player-Token": tokens[tp]},
                   json={"command": {"type": "flip_pages", "count": 2}})
            update = ws.receive_json()
            assert update["type"] == "update"
            assert any(e["type"] == "pages_flipped" for e in update["events"])
            opp_pages = update["state"]["players"][tp]["open_pages"]
            assert all(set(e) == {"page"} for e in opp_pages)  # 推送同樣過濾


def test_ws_bad_token_closed():
    with TestClient(app) as c:
        r = c.post("/api/rooms", json={"mode": "online"}).json()
        try:
            with c.websocket_connect(f"/api/rooms/{r['code']}/ws?token=bogus") as ws:
                ws.receive_json()
            connected = True
        except Exception:
            connected = False
        assert not connected
