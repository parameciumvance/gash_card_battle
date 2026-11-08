"""第 4 賽季卡片資料(card-data「第 4 賽季卡片資料」「第 4 賽季產品的代號」「atwiki 魔物卡與事件卡的身分」)。"""

import json

import pytest
from fastapi.testclient import TestClient

from gash.api.app import app
from gash.engine.cards import DATA_DIR, card_db, pending_cards
from gash.engine.deck import load_deck
from tests.test_season4_spells import BATCH as SPELLS_BASIC
from tests.test_season4_spells_2a import BATCH as SPELLS_2A
from tests.test_season4_spells_2b import BATCH as SPELLS_2B
from tests.test_season4_events_a import BATCH as EVENTS_A
from tests.test_season4_events_b import BATCH as EVENTS_B

RANGES = {"M": (70, 85), "S": (113, 146), "P": (44, 50), "E": (50, 54), "Ex": (51, 74)}
EXTRA = ["Ex-000", "Ex-049", "Ex-050", "Ex-099", "PR-012", "PR-013"]
MJ12 = [f"MJ-{i:03d}" for i in range(1, 7)]                # LEVEL:4 的 MJ12 卡
SEASON4 = [f"{p}-{i:03d}" for p, (lo, hi) in RANGES.items() for i in range(lo, hi + 1)] + EXTRA + MJ12
DX = ["Ex-100", "Ex-101"]                                   # 第 3 賽季補收:DX赤い魔本附錄
NEW = SEASON4 + DX
IMPLEMENTED = set(MJ12) | {"Ex-074"} | set(SPELLS_BASIC) | set(SPELLS_2A) | set(SPELLS_2B) | set(EVENTS_A) | set(EVENTS_B)   # 已實作、移出尚未開放清單(mj12-cards、season4-spells-*)


def test_numbers_complete():
    db = card_db()
    assert len(SEASON4) == 98 and all(n in db for n in NEW)
    assert len(db) == 432
    for lang in ("ja", "en", "zh-TW", "zh-CN"):
        texts = json.loads((DATA_DIR / f"cards.{lang}.json").read_text(encoding="utf-8"))
        assert all(n in texts for n in NEW), lang


def test_new_cards_pending():
    assert set(NEW) - IMPLEMENTED <= pending_cards()
    assert not IMPLEMENTED & pending_cards()


@pytest.mark.parametrize("number", ["M-070", "E-052", "Ex-051"])
def test_room_with_new_card_rejected(number):
    pages = list(load_deck(DATA_DIR / "decks/level1.json", card_db()).pages)
    pages[20] = number
    res = TestClient(app).post("/api/rooms", json={"mode": "online", "deck": {"pages": pages}})
    assert res.status_code == 422 and res.json()["detail"]["code"] == "deck.card_pending"


def test_products():
    raw = {c["number"]: c for c in json.loads((DATA_DIR / "cards.json").read_text(encoding="utf-8"))}
    assert raw["M-070"]["sets"][0] == "level-4" and raw["Ex-051"]["sets"][0] == "ex-sheet-3"
    assert {n: raw[n]["sets"][0] for n in ("Ex-000", "Ex-049", "Ex-050", "Ex-099", "Ex-100", "Ex-101")} == {
        "Ex-000": "festa-2004-spring", "Ex-049": "festa-2004-spring", "Ex-050": "festa-2004-spring",
        "Ex-099": "festa-2004-spring", "Ex-100": "dx-red-book", "Ex-101": "dx-red-book"}


def test_stone_tablet_and_icons():
    raw = {c["number"]: c for c in json.loads((DATA_DIR / "cards.json").read_text(encoding="utf-8"))}
    assert sorted(n for n, c in raw.items() if c.get("stone_tablet")) == ["Ex-056", "Ex-057", "Ex-058"]
    assert all(raw[n]["type"] == "mamodo" for n in ("Ex-056", "Ex-057", "Ex-058"))
    assert raw["M-080"]["effect_icons"] == ["jammer", "battle"] and raw["M-080"]["effect_icon"] is None


def test_mamodo_without_partner():
    db = card_db()
    assert db["PR-012"].type == "mamodo" and db["PR-012"].related_mamodo == "黒騎士"


def test_mj12_cards():
    # MJ12(LEVEL:4):第 6 種卡片類型,沒有魔力與費用欄位
    db = card_db()
    assert [db[n].type for n in MJ12] == ["mj12"] * 6
    assert db["MJ-004"].effect_ja.startswith("MPを1へらす→") and db["MJ-004"].cost is None
