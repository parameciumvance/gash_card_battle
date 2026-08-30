import pytest

from gash.engine.cards import DATA_DIR, card_db
from gash.engine.deck import DeckError, load_deck, validate_deck


def test_card_db_has_135_cards():
    db = card_db()
    assert len(db) == 135  # Level 1 67 + Level 2 67 + S-042
    assert db["M-001"].power_base == 4000
    assert db["S-001"].power_bonus == 2000 and db["S-001"].damage == 1
    assert db["S-005"].klass == "superior" and db["S-005"].cost == 6
    # S-025 為擲 1 次硬幣版本(非「2回」)
    assert "コイン" in db["S-025"].effect_en
    assert "2回" not in db["S-025"].effect_en
    # E-018 含連續回合限制條款
    assert "直前のターン" in db["E-018"].effect_en
    # E-022 限本回合入墓
    assert "このターン中" in db["E-022"].effect_en


def test_level1_deck_is_valid():
    db = card_db()
    deck = load_deck(DATA_DIR / "decks/level1.json", db)
    assert len(deck.pages) == 32
    assert deck.pages[0] == "M-001"
    assert deck.pages[31] == "S-005"


def test_invalid_first_page_rejected():
    db = card_db()
    pages = ["S-001"] + ["M-001"] + ["S-001"] * 29 + ["S-002"]
    with pytest.raises(DeckError) as exc:
        validate_deck(pages, db)
    assert exc.value.code in ("deck.first_page", "deck.max_copies")


def test_max_copies_rejected():
    db = card_db()
    deck = load_deck(DATA_DIR / "decks/level1.json", db)
    pages = list(deck.pages)
    # 把 5 個非 S-001 的頁換成 S-001(原本已有 3 張 → 超過 4)
    replaced = 0
    for i in range(1, 31):
        if pages[i] != "S-001" and replaced < 2:
            pages[i] = "S-001"
            replaced += 1
    with pytest.raises(DeckError) as exc:
        validate_deck(pages, db)
    assert exc.value.code == "deck.max_copies"


def test_superior_page_restriction():
    db = card_db()
    deck = load_deck(DATA_DIR / "decks/level1.json", db)
    pages = list(deck.pages)
    pages[2], pages[31] = pages[31], pages[2]  # 把 S-005 移到第 3 頁
    with pytest.raises(DeckError) as exc:
        validate_deck(pages, db)
    assert exc.value.code in ("deck.superior_page", "deck.last_page")
