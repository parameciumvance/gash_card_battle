"""窄螢幕行動記錄抽屜與查閱魔書位置的瀏覽器測試(battle-ui「行動記錄」「查閱己方魔書」)。
需要 playwright 與 Chromium。

Run: python -m pytest tests/test_mobile_log_book_ui.py -q
"""
import pytest

from tests.test_cheat_editor import browser, server  # noqa: F401  共用 fixture(隔離的伺服器與瀏覽器)


@pytest.fixture
def phone(browser, server):  # noqa: F811
    context = browser.new_context(viewport={"width": 390, "height": 844}, reduced_motion="reduce", locale="zh-TW")
    context.add_init_script("localStorage.setItem('gash-spotlight', 'off')")
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(server)
    page.wait_for_function("Object.keys(CARDS).length > 0")
    page.evaluate("startLocal()")
    page.wait_for_function("S && S.phase === 'start'")
    yield page
    context.close()
    assert not errors


def play_turns(page, n):
    """每回合:回合玩家翻 1 頁、雙方 pass 結束回合;累積記錄並讓魔書往後翻。"""
    for _ in range(n):
        page.evaluate("""async () => {
            await send({type: 'flip_pages', player: S.turn_player, count: 1});
            for (let i = 0; i < 2 && S.phase === 'battle'; i++) await send({type: 'pass', player: S.action_player});
        }""")
        page.wait_for_function("S.phase === 'start'")
    page.evaluate("Anim.idle()")


def visible_entries(page):
    return page.evaluate("""[...document.querySelectorAll('#log .ev')]
        .filter((el) => el.getBoundingClientRect().height > 0).map((el) => el.textContent)""")


def test_collapsed_drawer_shows_latest_four(phone):
    play_turns(phone, 2)
    entries = phone.evaluate("[...document.querySelectorAll('#log .ev')].map((el) => el.textContent)")
    assert len(entries) > 4
    assert visible_entries(phone) == entries[-4:]
    assert phone.locator("#log-title").text_content() == "行動記錄"


def test_expanded_drawer_shows_latest_without_squeezing_board(phone):
    play_turns(phone, 6)
    phone.locator("#log-title").click()
    m = phone.evaluate("""() => {
        const log = document.getElementById('log');
        const last = log.lastElementChild.getBoundingClientRect();
        const box = log.getBoundingClientRect();
        return {
            panel: document.getElementById('log-panel').getBoundingClientRect().height,
            board: document.getElementById('board').clientHeight,
            overflow: log.scrollHeight > log.clientHeight,
            lastVisible: last.bottom <= box.bottom + 1 && last.top >= box.top - 1,
            docScroll: document.scrollingElement.scrollHeight - innerHeight,
        };
    }""")
    assert m["overflow"]                                                   # 記錄超過面板高度
    assert abs(m["panel"] - 844 * 0.45) < 2
    assert m["board"] > 0
    assert m["lastVisible"]
    assert m["docScroll"] <= 0
    phone.locator("#log-title").click()
    assert len(visible_entries(phone)) == 4


def current_spread_visible(page):
    return page.evaluate("""() => {
        const box = document.getElementById('book-review').getBoundingClientRect();
        const head = document.getElementById('book-review-head').getBoundingClientRect();
        if (head.top < box.top - 1 || head.bottom > box.top + head.height + 1) return false;   // 標題列在上緣
        const cur = document.querySelector('#book-review .review-cell.open')
            || document.querySelector('#book-review .review-cell');
        const r = cur.getBoundingClientRect();
        return r.top >= head.bottom && r.bottom <= box.bottom;
    }""")


def test_book_review_opens_at_current_page(phone):
    play_turns(phone, 8)
    p = phone.evaluate("S.turn_player")
    assert phone.evaluate(f"S.players[{p}].pos") >= 8
    phone.evaluate(f"showBookReview({p})")
    assert phone.locator("#book-review .review-cell.open").count() > 0
    assert current_spread_visible(phone)


def test_book_review_keeps_scroll_on_rerender(phone):
    play_turns(phone, 8)
    p = phone.evaluate("S.turn_player")
    phone.evaluate(f"showBookReview({p})")
    phone.evaluate("document.getElementById('book-review').scrollTop = 0")
    phone.evaluate("render()")
    assert phone.evaluate("document.getElementById('book-review').scrollTop") == 0
    phone.evaluate("closeBookReview()")
    phone.evaluate(f"showBookReview({p})")                                # 重新開啟:回到當前頁
    assert current_spread_visible(phone)
