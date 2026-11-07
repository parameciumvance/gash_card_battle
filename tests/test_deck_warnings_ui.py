"""構築器的魔書組合提醒(deck-builder「魔書組合的提醒」)。需要 playwright 與 Chromium。

Run: python -m pytest tests/test_deck_warnings_ui.py -q
"""
import json
from pathlib import Path

from tests.test_builder_card_info_ui import builder  # noqa: F401

ROOT = Path(__file__).resolve().parent.parent

WARN = "#builder-validation .warn"


def set_book(page, pages):
    """魔書換成只有指定的頁:{頁碼: 卡號},其餘為空頁。"""
    page.evaluate("""(pages) => {
      B.deck.pages = Array(32).fill(null);
      for (const [p, c] of Object.entries(pages)) B.deck.pages[p - 1] = c;
      builderMutated();
    }""", {str(k): v for k, v in pages.items()})


def warnings(page):
    return page.locator(WARN).all_text_contents()


def test_spell_without_user_then_add_mamodo(builder):  # noqa: F811
    set_book(builder, {1: "M-004", 5: "S-001"})
    builder.wait_for_selector(WARN)
    assert warnings(builder) == ["薩喀爾(第 5 頁):魔書中沒有能使用的魔物"]
    set_book(builder, {1: "M-001", 5: "S-001"})
    builder.wait_for_function(f"!document.querySelector('{WARN}')")


def test_partner_without_mamodo(builder):  # noqa: F811
    set_book(builder, {1: "M-004", 8: "P-001"})
    builder.wait_for_selector(WARN)
    name = builder.evaluate("cname('P-001')")
    assert warnings(builder) == [f"{name}(第 8 頁):魔書中沒有對應的魔物"]


def test_warning_style_differs_from_errors(builder):  # noqa: F811
    set_book(builder, {1: "M-004", 5: "S-001"})                           # 也有構築違規(未滿 32 頁等)
    builder.wait_for_selector(WARN)
    assert builder.locator("#builder-validation .err").count() >= 1
    err = builder.locator("#builder-validation .err").first.evaluate("e => getComputedStyle(e).color")
    warn = builder.locator(WARN).first.evaluate("e => getComputedStyle(e).color")
    assert err != warn


def test_legal_book_with_warning_still_valid(builder):  # noqa: F811
    # 合法的預組魔書(level1),第 5 頁換成ブラゴ的戰術 S-008(預組沒有ブラゴ):仍顯示合法,另有提醒
    pages = json.loads((ROOT / "data/decks/level1.json").read_text(encoding="utf-8"))["pages"]
    assert pages[4] == "S-001"
    pages[4] = "S-008"
    set_book(builder, {i + 1: c for i, c in enumerate(pages)})
    builder.wait_for_selector(WARN)
    assert builder.locator("#builder-validation .ok").count() == 1
    assert builder.locator("#builder-validation .err").count() == 0
    name = builder.evaluate("cname('S-008')")
    assert warnings(builder) == [f"{name}(第 5 頁):魔書中沒有能使用的魔物"]
