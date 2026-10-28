"""卡池圖示篩選的瀏覽器測試(deck-builder「卡池圖示篩選列」「卡池篩選的選取方式」「卡池篩選的對應魔物」
「魔物篩選圖示與順序」「產品篩選分排」「篩選圖示缺圖退回文字」)。金手指共用同一套篩選,見 test_cheat_editor.py。
需要 playwright 與 Chromium。

Run: python -m pytest tests/test_pool_filters_ui.py -q
"""
import json

import pytest

DESKTOP = {"width": 1280, "height": 900}
PHONE = {"width": 390, "height": 844}
FILTERS = "#pool-filters"


def open_builder(browser, server, viewport=DESKTOP, routes=(), locale="zh-TW"):
    context = browser.new_context(viewport=viewport, reduced_motion="reduce", locale=locale)
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    for pattern, handler in routes:
        page.route(pattern, handler)
    page.goto(server + "/?builder=1")
    page.wait_for_function("Object.keys(CARDS).length > 0 && document.querySelector('#pool-grid .card')")
    return context, page, errors


@pytest.fixture
def builder(browser, server):  # noqa: F811
    context, page, errors = open_builder(browser, server)
    yield page
    context.close()
    assert not errors


def type_badge(page, ty):
    return page.locator(f"{FILTERS} .filter-type[data-type={ty}]")


def menu(page, group):
    return page.locator(f"{FILTERS} .filter-menu[data-group={group}]")


def panel(page, group):
    return page.locator(f"{FILTERS} .filter-panel[data-group={group}]")


def tile(page, group, key):
    return panel(page, group).locator(f".filter-tile[data-key='{key}']")


def pick(page, group, key):
    """展開網格、點選項目(單選,點選後網格收起)。"""
    menu(page, group).click()
    tile(page, group, key).click()


def pool_numbers(page):
    return sorted(page.locator("#pool-grid .card .cnum").all_text_contents())


def cards_where(page, expr):
    return page.evaluate(f"openCards().filter((c) => {expr}).map((c) => c.number).sort()")


def tile_keys(page, group):
    return panel(page, group).locator(".filter-tile[data-key]").evaluate_all("(ts) => ts.map((t) => t.dataset.key)")


# ---------------------------------------------------------------- 類型多選、魔物與產品單選、跨組

def test_type_multi_select(builder):
    type_badge(builder, "spell").click()
    type_badge(builder, "partner").click()
    assert pool_numbers(builder) == cards_where(builder, "c.type === 'spell' || c.type === 'partner'")
    type_badge(builder, "partner").click()
    assert type_badge(builder, "partner").get_attribute("aria-pressed") == "false"
    assert pool_numbers(builder) == cards_where(builder, "c.type === 'spell'")


def test_mamodo_single_select_and_summary(builder):
    pick(builder, "mamodo", "ガッシュ・ベル")
    assert not panel(builder, "mamodo").is_visible()                         # 選了就收起
    pick(builder, "mamodo", "ティオ")                                         # 改選取代原本的選取
    assert pool_numbers(builder) == cards_where(builder, "c.related_mamodo === 'ティオ'")
    summary = menu(builder, "mamodo").locator(".filter-summary")
    name = builder.evaluate("mamodoFilterItems().find((it) => it.key === 'ティオ').label")
    assert summary.locator(".filter-caption").inner_text() == name            # 圖示旁有名稱
    assert summary.locator(".mamodo-icon .filter-crop").count() == 1
    assert menu(builder, "mamodo").get_attribute("aria-label").endswith(name)
    menu(builder, "mamodo").click()
    assert tile(builder, "mamodo", "ティオ").get_attribute("aria-pressed") == "true"
    assert tile(builder, "mamodo", "ガッシュ・ベル").get_attribute("aria-pressed") == "false"
    panel(builder, "mamodo").locator(".filter-all").click()                   # 「全部」清除選取
    assert menu(builder, "mamodo").locator(".filter-summary").inner_text() == "全部"
    assert len(pool_numbers(builder)) == len(cards_where(builder, "true"))


def test_product_single_select(builder):
    pick(builder, "product", "level-1")
    pick(builder, "product", "level-2")
    assert pool_numbers(builder) == cards_where(builder, "c.sets.includes('level-2')")
    summary = menu(builder, "product").locator(".filter-summary")
    assert summary.locator(".filter-caption").inner_text() == builder.evaluate("t('product.level-2')")


def test_groups_combine_with_and(builder):
    type_badge(builder, "spell").click()
    pick(builder, "mamodo", "ガッシュ・ベル")
    pick(builder, "product", "level-1")
    expected = cards_where(builder, "c.type === 'spell' && c.related_mamodo === 'ガッシュ・ベル' && c.sets.includes('level-1')")
    assert expected and pool_numbers(builder) == expected


