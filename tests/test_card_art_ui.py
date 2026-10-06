"""卡圖網址(battle-ui「卡圖網址」):卡片元件、聚焦展示、規則頁只請求 {卡號}.webp。
在瀏覽器端攔截卡圖請求,不依賴本機下載了哪些卡圖。需要 playwright 與 Chromium。

Run: python -m pytest tests/test_card_art_ui.py -q
"""
import io
from urllib.parse import urlparse

import pytest
from PIL import Image

from tests.test_cheat_editor import browser, pw, server  # noqa: F401  共用 fixture(隔離的伺服器與瀏覽器)
from tests.test_spotlight_ui import SPOT, send, start_as


def webp_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGBA", (465, 679), (40, 40, 40, 255)).save(buf, "WEBP")
    return buf.getvalue()


def open_with_art(browser, server, *, installed, spotlight="off"):  # noqa: F811
    """installed="webp":只有 .webp 取得到;"jpg":只裝了舊格式。回傳 (context, page, 請求過的卡圖路徑)。"""
    context = browser.new_context(viewport={"width": 1280, "height": 900}, reduced_motion="reduce", locale="zh-TW")
    context.add_init_script(f"localStorage.setItem('gash-spotlight', '{spotlight}')")
    requested = []
    body = webp_bytes()

    def handle(route):
        path = urlparse(route.request.url).path
        requested.append(path)
        if path.endswith(f".{installed}"):
            route.fulfill(status=200, content_type="image/webp", body=body)
        else:
            route.fulfill(status=404)

    context.route("**/static/assets/cards/**", handle)
    page = context.new_page()
    page.goto(server)
    page.wait_for_function("Object.keys(CARDS).length > 0")
    return context, page, requested


@pytest.fixture
def webp_page(browser, server):  # noqa: F811
    context, page, requested = open_with_art(browser, server, installed="webp")
    yield page, requested
    context.close()


def test_card_component_requests_webp(webp_page):
    page, requested = webp_page
    page.evaluate("zoom('S-001')")
    img = page.locator("#zoom-card img")
    pw.expect(img).to_have_attribute("src", "/static/assets/cards/S-001.webp")
    page.wait_for_function("document.querySelector('#zoom-card img').naturalWidth > 0")
    assert requested and all(p.endswith(".webp") for p in requested)


def test_rules_page_requests_webp(webp_page):
    page, requested = webp_page
    page.evaluate("openRules('icons')")
    page.wait_for_function("document.querySelectorAll('#rules-body .icon-crop').length >= 5")
    srcs = page.locator("#rules-body .rules-figure img").evaluate_all("els => els.map(e => e.getAttribute('src'))")
    assert srcs and all(s.startswith("/static/assets/cards/") and s.endswith(".webp") for s in srcs)
    crops = page.locator("#rules-body .icon-crop").evaluate_all("els => els.map(e => e.style.backgroundImage)")
    assert all(".webp" in c for c in crops)
    assert requested and all(p.endswith(".webp") for p in requested)


def test_spotlight_requests_webp(browser, server):  # noqa: F811
    context, page, requested = open_with_art(browser, server, installed="webp", spotlight="normal")
    try:
        opp = start_as(page, "defender")
        send(page, opp, {"type": "flip_pages", "count": 0})
        send(page, opp, {"type": "declare_attack", "page": 3})          # S-001
        page.wait_for_selector(SPOT)
        assert page.locator("#spotlight .spot-art").get_attribute("src") == "/static/assets/cards/S-001.webp"
        assert all(p.endswith(".webp") for p in requested)
    finally:
        context.close()


def test_old_jpg_only_shows_card_back(browser, server):  # noqa: F811
    context, page, requested = open_with_art(browser, server, installed="jpg")
    try:
        page.evaluate("zoom('S-001')")
        pw.expect(page.locator("#zoom-card img")).to_have_attribute("src", "/static/back.jpg")
        assert "/static/assets/cards/S-001.webp" in requested
        assert not any(p.endswith(".jpg") for p in requested)               # 不改請求舊格式
    finally:
        context.close()
