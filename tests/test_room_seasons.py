"""房間的賽季(online-room「房間的賽季」「魔書依房間賽季驗證」、battle-api「預組的賽季」)。"""

from fastapi.testclient import TestClient

from gash.api.app import app, store
from gash.engine.cards import DATA_DIR, card_db
from gash.engine.deck import load_deck

client = TestClient(app)

LEVEL1 = list(load_deck(DATA_DIR / "decks/level1.json", card_db()).pages)
ZEON = list(load_deck(DATA_DIR / "decks/zeon.json", card_db()).pages)


def create(**body):
    return client.post("/api/rooms", json=body)


def assert_season_rejected(resp, season):
    assert resp.status_code == 422, resp.text
    detail = resp.json()["detail"]
    assert detail["code"] == "deck.season"
    assert detail["season"] == season


def test_create_with_season():
    r = create(mode="online", season=1).json()
    assert r["room"]["season"] == 1


def test_default_season_is_3():
    r = create(mode="online").json()
    assert r["room"]["season"] == 3


def test_unknown_season_rejected():
    before = set(store.rooms)
    resp = create(mode="online", season=4)
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "room.bad_season"
    assert set(store.rooms) == before


def test_creator_preset_beyond_season_rejected():
    before = set(store.rooms)
    assert_season_rejected(create(mode="online", season=1, deck={"preset": "level2"}), 1)
    assert set(store.rooms) == before


def test_creator_custom_deck_beyond_season_rejected():
    assert_season_rejected(create(mode="online", season=2, deck={"pages": ZEON}), 2)


def test_default_deck_allowed_in_season_1():
    r = create(mode="online", season=1)
    assert r.status_code == 200, r.text


def test_joiner_deck_beyond_season_rejected_and_room_still_waiting():
    r = create(mode="online", season=1).json()
    resp = client.post(f"/api/rooms/{r['code']}/join", json={"deck": {"preset": "zeon"}})
    assert_season_rejected(resp, 1)
    room = store.rooms[r["code"]]
    assert room.game is None and room.player_count() == 1
    ok = client.post(f"/api/rooms/{r['code']}/join", json={"deck": {"preset": "level1"}})
    assert ok.status_code == 200, ok.text


def test_local_room_either_deck_beyond_season_rejected():
    assert_season_rejected(create(mode="local", season=1, decks=[{"preset": "level1"}, {"preset": "level2"}]), 1)
    ok = create(mode="local", season=2, decks=[{"preset": "level1"}, {"preset": "level2"}])
    assert ok.status_code == 200, ok.text
    assert ok.json()["room"]["season"] == 2


def test_npc_deck_beyond_season_rejected():
    assert_season_rejected(create(mode="npc", season=1, npc_deck={"preset": "level2"}), 1)


def test_npc_candidates_with_deck_beyond_season_rejected():
    assert_season_rejected(create(mode="npc", season=2, npc_decks=[{"preset": "level1"}, {"preset": "zeon"}]), 2)


def test_npc_candidates_within_season():
    for seed in range(6):
        r = create(mode="npc", season=2, seed=seed, npc_decks=[{"preset": "level1"}, {"preset": "level2"}])
        assert r.status_code == 200, r.text
        assert store.rooms[r.json()["code"]].npc.deck in ({"preset": "level1"}, {"preset": "level2"})


def test_presets_list_has_season():
    decks = {d["id"]: d for d in client.get("/api/decks").json()["decks"]}
    assert decks["level1"]["season"] == 1
    assert decks["level2"]["season"] == 2
    assert decks["gash-nakama"]["season"] == 3
    assert decks["zeon"]["season"] == 3