def test_filters_do_not_touch_book(builder):
    builder.evaluate("B.deck.pages[0] = 'M-001'; builderMutated()")
    type_badge(builder, "event").click()
    pick(builder, "product", "level-2")
    assert builder.evaluate("B.deck.pages[0]") == "M-001"


def test_pool_order_mamodo_partner_spell_event(builder):
    numbers = builder.locator("#pool-grid .card .cnum").all_text_contents()
    prefixes = [n[0] for n in numbers]
    assert prefixes == sorted(prefixes, key="MPSE".index)                  # 事件在最後
    assert numbers[0] == "M-001" and numbers[-1].startswith("E-")
    for p in "MPSE":
        group = [n for n in numbers if n[0] == p]
        assert group == sorted(group)                                       # 同類型依卡號


# ---------------------------------------------------------------- 對應魔物「無」與事件

def test_mamodo_none_shows_command_spells(builder):
    pick(builder, "mamodo", "__none__")
    expected = cards_where(builder, "c.type === 'spell' && c.related_mamodo === 'コマンド'")
    assert expected and pool_numbers(builder) == expected


def test_mamodo_none_combines_with_product(builder):
    code = builder.evaluate("openCards().find((c) => c.related_mamodo === 'コマンド').sets[0]")
    pick(builder, "mamodo", "__none__")
    pick(builder, "product", code)
    expected = cards_where(builder, f"c.related_mamodo === 'コマンド' && c.sets.includes('{code}')")
    assert expected and pool_numbers(builder) == expected


def test_event_only_pauses_mamodo_filter(builder):
    pick(builder, "mamodo", "ガッシュ・ベル")
    type_badge(builder, "event").click()
    assert menu(builder, "mamodo").is_disabled()
    assert builder.evaluate("B.fmamodo") == "ガッシュ・ベル"                  # 保留原本的選取
    assert pool_numbers(builder) == cards_where(builder, "c.type === 'event'")
    type_badge(builder, "event").click()
    assert not menu(builder, "mamodo").is_disabled()
    assert pool_numbers(builder) == cards_where(builder, "filterFamily(c.related_mamodo) === 'ガッシュ・ベル'")


def test_event_only_ignores_mamodo_none(builder):
    pick(builder, "mamodo", "__none__")
    type_badge(builder, "event").click()
    assert pool_numbers(builder) == cards_where(builder, "c.type === 'event'")


def test_events_hidden_when_mamodo_picked_with_other_types(builder):
    pick(builder, "mamodo", "ガッシュ・ベル")
    type_badge(builder, "spell").click()
    type_badge(builder, "event").click()
    assert not menu(builder, "mamodo").is_disabled()
    assert pool_numbers(builder) == cards_where(builder, "c.type === 'spell' && c.related_mamodo === 'ガッシュ・ベル'")


# ---------------------------------------------------------------- 網格內容與順序

def test_product_rows_skip_reprints(builder):
    menu(builder, "product").click()
    rows = panel(builder, "product").locator(".filter-row").evaluate_all(
        "(rows) => rows.map((r) => [...r.querySelectorAll('.filter-tile')].map((t) => t.dataset.key))")
    assert rows == [["level-1"], ["level-2", "mahon-file"], ["level-3", "cardset-gash-nakama", "cardset-zeon"]]
    captions = panel(builder, "product").locator(".filter-caption").all_text_contents()
    assert captions[0] == builder.evaluate("t('product.level-1')")


def test_product_names_follow_language(browser, server):
    context, page, errors = open_builder(browser, server, locale="en")
    page.wait_for_function("document.documentElement.lang === 'en'")
    menu(page, "product").click()
    en = json.loads(open("frontend/i18n/en.json", encoding="utf-8").read())
    assert panel(page, "product").locator(".filter-caption").first.inner_text() == en["product.level-1"]
    context.close()
    assert not errors


def test_mamodo_tiles_use_representative_art(builder):
    menu(builder, "mamodo").click()
    keys = tile_keys(builder, "mamodo")
    assert keys[0] == "__none__"
    families = builder.evaluate("[...new Set(openCards().map((c) => c.related_mamodo))]"
                                ".filter((m) => m && m !== 'コマンド' && m !== '金色のガッシュベル')")
    assert sorted(keys[1:]) == sorted(families)
    crop = tile(builder, "mamodo", "ブラゴ").locator(".filter-crop")
    crop.wait_for()
    assert "/M-005.webp" in crop.evaluate("(e) => e.style.backgroundImage")


def test_merged_family_and_plain_labels(builder):
    menu(builder, "mamodo").click()
    assert "金色のガッシュベル" not in tile_keys(builder, "mamodo")
    assert tile(builder, "mamodo", "ロブノス").inner_text() == "羅布諾斯"          # 去掉「(分身體)」
    assert tile(builder, "mamodo", "バルトロ").inner_text() == "巴爾多羅"          # 去掉「(鎧甲體)」
    tile(builder, "mamodo", "ガッシュ・ベル").click()
    numbers = pool_numbers(builder)
    assert "M-047" in numbers                                                # 金色のガッシュベル併入ガッシュ・ベル
    assert numbers == cards_where(builder, "['ガッシュ・ベル', '金色のガッシュベル'].includes(c.related_mamodo)")


