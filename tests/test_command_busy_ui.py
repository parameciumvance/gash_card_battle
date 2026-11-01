"""指令送出中(battle-ui「指令送出中」)。需要 playwright 與 Chromium。

Run: python -m pytest tests/test_command_busy_ui.py -q
"""
from tests.test_timing_ui import send, start_as
from tests.test_turn_dial_ui import button

NOTE = "#action-bar .sending-note"


def delay_commands(page, ms, fail=False):
    """之後的 /commands 請求在瀏覽器內延遲 ms 毫秒才送出(fail 時改回 400);送出的指令記在 window.SENT。"""
    page.evaluate("""([ms, fail]) => {
        const orig = window.__origFetch || (window.__origFetch = window.fetch);
        window.SENT = [];
        window.fetch = async (url, opts) => {
            if (!String(url).endsWith('/commands')) return orig(url, opts);
            window.SENT.push(JSON.parse(opts.body).command);
            await new Promise((r) => setTimeout(r, ms));
            if (fail) return new Response(JSON.stringify({detail: {code: 'priority.other', message: 'x'}}),
                                          {status: 400, headers: {'Content-Type': 'application/json'}});
            return orig(url, opts);
        };
    }""", [ms, fail])


def sent(page):
    return page.evaluate("window.SENT.length")


def to_battle(page):
    tp, me = start_as(page, "turn")
    send(page, tp, {"type": "flip_pages", "count": 0})
    page.wait_for_function("S.phase === 'battle'")
    return tp


def test_slow_response_shows_note_and_blocks_second_send(page):
    tp = to_battle(page)
    delay_commands(page, 1000)
    button(page, "Pass").click()
    page.wait_for_selector(NOTE)
    assert page.locator(NOTE).text_content() == "處理中…"
    assert page.evaluate("document.body.classList.contains('sending')")
    button(page, "Pass").click(force=True)                                # 送出中再按:不會送出第二次
    page.evaluate(f"send({{type: 'pass', player: {tp}}})")                # 鍵盤等其他途徑也一樣
    page.wait_for_function("S.consecutive_passes === 1")
    page.wait_for_selector(NOTE, state="detached")
    assert not page.evaluate("document.body.classList.contains('sending')")
    assert sent(page) == 1


def test_fast_response_has_no_note(page):
    to_battle(page)
    page.evaluate("""() => { window.noteSeen = false;
        new MutationObserver(() => { if (document.querySelector('#action-bar .sending-note')) window.noteSeen = true; })
          .observe(document.body, {childList: true, subtree: true}); }""")
    button(page, "Pass").click()
    page.wait_for_function("S.consecutive_passes === 1")
    page.wait_for_timeout(300)
    assert not page.evaluate("window.noteSeen")


def test_failure_clears_busy_state(page):
    to_battle(page)
    delay_commands(page, 600, fail=True)
    button(page, "Pass").click()
    page.wait_for_selector(NOTE)
    page.wait_for_selector("#toast:not(.hidden)")
    page.wait_for_selector(NOTE, state="detached")
    assert not page.evaluate("document.body.classList.contains('sending')")
    page.evaluate("window.fetch = window.__origFetch")
    button(page, "Pass").click()                                          # 可以再操作
    page.wait_for_function("S.consecutive_passes === 1")
