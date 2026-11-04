"""接回對局的連線失敗與連線心跳(battle-ui「接回對局的連線失敗」「連線心跳」「返回進行中的對局」)。
需要 playwright 與 Chromium。

Run: python -m pytest tests/test_reconnect_ui.py -q
"""
import pytest

OVERLAY = "#reconnect-overlay:not(.hidden)"


def wait(tab, expr):
    tab.wait_for_function(expr, polling=100)


def create_room(page):
    page.add_init_script("window.__reconnectDelays = [300]; window.__wsHeartbeatMs = 300;")
    page.reload()
    wait(page, "Object.keys(CARDS).length > 0")
    page.evaluate("createRoom()")
    wait(page, "SESSION && SESSION.viewer === 0 && !document.getElementById('waiting').classList.contains('hidden')")
    return page.evaluate("SESSION.code"), page.evaluate("SESSION.tokens.me")


def fail_state_once(page, how):
    """下一次讀取房間狀態失敗一次(how:abort 網路失敗 / html 代理的 502 錯誤頁),之後照常。"""
    state = {"failed": False}

    def handle(route):
        if state["failed"]:
            route.continue_()
            return
        state["failed"] = True
        if how == "abort":
            route.abort()
        else:
            route.fulfill(status=502, content_type="text/html", body="<html><body>Bad gateway</body></html>")
    page.route("**/api/rooms/*/state", handle)
    return state


@pytest.mark.parametrize("how", ["abort", "html"])
def test_resume_retries_on_network_or_proxy_error(page, how):
    code, token = create_room(page)
    fail_state_once(page, how)
    page.reload()
    wait(page, "document.querySelector('#reconnect-overlay') && !document.querySelector('#reconnect-overlay').classList.contains('hidden')")
    assert "連線失敗,重試中" in page.locator("#reconnect-overlay").text_content()
    assert page.evaluate(f"localStorage.getItem('gash-room-{code}')") is not None      # 身分保留
    wait(page, "!document.getElementById('waiting').classList.contains('hidden')")   # 恢復後回到房間
    assert page.locator(OVERLAY).count() == 0
    assert page.evaluate("[SESSION.code, SESSION.tokens.me]") == [code, token]


def test_back_home_keeps_identity(page):
    code, _ = create_room(page)
    page.route("**/api/rooms/*/state", lambda route: route.abort())
    page.reload()
    wait(page, "document.querySelector('#reconnect-overlay') && !document.querySelector('#reconnect-overlay').classList.contains('hidden')")
    page.locator("#reconnect-home").click()
    wait(page, "!document.getElementById('landing').classList.contains('hidden')")
    assert page.locator(OVERLAY).count() == 0
    assert page.evaluate("location.search") == ""
    assert page.evaluate(f"localStorage.getItem('gash-room-{code}')") is not None
    page.unroute("**/api/rooms/*/state")
    page.evaluate("refreshResumeRooms()")
    wait(page, f"!!document.querySelector('#landing-resume .resume-item[data-code=\"{code}\"]')")   # 連得上後可返回


def test_gone_room_still_dropped(page):
    code, _ = create_room(page)
    page.route("**/api/rooms/*/state", lambda route: route.fulfill(
        status=404, json={"detail": {"code": "room.not_found", "message": "房間不存在"}}))
    page.reload()
    wait(page, "!document.getElementById('landing').classList.contains('hidden')")
    assert page.locator(OVERLAY).count() == 0
    assert page.evaluate(f"localStorage.getItem('gash-room-{code}')") is None


def test_landing_list_keeps_record_on_network_error(page):
    code, _ = create_room(page)
    page.evaluate("show('landing')")
    page.route("**/api/rooms/*/state", lambda route: route.abort())
    page.evaluate("refreshResumeRooms()")
    page.wait_for_timeout(500)
    assert page.evaluate(f"localStorage.getItem('gash-room-{code}')") is not None


def test_websocket_heartbeat(page):
    frames = []
    page.on("websocket", lambda ws: ws.on("framesent", lambda payload: frames.append(payload)))
    create_room(page)
    page.wait_for_timeout(1000)
    assert frames.count("ping") >= 2
