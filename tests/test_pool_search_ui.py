"""卡池文字搜尋(deck-builder「卡池文字搜尋」):構築器與金手指的卡池。需要 playwright 與 Chromium。

Run: python -m pytest tests/test_pool_search_ui.py -q
"""
import pytest

from tests.test_cheat_editor import open_local
from tests.test_pool_filters_ui import DESKTOP, cards_where, open_builder, pool_numbers, type_badge

SEARCH = "#pool-filters .pool-search"


@pytest.fixture
def builder(browser, server):  # noqa: F811
    context, page, errors = open_builder(browser, server)
    yield page
    context.close()
    assert not errors


def search(page, text, box=SEARCH):
    page.locator(box).fill(text)


def matches(page, expr):
    """卡池中符合 JS 條件(c 為卡片資料、z 為目前語言的文字)的卡號,排序後(同 pool_numbers)。"""
    return sorted(page.evaluate(f"""() => [...document.querySelectorAll('#pool-grid .card .cnum')].map(e => e.textContent)
        .filter(n => {{ const c = CARDS[n], z = TEXT[n] || {{}}; return {expr}; }})"""))


def test_search_by_chinese_name(builder):
    search(builder, "薩喀爾")
    numbers = pool_numbers(builder)
    assert "S-001" in numbers                                               # 卡名
    # 其餘的卡是卡名或效果文提到「薩喀爾」(如 M-029 的效果文)
    assert numbers == matches(builder, "(z.name || '').includes('薩喀爾') || (z.effect || '').includes('薩喀爾')")
    assert len(numbers) < len(builder.evaluate("Object.keys(CARDS)"))


@pytest.mark.parametrize("text", ["ザケルガ", "S-092", "s092", "Ｓ－０９２"])
def test_search_by_japanese_name_and_number(builder, text):
    search(builder, text)
    assert "S-092" in pool_numbers(builder)
    assert "S-001" not in pool_numbers(builder)                             # ザケル 不含「ザケルガ」、卡號也不同


def test_search_by_effect_text(builder):
    search(builder, "保護")
    numbers = pool_numbers(builder)
    assert numbers and all("保護" in builder.evaluate(f"(TEXT['{n}'] || {{}}).effect || ''") for n in numbers
                           if "保護" not in builder.evaluate(f"cname('{n}')"))


def test_search_combines_with_type_filter_and_clears(builder):
    type_badge(builder, "spell").click()
    spells = pool_numbers(builder)
    search(builder, "ザケル")                                                # 日文原名含ザケル的戰術
    numbers = pool_numbers(builder)
    assert numbers and set(numbers) <= set(spells)                          # 同時符合類型與搜尋
    assert len(numbers) < len(spells)
    search(builder, "")
    assert pool_numbers(builder) == spells                                  # 清空回到只有類型篩選


def test_search_does_not_change_book(builder):
    before = builder.evaluate("[...B.deck.pages]")
    search(builder, "S-005")
    assert pool_numbers(builder) == ["S-005"]
    assert builder.evaluate("[...B.deck.pages]") == before


def test_escape_clears_search(builder):
    search(builder, "S-005")
    builder.locator(SEARCH).press("Escape")
    assert builder.locator(SEARCH).input_value() == ""
    assert len(pool_numbers(builder)) > 1


@pytest.mark.parametrize("lang,placeholder", [("zh-TW", "搜尋卡名、卡號、效果"), ("ja", "カード名・番号・効果で検索"),
                                              ("en", "Search name, number, effect")])
def test_placeholder_per_language(browser, server, lang, placeholder):  # noqa: F811
    context, page, errors = open_builder(browser, server, locale=lang)
    box = page.locator(SEARCH)
    assert box.get_attribute("placeholder") == placeholder
    assert box.get_attribute("aria-label") == placeholder
    context.close()


def test_cheat_pool_search(page):
    open_local(page)
    box = "#cheat-filters .pool-search"
    search(page, "S-005", box)
    page.wait_for_function("document.querySelectorAll('#cheat-pool-grid .card').length === 1")
    assert page.locator("#cheat-pool-grid .cnum").all_text_contents() == ["S-005"]
    page.locator(box).press("Escape")                                      # 清空,不關閉金手指視窗
    assert page.locator("#cheat-panel").evaluate("d => d.open")
    assert len(page.locator("#cheat-pool-grid .cnum").all_text_contents()) > 1
