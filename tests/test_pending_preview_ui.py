"""尚未開放的卡:構築器顯示但不可加入魔書,金手指不顯示(deck-builder「卡池的尚未開放卡片」「產品篩選分排」「卡池排序」)。
需要 playwright 與 Chromium。

Run: python -m pytest tests/test_pending_preview_ui.py -q
"""
from tests.test_cheat_editor import open_local
from tests.test_pool_filters_ui import SEASON_ROWS, menu, open_builder, pick, pool_numbers, product_rows, tile_keys
from tests.test_pool_filters_ui import open_products


def level4_open() -> set[str]:
    import json

    from gash.engine.cards import DATA_DIR, pending_cards
    cards = json.loads((DATA_DIR / "cards.json").read_text(encoding="utf-8"))
    return {c["number"] for c in cards if "level-4" in c["sets"] and c["number"] not in pending_cards()}


PENDING_CARD = "M-070"   # 第 4 賽季,資料已收錄、效果尚未實作
OPEN_CARD = "M-001"


def pending_only_families() -> set[str]:
    """所有卡片(魔物、搭檔、戰術)都還在尚未開放清單的魔物家族(依資料計算,分批開放時不必改)。"""
    import json as _json

    from gash.engine.cards import DATA_DIR, pending_cards
    pend = pending_cards()
    fams: dict[str, set[bool]] = {}
    for c in _json.loads((DATA_DIR / "cards.json").read_text(encoding="utf-8")):
        if c.get("related_mamodo"):
            fams.setdefault(c["related_mamodo"], set()).add(c["number"] in pend)
    return {f for f, flags in fams.items() if flags == {True}}


def pool_card(page, num, grid="#pool-grid"):
    return page.locator(f'{grid} .card[aria-label^="{num} "]')


def pages(page):
    return page.evaluate("[...B.deck.pages]")


def test_builder_shows_pending_card_dimmed(browser, server):
    context, page, errors = open_builder(browser, server)
    card = pool_card(page, PENDING_CARD)
    assert card.count() == 1
    assert "pending" in card.get_attribute("class").split()
    label = page.evaluate("t('builder.pending')")
    assert label in card.get_attribute("aria-label") and label in card.inner_text()
    opened = pool_card(page, OPEN_CARD)
    assert "pending" not in opened.get_attribute("class").split()
    context.close()
    assert not errors


def test_pending_card_cannot_be_added(browser, server):
    context, page, errors = open_builder(browser, server)
    before = pages(page)
    pool_card(page, PENDING_CARD).click()
    assert pages(page) == before
    assert page.locator("#toast").inner_text() == page.evaluate("t('builder.pending_blocked')")
    pool_card(page, PENDING_CARD).focus()
    page.keyboard.press("Enter")
    assert pages(page) == before
    pool_card(page, PENDING_CARD).locator(".card-detail").click()            # 詳情照常放大檢視
    assert page.locator("#zoom-overlay").is_visible()
    assert page.evaluate("ZOOM.num") == PENDING_CARD and pages(page) == before
    context.close()
    assert not errors


def test_open_card_still_added(browser, server):
    context, page, errors = open_builder(browser, server)
    pool_card(page, OPEN_CARD).click()
    assert OPEN_CARD in pages(page)
    context.close()
    assert not errors


def test_builder_grids_include_pending_only_items(browser, server):
    context, page, errors = open_builder(browser, server)
    menu(page, "product").click()
    assert product_rows(page) == SEASON_ROWS                                   # LEVEL:4 等新產品也列出
    page.keyboard.press("Escape")
    menu(page, "mamodo").click()
    assert "ゴーレン" in tile_keys(page, "mamodo")                            # 只有尚未開放卡片的魔物家族
    page.keyboard.press("Escape")
    pick(page, "product", "level-4")
    numbers = pool_numbers(page)
    assert numbers and PENDING_CARD in numbers
    opened = page.locator("#pool-grid .card:not(.pending) .cnum").all_text_contents()
    # 已實作(不在尚未開放清單)的 LEVEL:4 卡照常可選
    assert set(opened) == level4_open()
    context.close()
    assert not errors


def test_cheat_pool_hides_pending(page):
    open_local(page)
    assert pool_card(page, PENDING_CARD, "#cheat-pool-grid").count() == 0
    assert pool_card(page, OPEN_CARD, "#cheat-pool-grid").count() == 1
    filters = page.locator("#cheat-filters")
    filters.locator(".filter-menu[data-group=product]").click()
    keys = filters.locator(".filter-panel[data-group=product] .filter-tile[data-key]").evaluate_all(
        "(ts) => ts.map((t) => t.dataset.key)")
    assert set(keys) == open_products()                                       # 只列有已開放卡片的產品
    filters.locator(".filter-menu[data-group=mamodo]").click()
    keys = filters.locator(".filter-panel[data-group=mamodo] .filter-tile[data-key]").evaluate_all(
        "(ts) => ts.map((t) => t.dataset.key)")
    hidden = pending_only_families()                                          # 只有尚未開放卡片的魔物家族
    assert hidden and not hidden & set(keys)


def test_mj12_sorted_after_events(browser, server):
    context, page, errors = open_builder(browser, server)
    order = page.locator("#pool-grid .card .cnum").all_text_contents()
    types = page.evaluate("(ns) => ns.map((n) => CARDS[n].type)", order)
    mj = [i for i, ty in enumerate(types) if ty == "mj12"]
    events = [i for i, ty in enumerate(types) if ty == "event" and order[i].startswith("E-")]   # Ex 事件排在最後
    assert len(mj) == 6 and min(mj) > max(events)
    assert [order[i] for i in mj] == [f"MJ-{n:03d}" for n in range(1, 7)]
    context.close()
    assert not errors
