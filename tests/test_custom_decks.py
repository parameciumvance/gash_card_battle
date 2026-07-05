"""開局攜帶自訂牌組(deck-builder / online-room 差分)。"""

from fastapi.testclient import TestClient

from gash.api.app import app
from gash.engine.cards import DATA_DIR, card_db
from gash.engine.deck import load_deck

client = TestClient(app)

LEVEL1 = list(load_deck(DATA_DIR / "decks/level1.json", card_db()).pages)


def custom_deck():
    """合法自訂牌組:對調 P2(S-025) 與 P20(E-003),仍符合全部構築規則。"""
    pages = list(LEVEL1)
    pages[1], pages[19] = pages[19], pages[1]
    return pages


def test_create_and_join_with_custom_decks_boards_differ():
    custom = custom_deck()
    r = client.post("/api/rooms", json={"mode": "online", "seed": 5,
                                        "deck": {"pages": custom}}).json()
    j = client.post(f"/api/rooms/{r['code']}/join", json={}).json()
    # 建房者(player 0)視角:自己第 2 頁是 E-003(對調後);對手翻開頁為卡背
    s0 = client.get(f"/api/rooms/{r['code']}/state",
                    headers={"X-Player-Token": r["player_token"]}).json()["state"]
    own = {e["page"]: e.get("card") for e in s0["players"][0]["open_pages"]}
    assert own[2] == "E-003"
    assert all(set(e) == {"page"} for e in s0["players"][1]["open_pages"])
    # 加入者(player 1)缺省 level1:自己第 2 頁是 S-025
    s1 = j["state"]
    own1 = {e["page"]: e.get("card") for e in s1["players"][1]["open_pages"]}
    assert own1[2] == "S-025"


def test_join_with_own_custom_deck():
    custom = custom_deck()
    r = client.post("/api/rooms", json={"mode": "online", "seed": 5}).json()
    j = client.post(f"/api/rooms/{r['code']}/join",
                    json={"deck": {"pages": custom}}).json()
    own1 = {e["page"]: e.get("card") for e in j["state"]["players"][1]["open_pages"]}
    assert own1[2] == "E-003"


def test_local_room_two_custom_decks():
    custom = custom_deck()
    res = client.post("/api/rooms", json={
        "mode": "local",
        "decks": [{"pages": custom}, {"preset": "level1"}],
    }).json()
    pages = {p: [e.get("card") for e in res["state"]["players"][p]["open_pages"]] for p in (0, 1)}
    assert "E-003" in pages[0] and "S-025" in pages[1]


def test_default_preset_unchanged():
    r = client.post("/api/rooms", json={"mode": "local"}).json()
    own = {e["page"]: e.get("card") for e in r["state"]["players"][0]["open_pages"]}
    assert own[2] == "S-025"  # level1 原樣


ILLEGAL_CASES = [
    (LEVEL1[:31], "deck.size"),                                   # 31 頁
    (["S-001"] + LEVEL1[1:], "deck.first_page"),                  # 首頁非魔物
    (LEVEL1[:31] + ["M-012"], "deck.last_page"),                  # 末頁非術
    (LEVEL1[:2] + ["S-005"] + LEVEL1[3:], "deck.superior_page"),  # 上級卡在第 3 頁
    (LEVEL1[:20] + ["S-001", "S-001"] + LEVEL1[22:], "deck.max_copies"),  # S-001 共 5 張
    (["M-001"] + ["M-004", "M-005", "M-006", "M-008", "M-009",
                  "M-011", "M-012", "M-015"] + LEVEL1[9:], "deck.max_mamodo"),  # 魔物 9 張
    (LEVEL1[:5] + ["M-999"] + LEVEL1[6:], "deck.unknown_card"),   # 未知卡號
]


def test_illegal_decks_rejected_422():
    for pages, expect_code in ILLEGAL_CASES:
        res = client.post("/api/rooms", json={"mode": "online", "deck": {"pages": pages}})
        assert res.status_code == 422, expect_code
        assert res.json()["detail"]["code"] == expect_code


def test_join_with_illegal_deck_keeps_seat_free():
    r = client.post("/api/rooms", json={"mode": "online"}).json()
    bad = LEVEL1[:2] + ["S-005"] + LEVEL1[3:]
    res = client.post(f"/api/rooms/{r['code']}/join", json={"deck": {"pages": bad}})
    assert res.status_code == 422
    # 玩家位未被佔用:改用合法牌組可加入
    res = client.post(f"/api/rooms/{r['code']}/join", json={})
    assert res.status_code == 200
