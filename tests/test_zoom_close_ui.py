"""放大檢視的關閉(battle-ui「放大檢視的關閉」):右上角的「×」、Esc 只關最上層、點背景照舊關閉。

需要 playwright 與 Chromium。

Run: python -m pytest tests/test_zoom_close_ui.py -q
"""
from tests.test_builder_card_info_ui import PHONE, builder  # noqa: F401
from tests.test_card_action_menu_ui import page_card, to_battle

ZOOM = "#zoom-overlay:not(.hidden)"
CLOSE = "#zoom-close"
DIALOG = "#dialog-overlay:not(.hidden)"


def open_zoom(page):
    tp, me = to_battle(page)
    page_card(page, me, 2).click()                                        # S-025:選單「防禦」(停用)與「詳情」
    page.locator("#card-menu button", has_text="詳情").click()
    page.wait_for_selector(ZOOM)
    return tp, me


def zoom_open(page):
    return page.locator(ZOOM).count() == 1


def hittable(page):
    """「×」的中心點命中按鈕本身(沒有被裁掉或被其他元素蓋住)。"""
    return page.evaluate("""() => {
        const b = document.getElementById('zoom-close').getBoundingClientRect();
        return document.elementFromPoint(b.x + b.width / 2, b.y + b.height / 2)?.id === 'zoom-close';
    }""")


def test_close_button(page):
    open_zoom(page)
    btn = page.locator(CLOSE)
    assert btn.is_visible()
    box = btn.bounding_box()
    assert box["width"] >= 44 and box["height"] >= 44
    assert btn.get_attribute("aria-label") == "關閉"
    before = page.evaluate("S.event_count")
    btn.click()
    assert not zoom_open(page)
    assert page.evaluate("S.event_count") == before                       # 盤面不變


def test_close_button_label_follows_language(page):
    page.evaluate("localStorage.setItem(LANG_KEY, 'en')")
    page.reload()
    page.wait_for_function("Object.keys(CARDS).length > 0")
    page.evaluate("zoom('S-001')")
    page.wait_for_selector(ZOOM)
    assert page.locator(CLOSE).get_attribute("aria-label") == "Close"


def test_escape_closes(page):
    open_zoom(page)
    page.keyboard.press("Escape")
    assert not zoom_open(page)


def test_escape_closes_only_top_layer(page):
    tp, me = to_battle(page)
    page.evaluate("(p) => { S.players[p].discard = ['S-029', 'P-011']; render(); showDiscard(p); }", me)
    page.wait_for_selector(DIALOG)
    page.locator("#dialog-overlay .card").first.click()                   # 棄牌區的卡:沒有行動,直接放大
    page.wait_for_selector(ZOOM)
    page.keyboard.press("Escape")
    assert not zoom_open(page)
    assert page.locator(DIALOG).count() == 1                              # 棄牌區視窗還開著
    page.keyboard.press("Escape")
    assert page.locator(DIALOG).count() == 0


def test_escape_does_not_reset_book_browse(page):
    tp, me = to_battle(page)
    page.keyboard.press("ArrowRight")                                     # 魔書翻閱往後一個對頁
    browse = page.evaluate(f"BOOK_BROWSE[{me}]")
    assert browse is not None
    page.evaluate("zoom('S-001')")
    page.wait_for_selector(ZOOM)
    page.keyboard.press("Escape")
    assert not zoom_open(page)
    assert page.evaluate(f"BOOK_BROWSE[{me}]") == browse                  # 沒有被 Esc 拉回目前頁


def test_background_click_still_closes(page):
    open_zoom(page)
    page.mouse.click(5, 450)
    assert not zoom_open(page)


def test_close_button_next_to_card_top_right(page):
    open_zoom(page)
    btn = page.locator(CLOSE).bounding_box()
    card = page.locator("#zoom-card .card").bounding_box()
    assert 0 <= btn["x"] - (card["x"] + card["width"]) <= 16              # 卡面右緣外側
    assert abs(btn["y"] - card["y"]) <= 2                                 # 與卡面上緣對齊
    assert hittable(page)


def test_close_button_clear_of_card_on_phone(page):
    page.set_viewport_size(PHONE)
    open_zoom(page)
    btn = page.locator(CLOSE).bounding_box()
    card = page.locator("#zoom-card .card").bounding_box()
    overlap_x = btn["x"] < card["x"] + card["width"] and card["x"] < btn["x"] + btn["width"]
    overlap_y = btn["y"] < card["y"] + card["height"] and card["y"] < btn["y"] + btn["height"]
    assert not (overlap_x and overlap_y)
    assert btn["x"] + btn["width"] <= PHONE["width"] and btn["y"] >= 0
    assert hittable(page)
    assert btn["y"] + btn["height"] <= card["y"] and btn["x"] + btn["width"] - (card["x"] + card["width"]) <= 2   # 卡面右上角正上方
    page.locator(CLOSE).click()
    assert not zoom_open(page)


def test_builder_detail_close(builder):  # noqa: F811
    before = builder.evaluate("[...B.deck.pages]")
    card = builder.locator("#pool-grid .card", has=builder.locator(".cnum", has_text="S-005")).first
    card.locator(".card-detail").click()
    builder.wait_for_selector(ZOOM)
    builder.locator(CLOSE).click()
    assert builder.locator(ZOOM).count() == 0
    card.locator(".card-detail").click()
    builder.wait_for_selector(ZOOM)
    builder.keyboard.press("Escape")
    assert builder.locator(ZOOM).count() == 0
    assert builder.evaluate("[...B.deck.pages]") == before
