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


# ---------------------------------------------------------------- 關閉(close-rooms)

def remember(page, code, mode, token, viewer=0):
    """讓瀏覽器記得這個房間(與進房時存的格式相同),回到首頁重新列出。"""
    page.evaluate(f"""() => localStorage.setItem('gash-room-{code}',
        JSON.stringify({{code: '{code}', mode: '{mode}', viewer: {viewer}, tokens: {{me: '{token}'}}}}))""")
    page.evaluate("show('landing')")


def row(page, code):
    return page.locator(f'#landing-resume .resume-row:has(.resume-item[data-code="{code}"])')


def test_close_local_room_without_confirm(page, server):
    start_as(page, "all")
    code = page.evaluate("SESSION.code")
    token = page.evaluate("Object.values(SESSION.tokens)[0]")
    page.locator("#leave-room").click()
    assert resume_items(page) == [code]
    row(page, code).locator(".resume-close").click()
    page.wait_for_function("document.getElementById('landing-resume').classList.contains('hidden')")
    assert page.evaluate(f"localStorage.getItem('gash-room-{code}')") is None
    res = page.request.get(f"{server}/api/rooms/{code}/state", headers={"X-Player-Token": token})
    assert res.status == 404                                                   # 伺服器上的房間已刪除


def test_close_started_online_room_confirms_then_forfeits(page, server):
    a = page.request.post(f"{server}/api/rooms", data={"mode": "online", "seed": 5}).json()
    page.request.post(f"{server}/api/rooms/{a['code']}/join")
    code = a["code"]
    remember(page, code, "online", a["player_token"])
    assert resume_items(page) == [code]
    row(page, code).locator(".resume-close").click()
    assert row(page, code).locator(".resume-confirm").is_visible()           # 先確認,不直接棄權
    row(page, code).locator(".resume-cancel").click()
    assert row(page, code).locator(".resume-close").is_visible()
    row(page, code).locator(".resume-close").click()
    row(page, code).locator(".resume-confirm").click()
    page.wait_for_function(f"localStorage.getItem('gash-room-{code}') === null")
    state = page.request.get(f"{server}/api/rooms/{code}/state",
                             headers={"X-Player-Token": a["player_token"]}).json()["state"]
    assert state["phase"] == "game_over" and state["winner"] == 1 and state["end_reason"] == "forfeit"


def test_close_waiting_table_leaves_table(page, server):
    host = page.request.post(f"{server}/api/tables/5/sit",
                             data={"name": "測試", "expect": "empty", "timer_seconds": 60}).json()
    code = host["code"]
    remember(page, code, "online", host["player_token"])
    assert resume_items(page) == [code]
    row(page, code).locator(".resume-close").click()
    page.wait_for_function(f"localStorage.getItem('gash-room-{code}') === null")
    tables = page.request.get(f"{server}/api/tables").json()
    assert tables["tables"][4]["state"] == "empty"
