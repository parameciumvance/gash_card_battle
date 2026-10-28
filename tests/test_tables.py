"""牌桌(game-tables)的 API 測試:列表、入座與衝突、離開與斷線寬限、結束後的再戰 / 離開、房間回收。
時間相關的規則直接呼叫牌桌檢查函式並傳入時刻,不實際等待。"""

import asyncio

import pytest
from fastapi.testclient import TestClient

from gash.api import tables as tables_mod
from gash.api.app import app, check_tables, store
from gash.engine.state import GAME_OVER

client = TestClient(app)


@pytest.fixture(autouse=True)
def fresh_tables():
    tables_mod.TABLES.reset()
    yield
    tables_mod.TABLES.reset()


def listing():
    res = client.get("/api/tables")
    assert res.status_code == 200
    return res.json()["tables"]


def sit(number, name, expect="empty", timer=60, deck=None, status=200):
    body = {"name": name, "expect": expect}
    if expect == "empty":
        body["timer_seconds"] = timer
    if deck is not None:
        body["deck"] = deck
    res = client.post(f"/api/tables/{number}/sit", json=body)
    assert res.status_code == status, res.text
    return res.json()


def table(number):
    return listing()[number - 1]


def end_game(code):
    """直接把房間的對局標為結束(對局內容不是這裡要測的)。"""
    store.get(code).game.state.phase = GAME_OVER


def run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------- 列表與入座

def test_listing_has_five_empty_tables():
    t = listing()
    assert [x["number"] for x in t] == [1, 2, 3, 4, 5]
    assert all(x["state"] == "empty" for x in t)


def test_open_table_and_listing_hides_tokens():
    r = sit(2, "小明", timer=60)
    assert r["code"] and r["player_token"]
    t = table(2)
    assert t["state"] == "waiting" and t["names"][0] == "小明" and t["timer_seconds"] == 60
    assert t["waiting_seconds"] >= 0
    text = str(listing())
    assert r["player_token"] not in text and r["code"] not in text


def test_join_waiting_table_starts_game():
    host = sit(2, "小明")
    guest = sit(2, "小美", expect="waiting")
    assert guest["code"] == host["code"] and guest["room"]["started"] is True
    t = table(2)
    assert t["state"] == "playing" and t["names"] == ["小明", "小美"]
    assert t["spectate_url"].startswith(f"/?spectate={host['code']}")


def test_conflict_returns_actual_host_and_timer():
    sit(2, "小明", timer=60)
    res = client.post("/api/tables/2/sit", json={"name": "阿華", "expect": "empty", "timer_seconds": 120})
    assert res.status_code == 409
    detail = res.json()["detail"]
    assert detail["code"] == "table.taken" and detail["host"] == "小明" and detail["timer_seconds"] == 60
    assert table(2)["state"] == "waiting" and table(2)["names"][1] is None   # 後到者沒有入座


@pytest.mark.parametrize("timer", [None, 0, 45])
def test_table_requires_timer(timer):
    res = client.post("/api/tables/1/sit", json={"name": "x", "expect": "empty", "timer_seconds": timer})
    assert res.status_code == 422 and res.json()["detail"]["code"] == "table.bad_timer"
    assert table(1)["state"] == "empty"


def test_invalid_deck_keeps_table():
    sit(1, "x", deck={"pages": ["S-001"] * 32}, status=422)
    assert table(1)["state"] == "empty"


def test_busy_table_rejects_sit():
    sit(3, "a")
    sit(3, "b", expect="waiting")
    res = client.post("/api/tables/3/sit", json={"name": "c", "expect": "waiting"})
    assert res.status_code == 409 and res.json()["detail"]["code"] == "table.busy"


def test_table_room_cannot_be_joined_by_code():
    host = sit(4, "小明")
    res = client.post(f"/api/rooms/{host['code']}/join")
    assert res.status_code == 409 and res.json()["detail"]["code"] == "room.table_only"
    assert table(4)["state"] == "waiting"


# ---------------------------------------------------------------- 離開與斷線

