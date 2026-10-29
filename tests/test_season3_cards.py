"""第 3 賽季卡片資料(card-data「第 3 賽季卡片資料」)。"""

import json

from fastapi.testclient import TestClient

from gash.api.app import app
from gash.engine.cards import DATA_DIR, card_db, pending_cards
from gash.engine.deck import load_deck

RANGES = {"M": (54, 69), "S": (107, 112), "P": (36, 43), "E": (44, 49), "PR": (1, 11), "Ex": (1, 48)}
SEASON3 = [f"{p}-{i:03d}" for p, (lo, hi) in RANGES.items() for i in range(lo, hi + 1)]


def test_season3_numbers_complete():
    db = card_db()
    assert len(SEASON3) == 95 and all(n in db for n in SEASON3)
    assert len(db) == 332
    for lang in ("ja", "en", "zh-TW", "zh-CN"):
        texts = json.loads((DATA_DIR / f"cards.{lang}.json").read_text(encoding="utf-8"))
        assert all(n in texts for n in SEASON3), lang


def test_ex_numbers_use_atwiki_spelling():
    db = card_db()
    assert db["Ex-025"].name_ja == "ガッシュ・ベル" and db["Ex-025"].type == "mamodo"
    assert not [n for n in db if n.startswith("EX-")]


def test_season3_cards_pending():
    assert set(SEASON3) <= pending_cards()


def test_room_with_ex_card_rejected():
    pages = list(load_deck(DATA_DIR / "decks/level1.json", card_db()).pages)
    pages[20] = "Ex-001"
    res = TestClient(app).post("/api/rooms", json={"mode": "online", "deck": {"pages": pages}})
    assert res.status_code == 422 and res.json()["detail"]["code"] == "deck.card_pending"
