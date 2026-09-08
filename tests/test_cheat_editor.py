"""Chromium integration tests. Requires playwright and its Chromium browser.

Run: python -m pytest tests/test_cheat_editor.py -q
Uses an isolated local server and a fresh browser context per test.
"""
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

import pytest

pw = pytest.importorskip("playwright.sync_api")
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def server():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "gash.api.app:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(100):
            try:
                with urlopen(base + "/api/meta", timeout=1):
                    break
            except OSError:
                if process.poll() is not None:
                    pytest.fail("Browser test server exited")
                time.sleep(.05)
        else:
            pytest.fail("Browser test server did not start")
        yield base
    finally:
        process.terminate()
        process.wait(timeout=10)


@pytest.fixture(scope="module")
def browser():
    with pw.sync_playwright() as runtime:
        try:
            instance = runtime.chromium.launch()
        except pw.Error as exc:
            pytest.skip(f"Chromium unavailable: {exc}")
        yield instance
        instance.close()


@pytest.fixture
def page(browser, server):
    context = browser.new_context(viewport={"width": 1280, "height": 900}, reduced_motion="reduce")
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(server)
    page.wait_for_function("Object.keys(CARDS).length > 0 && document.querySelector('#cheat-toggle').textContent")
    yield page
    context.close()
    assert not errors


def open_local(page):
    page.evaluate("startLocal()")
    page.locator("#cheat-toggle").click()
    ready(page)


def ready(page):
    page.wait_for_function("CHEAT && CHEAT.players && !CHEAT.busy")


def books(page):
    return page.evaluate("CHEAT.players.map(p => [...p.book])")


def slot(page, n, grid="cheat-book-grid"):
    return page.locator(f"#{grid} .page-slot").nth(n)


def choose(page, num):
    page.locator(f'#cheat-pool-grid .card[aria-label^="{num} "]').click()


def debug_state(page):
    return page.evaluate("api(`/api/rooms/${SESSION.code}/debug-state`, {headers: {'X-Player-Token': Object.values(SESSION.tokens)[0]}})")


def test_page_edit_swap_and_cancel_do_not_touch_saved_decks(page):
    page.evaluate("localStorage.setItem('gash-deck-draft', JSON.stringify({name:'draft', pages:Array(32).fill('M-001')}))")
    draft = page.evaluate("localStorage.getItem('gash-deck-draft')")
    posts = []
    page.on("request", lambda r: posts.append(r) if r.method == "POST" and r.url.endswith("/debug-state") else None)
    open_local(page)
    initial = books(page)
    choose(page, "E-001")
    assert books(page) == initial
    assert page.locator("#cheat-error").is_visible()
    slot(page, 11).click()
    choose(page, "E-001")
    expected = [*initial[0]]
    expected[11] = "E-001"
    assert books(page) == [expected, initial[1]]
    assert slot(page, 11).get_attribute("aria-pressed") == "true"
    slot(page, 11).click()
    assert slot(page, 11).get_attribute("aria-pressed") == "false"
    assert books(page)[0] == expected
    slot(page, 2).click()
    slot(page, 4).click()
    assert books(page)[0] == expected
    slot(page, 2).drag_to(slot(page, 4))
    expected[2], expected[4] = expected[4], expected[2]
    assert books(page)[0] == expected
    assert page.locator("#cheat-book-grid .selected").count() == 0
    page.locator("#cheat-mp").fill("77")
    page.locator("#cheat-players button").nth(1).click()
    slot(page, 0).click()
    choose(page, "E-002")
    page.locator("#cheat-players button").first.click()
    assert page.locator("#cheat-mp").input_value() == "77"
    assert books(page)[0] == expected
    assert books(page)[1][0] == "E-002"
    page.evaluate("render()")
    assert page.locator("#cheat-mp").input_value() == "77"
    assert page.evaluate("localStorage.getItem('gash-deck-draft')") == draft
    page.locator("#cheat-cancel").click()
    assert not page.locator("#cheat-panel").is_visible()
    assert not posts
    page.locator("#cheat-toggle").click()
    ready(page)
    assert books(page) == initial


