"""網站名稱、標題字與網頁圖示(battle-ui「網站名稱與圖示」)。"""
import json
import re
from pathlib import Path

from fastapi.testclient import TestClient

from gash.api.app import app
from tests.test_cheat_editor import browser, server  # noqa: F401  共用 fixture(隔離的伺服器與瀏覽器)

ROOT = Path(__file__).resolve().parents[1]
NAME = "Gash Card Battle Online"
INDEX = (ROOT / "frontend/index.html").read_text(encoding="utf-8")


def test_name_is_the_same_in_every_language():
    for lang in ("zh-TW", "zh-CN", "en", "ja"):
        d = json.loads((ROOT / f"frontend/i18n/{lang}.json").read_text(encoding="utf-8"))
        assert d["app.title"] == NAME, lang
    assert re.search(r"<title>(.*?)</title>", INDEX).group(1) == NAME


def test_favicon_is_linked_and_served():
    link = re.search(r'<link rel="icon"[^>]*>', INDEX)
    assert link and 'href="/static/favicon.svg"' in link.group(0) and 'type="image/svg+xml"' in link.group(0)
    res = TestClient(app).get("/static/favicon.svg")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("image/svg+xml")
    assert "<circle" in res.text                                          # 五圓紋


def test_title_font_is_self_hosted_with_license():
    client = TestClient(app)
    res = client.get("/static/fonts/oswald-title.woff2")
    assert res.status_code == 200 and res.content[:4] == b"wOF2"
    assert "SIL Open Font License" in (ROOT / "frontend/fonts/OFL-Oswald.txt").read_text(encoding="utf-8")
    assert "fonts.googleapis.com" not in INDEX                           # 不向第三方請求字型


def test_landing_wordmark(browser, server):  # noqa: F811
    context = browser.new_context(viewport={"width": 1280, "height": 900}, locale="ja")
    page = context.new_page()
    page.goto(server)
    page.wait_for_selector("#landing:not(.hidden)")
    title = page.locator("#landing-title")
    assert title.get_attribute("aria-label") == NAME
    assert title.locator(".wm-text > span").all_text_contents() == ["GASH", "CARD BATTLE", "ONLINE"]
    assert title.locator(".wm-badge").get_attribute("src") == "/static/favicon.svg"   # 徽章與網頁圖示相同
    centers = page.evaluate("""() => ['.wm-text', '.wm-online'].map((s) => {
        const r = document.querySelector('#landing-title ' + s).getBoundingClientRect();
        return r.left + r.width / 2; })""")
    assert abs(centers[0] - centers[1]) <= 2                              # ONLINE 置中
    assert page.evaluate("document.fonts.check('700 20px \"Oswald Title\"')")
    assert page.title() == NAME
    context.close()
