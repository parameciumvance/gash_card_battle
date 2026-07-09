"""玩家暱稱與己方全魔本快照(online-room / battle-api 差分)。"""

import json

import gash.api.app as appmod
from fastapi.testclient import TestClient
from gash.api.app import _clean_name

client = TestClient(appmod.app)


# ---------------------------------------------------------------- 暱稱清理

def test_clean_name_trims_and_limits():
    assert _clean_name("  阿賢  ") == "阿賢"
    assert _clean_name("x" * 40) == "x" * 16          # 限長 16
    assert _clean_name("") is None                     # 空 → 預設
    assert _clean_name("   ") is None                  # 純空白 → 預設
    assert _clean_name(None) is None
    assert _clean_name("a\x00b\x07c") == "abc"         # 控制字元濾除


# ---------------------------------------------------------------- 暱稱端到端

def test_create_and_join_carry_names():
    r = client.post("/api/rooms", json={"mode": "online", "name": " 阿賢 "}).json()
    code = r["code"]
    assert r["room"]["names"][0] == "阿賢"
    j = client.post(f"/api/rooms/{code}/join", json={"name": "小美"}).json()
    assert j["room"]["names"] == ["阿賢", "小美"]


def test_local_room_both_names():
    r = client.post("/api/rooms", json={"mode": "local",
                    "names": ["黑貓", "白狗"]}).json()
    assert r["room"]["names"] == ["黑貓", "白狗"]


def test_missing_name_defaults_to_none():
    r = client.post("/api/rooms", json={"mode": "online"}).json()
    assert r["room"]["names"] == [None, None]


def test_name_in_state_snapshot_after_reload():
    r = client.post("/api/rooms", json={"mode": "local", "names": ["甲", "乙"]}).json()
    code = r["code"]
    tok = r["player_tokens"][0]
    s = client.get(f"/api/rooms/{code}/state", headers={"X-Player-Token": tok}).json()
    assert s["room"]["names"] == ["甲", "乙"]


# ---------------------------------------------------------------- 己方全魔本視角化

def test_own_book_visible_opponent_hidden():
    r = client.post("/api/rooms", json={"mode": "online"}).json()
    code = r["code"]
    client.post(f"/api/rooms/{code}/join").json()
    s0 = client.get(f"/api/rooms/{code}/state",
                    headers={"X-Player-Token": r["player_token"]}).json()["state"]
    assert len(s0["players"][0]["book"]) == 32     # 自己完整
    assert "book" not in s0["players"][1]          # 對手不含


def test_local_all_view_both_books():
    r = client.post("/api/rooms", json={"mode": "local"}).json()
    code = r["code"]
    s = client.get(f"/api/rooms/{code}/state",
                   headers={"X-Player-Token": r["player_tokens"][0]}).json()["state"]
    # 本機全視角:雙方 book 皆含
    assert len(s["players"][0]["book"]) == 32
    assert len(s["players"][1]["book"]) == 32


def test_name_not_executable_markup_preserved_as_text():
    # XSS 字串經清理後仍為純文字(前端以 textContent 呈現);清理不改變可見字元
    raw = "<b>x</b>"
    r = client.post("/api/rooms", json={"mode": "online", "name": raw}).json()
    assert r["room"]["names"][0] == "<b>x</b>"      # 原樣保留,前端負責不執行
