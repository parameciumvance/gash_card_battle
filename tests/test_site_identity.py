"""網站名稱、標題字與網頁圖示(battle-ui「網站名稱與圖示」)。"""
import json
import re
from pathlib import Path

from fastapi.testclient import TestClient

from gash.api.app import app
from tests.test_cheat_editor import browser, server  # noqa: F401  共用 fixture(隔離的伺服器與瀏覽器)

ROOT = Path(__file__).resolve().parents[1]
NAME = "Gash Card Battle Online"
# 首頁標題字三行的墨色中心(以 canvas 量字形實際的左右邊界,含字距;不受字形左右留白與字尾字距影響)
INK_CENTERS = """async () => {
    await document.fonts.ready;
    return [...document.querySelectorAll('#landing-title .wm-text > span')].map((el) => {
        const cs = getComputedStyle(el);
        const c = document.createElement('canvas').getContext('2d');
        c.font = `${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
        c.letterSpacing = cs.letterSpacing;
        const m = c.measureText(el.textContent);
        const left = el.getBoundingClientRect().left + parseFloat(cs.paddingLeft);
        return left + (m.actualBoundingBoxRight - m.actualBoundingBoxLeft) / 2;
    });
}"""
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
    assert page.evaluate("document.fonts.check('700 20px \"Oswald Title\"')")
    centers = page.evaluate(INK_CENTERS)
    assert max(centers) - min(centers) <= 2, centers                      # 三行的墨色沿同一條中線置中
    assert page.title() == NAME
    context.close()


def test_topbar_wordmark_sits_on_one_baseline(browser, server):  # noqa: F811
    context = browser.new_context(viewport={"width": 1280, "height": 900}, locale="zh-TW")
    page = context.new_page()
    page.goto(server)
    page.wait_for_selector("#landing:not(.hidden)")
    page.evaluate("document.fonts.ready")
    bottoms = page.evaluate("""() => [...document.querySelectorAll('#title .wm-sub')]
        .map((el) => Math.round(el.getBoundingClientRect().bottom))""")
    assert len(bottoms) == 2 and bottoms[0] == bottoms[1]                 # CARD BATTLE 與 ONLINE 同一基線
    context.close()