def test_apply_both_players_and_permissive_books_sync_board(page):
    open_local(page)
    page.evaluate("CHEAT.players[0].book = Array(32).fill('S-001'); CHEAT.players[1].book = Array(32).fill('M-001'); renderCheatFields()")
    page.locator("#cheat-mp").fill("99")
    page.locator("#cheat-players button").nth(1).click()
    page.locator("#cheat-mp").fill("42")
    with page.expect_request(lambda r: r.method == "POST" and r.url.endswith("/debug-state")) as sent:
        page.locator("#cheat-apply").click()
    ready(page)
    payload = sent.value.post_data_json
    assert payload["players"] == [{"book": ["S-001"]*32, "mp": 99}, {"book": ["M-001"]*32, "mp": 42}]
    assert debug_state(page) == payload
    assert page.evaluate("S.players.map(p => p.mp)") == [99, 42]
    assert page.locator("#cheat-status").inner_text() == "已套用"
    assert page.evaluate("localStorage.getItem('gash-deck-draft')") is None


def test_pending_failure_refresh_and_validation_preserve_draft(page):
    open_local(page)
    initial = debug_state(page)
    page.locator("#cheat-mp").fill("67")
    pending = []
    page.route("**/debug-state", lambda route: pending.append(route))
    page.locator("#cheat-apply").click()
    page.wait_for_function("CHEAT.busy")
    assert page.locator("#cheat-apply").is_disabled()
    assert page.locator("#cheat-refresh").is_disabled()
    assert page.locator("#cheat-mp").is_disabled()
    page.evaluate("cheatApply()")
    assert len(pending) == 1
    pending.pop().fulfill(status=500, json={"detail": {"message": "test failure"}})
    ready(page)
    assert page.locator("#cheat-mp").input_value() == "67"
    assert page.locator("#cheat-error").inner_text() == "test failure"
    page.locator("#cheat-refresh").click()
    page.wait_for_function("CHEAT.busy")
    pending.pop().abort()
    ready(page)
    assert page.locator("#cheat-mp").input_value() == "67"
    page.unroute("**/debug-state")
    page.evaluate("CHEAT.players[0].book[0] = 'X-999'")
    page.locator("#cheat-apply").click()
    assert "有效卡號" in page.locator("#cheat-error").inner_text()
    assert page.evaluate("CHEAT.players[0].book[0]") == "X-999"
    page.locator("#cheat-refresh").click()
    ready(page)
    assert page.evaluate("CHEAT.players") == initial["players"]
    assert page.evaluate("CHEAT.selected") == [None, None]


def test_initial_failure_and_stale_response_cannot_reopen_or_overwrite(page):
    page.evaluate("startLocal()")
    page.route("**/debug-state", lambda route: route.fulfill(status=503, json={"detail": {"message": "offline"}}))
    page.locator("#cheat-toggle").click()
    pw.expect(page.locator("#cheat-error")).to_have_text("offline")
    assert page.locator("#cheat-apply").is_disabled()
    assert page.locator("#cheat-mp").is_disabled()
    page.unroute("**/debug-state")
    page.locator("#cheat-refresh").click()
    ready(page)
    old = debug_state(page)
    old["players"][0]["mp"] = 888
    pending = []
    page.route("**/debug-state", lambda route: pending.append(route))
    page.locator("#cheat-refresh").click()
    page.wait_for_function("CHEAT.busy")
    old_route = pending.pop()
    page.keyboard.press("Escape")
    assert page.evaluate("CHEAT") is None
    page.locator("#cheat-toggle").click()
    page.wait_for_function("CHEAT.busy")
    new_route = pending.pop()
    fresh = {"players": [{"book": ["M-001"]*32, "mp": 7}, {"book": ["S-001"]*32, "mp": 9}]}
    new_route.fulfill(json=fresh)
    ready(page)
    with page.expect_response(lambda r: r.url.endswith("/debug-state")):
        old_route.fulfill(json=old)
    page.wait_for_function("!CHEAT.busy")
    assert page.locator("#cheat-mp").input_value() == "7"
    assert page.evaluate("CHEAT.players") == fresh["players"]
    page.evaluate("leaveRoom()")
    assert page.evaluate("CHEAT") is None
    assert not page.locator("#cheat-panel").is_visible()


