"""首頁對戰中人數的瀏覽器測試(battle-ui「首頁對戰中人數」)。
以 route 換成可控制的回應並記錄請求次數;以 Playwright 的假時鐘推進 30 秒的更新間隔。需要 playwright 與 Chromium。

Run: python -m pytest tests/test_online_count_ui.py -q
"""
import json

import pytest

from tests.test_cheat_editor import browser, server  # noqa: F401  共用 fixture(隔離的伺服器與瀏覽器)

LINE = "#landing-online"


class Online:
    """假的 /api/online:count 為 None 時回 500。"""

    def __init__(self, count=3):
        self.count = count
        self.calls = 0

    def handle(self, route):
        self.calls += 1
        if self.count is None:
            route.fulfill(status=500, body="error")
        else:
            route.fulfill(status=200, content_type="application/json", body=json.dumps({"count": self.count}))


def open_page(browser, server, online, *, locale="zh-TW"):  # noqa: F811
    context = browser.new_context(viewport={"width": 1280, "height": 900}, locale=locale)
    context.add_init_script("localStorage.setItem('gash-spotlight', 'off')")
    context.route("**/api/online", online.handle)
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.clock.install()
    page.goto(server)
    page.wait_for_function("Object.keys(CARDS).length > 0")
    page.wait_for_selector("#landing:not(.hidden)")
    return context, page, errors


@pytest.fixture
def online():
    return Online()


@pytest.fixture
def landing(browser, server, online):  # noqa: F811
    context, page, errors = open_page(browser, server, online)
    yield page
    context.close()
    assert not errors


def shown(page, text):
    page.wait_for_function(f"(t) => {{ const e = document.querySelector('{LINE}');"
                           " return !e.classList.contains('hidden') && e.textContent === t; }", arg=text)


def settle(page):
    page.wait_for_timeout(300)


def set_hidden(page, hidden):
    page.evaluate("""(hidden) => {
        Object.defineProperty(document, 'visibilityState', { value: hidden ? 'hidden' : 'visible', configurable: true });
        Object.defineProperty(document, 'hidden', { value: hidden, configurable: true });
        document.dispatchEvent(new Event('visibilitychange'));
    }""", hidden)


def test_shows_count_between_entries_and_disclaimer(landing):
    shown(landing, "目前 3 人對戰中")
    order = landing.evaluate(f"""() => {{
        const line = document.querySelector('{LINE}');
        const before = (a, b) => !!(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);
        return [before(document.querySelector('#landing-cards'), line),
                before(line, document.querySelector('#landing-disclaimer'))];
    }}""")
    assert order == [True, True]


def test_zero_shows_nobody(browser, server):  # noqa: F811
    context, page, errors = open_page(browser, server, Online(count=0))
    shown(page, "目前沒有人對戰")
    context.close()
    assert not errors


def test_refreshes_every_30_seconds(landing, online):
    shown(landing, "目前 3 人對戰中")
    calls = online.calls
    online.count = 5
    landing.clock.fast_forward(25_000)
    settle(landing)
    assert online.calls == calls
    landing.clock.fast_forward(5_000)
    shown(landing, "目前 5 人對戰中")
    assert online.calls == calls + 1


def test_refetches_when_returning_to_landing(landing, online):
    shown(landing, "目前 3 人對戰中")
    landing.locator("#entry-npc").click()
    calls = online.calls
    online.count = 7
    landing.locator("#setup-back").click()
    shown(landing, "目前 7 人對戰中")
    assert online.calls == calls + 1


def test_no_requests_after_leaving_landing(landing, online):
    shown(landing, "目前 3 人對戰中")
    landing.locator("#entry-friend").click()
    calls = online.calls
    landing.clock.fast_forward(95_000)
    settle(landing)
    assert online.calls == calls


def test_paused_while_hidden_and_refreshed_on_return(landing, online):
    shown(landing, "目前 3 人對戰中")
    calls = online.calls
    set_hidden(landing, True)
    landing.clock.fast_forward(95_000)
    settle(landing)
    assert online.calls == calls
    online.count = 4
    set_hidden(landing, False)
    shown(landing, "目前 4 人對戰中")
    assert online.calls == calls + 1


def test_failure_hides_line(landing, online):
    shown(landing, "目前 3 人對戰中")
    online.count = None
    landing.clock.fast_forward(30_000)
    landing.wait_for_selector(f"{LINE}.hidden", state="attached")
    assert not landing.locator(LINE).is_visible()


def test_japanese(browser, server):  # noqa: F811
    context, page, errors = open_page(browser, server, Online(count=3), locale="ja")
    shown(page, "現在 3 人が対戦中")
    context.close()
    assert not errors