def test_mamodo_order_follows_config(browser, server):
    config = json.loads(open("frontend/pool-filters.json", encoding="utf-8").read())
    config["mamodo"] = ["ティオ", "ガッシュ・ベル"]                   # 沒列出的家族接在後面

    def serve(route):
        route.fulfill(content_type="application/json", body=json.dumps(config))

    context, page, errors = open_builder(browser, server, routes=[("**/static/pool-filters.json", serve)])
    menu(page, "mamodo").click()
    keys = tile_keys(page, "mamodo")
    assert keys[:4] == ["__none__", "ティオ", "ガッシュ・ベル", "レイコム"]   # レイコム 為下一個代表卡卡號
    context.close()
    assert not errors


# ---------------------------------------------------------------- 缺圖退回文字

def test_missing_art_falls_back_to_text(browser, server):
    context, page, errors = open_builder(
        browser, server, routes=[("**/static/assets/cards/*", lambda route: route.abort())])
    page.wait_for_timeout(300)
    marks = page.locator(f"{FILTERS} .filter-type .type-icon").all_text_contents()
    assert marks == ["魔", "使", "術", "鍵"]
    menu(page, "mamodo").click()
    blago = tile(page, "mamodo", "ブラゴ")
    assert blago.locator(".filter-crop").count() == 0
    assert blago.inner_text() == page.evaluate("TEXT['M-005'].name")
    blago.click()
    assert pool_numbers(page) == cards_where(page, "c.related_mamodo === 'ブラゴ'")
    context.close()
    assert not errors


def test_missing_product_image_shows_name(browser, server):
    context, page, errors = open_builder(
        browser, server, routes=[("**/static/products/cardset-zeon.webp", lambda route: route.abort())])
    menu(page, "product").click()
    zeon = tile(page, "product", "cardset-zeon")
    page.wait_for_function("!document.querySelector(\"#pool-filters [data-key='cardset-zeon'] img\")")
    assert zeon.locator(".filter-caption").inner_text() == page.evaluate("t('product.cardset-zeon')")
    assert tile(page, "product", "level-1").locator("img").count() == 1          # 其他產品圖不受影響
    zeon.click()
    assert pool_numbers(page) == cards_where(page, "c.sets.includes('cardset-zeon')")
    context.close()
    assert not errors


# ---------------------------------------------------------------- 展開、收起與鍵盤

def test_only_one_panel_open(builder):
    menu(builder, "mamodo").click()
    assert panel(builder, "mamodo").is_visible()
    menu(builder, "product").click()
    assert panel(builder, "product").is_visible() and not panel(builder, "mamodo").is_visible()
    assert menu(builder, "mamodo").get_attribute("aria-expanded") == "false"


def test_click_outside_and_escape_close(builder):
    menu(builder, "mamodo").click()
    builder.locator("#book-hint").click()
    assert not panel(builder, "mamodo").is_visible()
    menu(builder, "product").click()
    builder.keyboard.press("Escape")
    assert not panel(builder, "product").is_visible()
    assert builder.evaluate("document.activeElement.dataset.group") == "product"


def test_icons_have_text_labels(builder):
    labels = builder.locator(f"{FILTERS} .filter-type .filter-label").all_text_contents()
    assert labels == ["魔物", "搭檔", "戰術", "事件"]
    menu(builder, "mamodo").click()
    blago = tile(builder, "mamodo", "ブラゴ")
    blago.locator(".filter-crop").wait_for()
    assert blago.locator(".filter-caption").inner_text() == builder.evaluate("TEXT['M-005'].name")
    menu(builder, "product").click()
    level1 = tile(builder, "product", "level-1")
    assert level1.locator("img").evaluate("(img) => img.complete && img.naturalWidth > 0")
    assert level1.locator(".filter-caption").inner_text() == builder.evaluate("t('product.level-1')")


def test_keyboard_toggles_type(builder):
    type_badge(builder, "spell").focus()
    builder.keyboard.press("Enter")
    assert type_badge(builder, "spell").get_attribute("aria-pressed") == "true"
    assert type_badge(builder, "spell").get_attribute("aria-label") == "戰術"
    assert pool_numbers(builder) == cards_where(builder, "c.type === 'spell'")


def test_phone_filter_bar_is_one_line(browser, server):
    context, page, errors = open_builder(browser, server, viewport=PHONE)
    tops = page.locator(f"{FILTERS} .filter-bar > button").evaluate_all(
        "(bs) => bs.map((b) => Math.round(b.getBoundingClientRect().top))")
    assert len(tops) == 6 and len(set(tops)) == 1
    menu(page, "mamodo").click()
    assert panel(page, "mamodo").is_visible()
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    context.close()
    assert not errors