def test_host_leave_frees_table():
    host = sit(4, "小明")
    res = client.post("/api/tables/4/leave", headers={"X-Player-Token": host["player_token"]})
    assert res.status_code == 200
    assert table(4)["state"] == "empty"
    assert client.post(f"/api/rooms/{host['code']}/join").status_code in (404, 409)


def test_host_disconnect_grace():
    sit(4, "小明")
    now = 1_000_000.0
    run(check_tables(now))                       # 沒有連線:開始計時
    run(check_tables(now + 10))
    assert table(4)["state"] == "waiting"        # 寬限內
    run(check_tables(now + 61))
    assert table(4)["state"] == "empty"          # 超過 60 秒


def test_host_reconnect_keeps_table():
    host = sit(4, "小明")
    now = 1_000_000.0
    run(check_tables(now))
    with client.websocket_connect(f"/api/rooms/{host['code']}/ws?token={host['player_token']}") as ws:
        ws.receive_json()
        run(check_tables(now + 30))              # 重新連上:清除缺席
        run(check_tables(now + 120))
        assert table(4)["state"] == "waiting"


# ---------------------------------------------------------------- 結束後的再戰 / 離開

def play_and_end(number):
    host = sit(number, "小明")
    guest = sit(number, "小美", expect="waiting")
    end_game(host["code"])
    return host, guest


def choose(number, token, choice):
    res = client.post(f"/api/tables/{number}/choice", headers={"X-Player-Token": token}, json={"choice": choice})
    assert res.status_code == 200, res.text
    return res.json()


def test_game_over_turns_table_to_ended():
    play_and_end(5)
    assert table(5)["state"] == "ended"


def test_both_rematch_starts_new_room():
    host, guest = play_and_end(5)
    with client.websocket_connect(f"/api/rooms/{host['code']}/ws?token={host['player_token']}") as ws:
        ws.receive_json()
        choose(5, host["player_token"], "rematch")
        choose(5, guest["player_token"], "rematch")
        msg = ws.receive_json()
        while msg["type"] != "table_moved":
            msg = ws.receive_json()
    t = table(5)
    assert t["state"] == "playing" and t["names"] == ["小明", "小美"] and t["timer_seconds"] == 60
    assert msg["code"] != host["code"] and msg["token"] and msg["seat"] == 0 and msg["started"] is True
    new = store.get(msg["code"])
    assert new.viewer_of(msg["token"]) == 0 and new.game is not None


def test_one_leaves_other_hosts():
    host, guest = play_and_end(5)
    choose(5, guest["player_token"], "leave")
    choose(5, host["player_token"], "rematch")
    t = table(5)
    assert t["state"] == "waiting" and t["names"][0] == "小明" and t["names"][1] is None


def test_both_leave_frees_table():
    host, guest = play_and_end(5)
    choose(5, host["player_token"], "leave")
    choose(5, guest["player_token"], "leave")
    assert table(5)["state"] == "empty"


def test_choice_timeout_counts_as_leave():
    host, guest = play_and_end(5)
    now = 1_000_000.0
    run(check_tables(now))                       # 記下結束時刻
    with client.websocket_connect(f"/api/rooms/{host['code']}/ws?token={host['player_token']}") as ws:
        ws.receive_json()
        choose(5, host["player_token"], "rematch")
        run(check_tables(now + 61, notify=False))   # 小美斷線超過 60 秒:視為離開(不推送:測試的事件迴圈不同)
    t = table(5)
    assert t["state"] == "waiting" and t["names"][0] == "小明"


def test_undecided_two_minutes_is_leave():
    host, guest = play_and_end(5)
    now = 1_000_000.0
    with client.websocket_connect(f"/api/rooms/{host['code']}/ws?token={host['player_token']}") as w0, \
         client.websocket_connect(f"/api/rooms/{host['code']}/ws?token={guest['player_token']}") as w1:
        w0.receive_json(); w1.receive_json()
        run(check_tables(now))
        run(check_tables(now + 121))             # 雙方都連著但都沒選:2 分鐘後視為離開
    assert table(5)["state"] == "empty"


def test_idle_cleanup_frees_table():
    host = sit(1, "x")
    store.get(host["code"]).last_activity = 0
    store.cleanup_idle()
    assert table(1)["state"] == "empty"
