"""賽季定義(card-data「賽季定義」「魔書的賽季」「構築規則的賽季限制」)。"""

import json

import pytest

from gash.engine.cards import DATA_DIR, card_db
from gash.engine.deck import DeckError, validate_deck
from gash.engine.seasons import card_season, deck_season


def _preset(name):
    return json.loads((DATA_DIR / f"decks/{name}.json").read_text(encoding="utf-8"))["pages"]


@pytest.mark.parametrize("number, season", [
    ("M-015", 1), ("M-016", 2), ("S-106", 3), ("M-053", 3),
    ("PR-002", 1), ("PR-003", 2), ("Ex-010", 2), ("Ex-048", 3),
])
def test_card_season(number, season):
    assert card_season(number) == season


def test_special_assignment_overrides_range():
    assert card_season("Ex-000") == 4


def test_card_outside_every_season_has_none():
    assert card_season("M-086") is None                  # LIMITED EDITION Ⅱ:第 5 賽季,尚未定義
    assert card_season("Ex-075") is None
    assert card_season("MJ-007") is None                 # MJ12:第 4 賽季只到 MJ-006


@pytest.mark.parametrize("number, season", [("Ex-100", 3), ("Ex-101", 3), ("Ex-099", 4)])
def test_special_assignment_outside_ranges(number, season):
    # DX赤い魔本附錄(第 3 賽季)、電撃フェスタ(第 4 賽季):編號不在任何賽季的 Ex 範圍內
    assert card_season(number) == season


@pytest.mark.parametrize("number, season", [
    ("PR-004", 2), ("PR-005", 3), ("PR-007", 3), ("PR-010", 3), ("PR-011", 4), ("PR-013", 4)])
def test_pr_seasons(number, season):
    assert card_season(number) == season


@pytest.mark.parametrize("number", ["M-070", "M-085", "S-146", "P-050", "E-054", "Ex-049", "Ex-074", "MJ-001", "MJ-006"])
def test_season4_cards(number):
    assert card_season(number) == 4


def test_preset_deck_seasons():
    assert [deck_season(_preset(n)) for n in ("level1", "level2", "gash-nakama", "zeon")] == [1, 2, 3, 3]


def test_deck_season_is_max_of_cards():
    pages = _preset("level1")
    assert deck_season(pages) == 1
    pages[20] = "M-030"
    assert deck_season(pages) == 2


def _level1_with(number, page=20):
    pages = _preset("level1")
    pages[page] = number
    return pages


def test_validate_rejects_card_beyond_season():
    pages = _level1_with("M-030")
    validate_deck(pages, card_db())                     # 本身是合法魔書
    with pytest.raises(DeckError) as exc:
        validate_deck(pages, card_db(), season=1)
    assert exc.value.code == "deck.season"


def test_validate_accepts_deck_within_season():
    validate_deck(_preset("level2"), card_db(), season=3)
    validate_deck(_preset("level2"), card_db(), season=2)


def test_validate_without_season_skips_check():
    validate_deck(_preset("zeon"), card_db())