def test_filters_fallback_mobile_and_modal_permissions(page):
    page.route("**/static/assets/cards/E-001.jpg", lambda route: route.abort())
    open_local(page)
    filters = page.locator("#cheat-filters select")
    card = page.evaluate("Object.values(CARDS).find(c => c.type === 'spell' && c.related_mamodo && c.related_mamodo !== 'Command: All' && c.sets.length)")
    before = books(page)
    filters.nth(0).select_option("spell")
    filters.nth(1).select_option(card["related_mamodo"])
    filters.nth(2).select_option(card["sets"][0])
    nums = page.locator("#cheat-pool-grid .cnum").all_text_contents()
    expected = page.evaluate("c => Object.values(CARDS).filter(x => x.type === 'spell' && x.related_mamodo === c.related_mamodo && x.sets.includes(c.sets[0])).map(x => x.number).sort()", card)
    assert nums == expected
    assert books(page) == before
    for i in range(3):
        filters.nth(i).select_option("")
    image = page.locator('#cheat-pool-grid .card[aria-label^="E-001 "] img')
    pw.expect(image).to_have_attribute("src", "/static/back.jpg")
    for width in (390, 320):
        page.set_viewport_size({"width": width, "height": 844})
        assert page.evaluate("document.querySelector('#cheat-panel').scrollWidth <= document.querySelector('#cheat-panel').clientWidth")
        slot(page, 31).click()
        choose(page, "E-002")
        assert books(page)[0][31] == "E-002"
        assert page.locator("#cheat-apply").is_visible()
    assert page.evaluate("document.querySelector('#cheat-panel').matches(':modal')")
    page.locator("#cheat-close").click()
    page.evaluate("SESSION.viewer = 'spectator'; renderTopbar()")
    assert not page.locator("#cheat-toggle").is_visible()
    page.evaluate("openCheat()")
    assert page.evaluate("CHEAT") is None
    page.evaluate("SESSION.mode = 'online'; SESSION.viewer = 0; renderTopbar()")
    assert not page.locator("#cheat-toggle").is_visible()


def test_builder_shared_components_keep_original_behavior(page):
    page.evaluate("showBuilder()")
    page.locator('#pool-grid .card[aria-label^="M-001 "]').click()
    page.locator('#pool-grid .card[aria-label^="S-001 "]').click()
    assert page.evaluate("B.deck.pages.slice(0,2)") == ["M-001", "S-001"]
    slot(page, 0, "book-grid").click()
    slot(page, 1, "book-grid").click()
    assert page.evaluate("B.deck.pages.slice(0,2)") == ["S-001", "M-001"]
    slot(page, 0, "book-grid").drag_to(slot(page, 1, "book-grid"))
    assert page.evaluate("B.deck.pages.slice(0,2)") == ["M-001", "S-001"]
    slot(page, 0, "book-grid").click()
    slot(page, 0, "book-grid").click()
    assert page.evaluate("B.deck.pages[0]") is None
    assert page.evaluate("DeckStore.loadDraft().pages") == page.evaluate("B.deck.pages")
    page.locator("#pool-filters select").first.select_option("event")
    assert page.locator("#pool-grid .card:not(.type-event)").count() == 0
    assert page.locator("#builder-validation .err").count() > 0
    page.locator("#builder-save").click()
    assert page.evaluate("DeckStore.list()[0].valid") is False


def test_keyboard_selection_and_edit_clears_applied_status(page):
    open_local(page)
    page.locator("#cheat-apply").click()
    ready(page)
    assert page.locator("#cheat-status").inner_text() == "已套用"
    before = books(page)
    slot(page, 10).focus()
    page.keyboard.press("Enter")
    assert slot(page, 10).get_attribute("aria-pressed") == "true"
    pw.expect(slot(page, 10)).to_be_focused()
    page.keyboard.press("Space")
    assert slot(page, 10).get_attribute("aria-pressed") == "false"
    assert books(page) == before
    page.locator("#cheat-mp").fill("18")
    assert page.locator("#cheat-status").inner_text() == ""


def test_post_response_from_closed_editor_preserves_new_draft(page):
    open_local(page)
    pending = []
    page.route("**/debug-state", lambda route: pending.append(route) if route.request.method == "POST" else route.continue_())
    page.locator("#cheat-mp").fill("70")
    page.locator("#cheat-apply").click()
    page.wait_for_function("CHEAT.busy")
    old_route = pending.pop()
    page.locator("#cheat-close").click()
    page.locator("#cheat-toggle").click()
    ready(page)
    page.locator("#cheat-mp").fill("21")
    with page.expect_response(lambda r: r.url.endswith("/state")):
        old_route.fulfill(json={"players": [{"book": ["M-001"]*32, "mp": 70}, {"book": ["M-001"]*32, "mp": 1}]})
    page.wait_for_function("CHEAT.players[0].mp === '21'")
    assert page.locator("#cheat-mp").input_value() == "21"
    assert page.locator("#cheat-status").inner_text() == ""
    # A successful POST followed by a failed state read is reported as applied.
    page.unroute("**/debug-state")
    page.route("**/state", lambda route: route.abort())
    page.locator("#cheat-apply").click()
    ready(page)
    assert "已套用，但讀取最新盤面失敗" in page.locator("#cheat-error").inner_text()
    assert page.locator("#cheat-status").inner_text() == "已套用"
    assert debug_state(page)["players"][0]["mp"] == 21
