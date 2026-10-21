"""返回進行中的對局、標題回到首頁(battle-ui「返回進行中的對局」「標題回到首頁」)。

Run: python -m pytest tests/test_resume_room_ui.py -q
"""
import json

from tests.test_timing_ui import start_as


def resume_items(page):
    page.wait_for_function("window.__resumeDone === true || !document.getElementById('landing').classList.contains('hidden')")
    page.wait_for_timeout(300)                                                 # 等並行的查詢完成
    return page.evaluate("""() => {
        const box = document.getElementById('landing-resume');
        if (!box || box.classList.contains('hidden')) return null;
        return [...box.querySelectorAll('.resume-item')].map(b => b.dataset.code);
    }""")


def test_leave_then_resume_from_landing(page):
    start_as(page, "all")
    code = page.evaluate("SESSION.code")
    turn = page.evaluate("S.turn_no")
    page.locator("#leave-room").click()
    assert resume_items(page) == [code]
    text = page.locator(f'#landing-resume .resume-item[data-code="{code}"]').text_content()
    assert code in text and "自由調查時間" in text and page.evaluate(f"t('ui.turn', {{n: {turn}}})") in text
    page.locator(f'#landing-resume .resume-item[data-code="{code}"]').click()
    page.wait_for_function(f"SESSION && SESSION.code === '{code}' && !document.getElementById('layout').classList.contains('hidden')")
    assert page.evaluate("location.search") == f"?room={code}"


def test_gone_room_removed_and_finished_room_hidden(page):
    start_as(page, "all")
    code = page.evaluate("SESSION.code")
    page.locator("#leave-room").click()
    resume_items(page)
    page.evaluate("""() => localStorage.setItem('gash-room-GONE00',
        JSON.stringify({code: 'GONE00', mode: 'online', viewer: 0, tokens: {me: 'nope'}}))""")
    page.route(f"**/api/rooms/{code}/state", lambda route: route.fulfill(
        status=200, content_type="application/json",
        body=json.dumps({"state": {"phase": "game_over", "turn_no": 3}, "room": {"mode": "local", "started": True,
                                                                            "names": [None, None]}})))
    page.evaluate("show('landing')")
    assert resume_items(page) is None                                          # 已結束 + 不存在:沒有項目就不顯示
    assert page.evaluate("localStorage.getItem('gash-room-GONE00')") is None   # 不存在的房間移除記錄


def test_title_goes_home_from_builder_and_game(page):
    page.evaluate("showBuilder()")
    page.locator("#title").click()
    page.wait_for_function("!document.getElementById('landing').classList.contains('hidden')")
    start_as(page, "all")
    code = page.evaluate("SESSION.code")
    page.locator("#title").focus()
    page.keyboard.press("Enter")
    page.wait_for_function("!document.getElementById('landing').classList.contains('hidden')")
    assert page.evaluate("SESSION") is None
    assert resume_items(page) == [code]                                        # 對局仍可返回
