"""battle-api spec 整合測試:建局 → 指令 → 狀態 → 資訊隱藏 → 增量事件。"""

from fastapi.testclient import TestClient

from gash.api.app import app

client = TestClient(app)


def create(seed=5):
    res = client.post("/api/games", json={"seed": seed})
    assert res.status_code == 200
    return res.json()


def test_create_game_initial_state():
    data = create()
    st = data["state"]
    assert st["phase"] == "start"
    assert st["turn_no"] == 1
    for p in st["players"]:
        assert p["mp"] == 2
        assert p["pos"] == 2
        assert len(p["slots"]) == 1 and p["slots"][0]["top"] == "M-001"
        assert {e["page"] for e in p["open_pages"]} == {2, 3}


def test_command_flow_and_illegal_rejection():
    data = create()
    gid = data["game_id"]
    tp = data["state"]["turn_player"]
    # 非法:非回合玩家翻頁
    res = client.post(f"/api/games/{gid}/commands",
                      json={"command": {"type": "flip_pages", "player": 1 - tp, "count": 1}})
    assert res.status_code == 400
    assert res.json()["detail"]["code"] == "priority.turn"
    # 合法:回合玩家翻 2 張
    res = client.post(f"/api/games/{gid}/commands",
                      json={"command": {"type": "flip_pages", "player": tp, "count": 2}})
    assert res.status_code == 200
    body = res.json()
    assert any(e["type"] == "pages_flipped" for e in body["events"])
    assert body["state"]["players"][tp]["mp"] == 6


def test_hidden_pages_not_in_response():
    data = create()
    gid = data["game_id"]
    # 快照中只有翻開頁的卡號;未翻開頁(如第 32 頁的 S-005)不得出現
    text = client.get(f"/api/games/{gid}/state").text
    assert "S-005" not in text
    assert "M-012" not in text  # 第 14 頁
    # 建局回應同樣不外洩
    import json
    created_text = json.dumps(data)
    assert "S-005" not in created_text


def test_spell_cost_shown_with_last_page_rule():
    data = create()
    st = data["state"]
    spells = {e["card"]: e["cost"] for e in st["players"][0]["open_pages"] if "cost" in e}
    assert spells.get("S-001") == 1  # 第 3 頁札克爾


def test_incremental_events():
    data = create()
    gid = data["game_id"]
    n0 = data["state"]["event_count"]
    tp = data["state"]["turn_player"]
    client.post(f"/api/games/{gid}/commands",
                json={"command": {"type": "flip_pages", "player": tp, "count": 0}})
    res = client.get(f"/api/games/{gid}/events", params={"since": n0})
    body = res.json()
    assert body["next"] > n0
    assert all(e["seq"] >= n0 for e in body["events"])
    seqs = [e["seq"] for e in body["events"]]
    assert seqs == sorted(seqs)


def test_unknown_game_404():
    res = client.get("/api/games/nope/state")
    assert res.status_code == 404
