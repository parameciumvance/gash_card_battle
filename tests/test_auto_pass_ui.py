"""自動 pass 與有可用行動的提示(battle-ui「自動 pass」「有可用行動的提示」)。需要 playwright 與 Chromium。

快照的 idle 以注入模擬(判斷本身由 tests/test_auto_pass.py 驗證);send 換成記錄,並模擬狀態前進。

Run: python -m pytest tests/test_auto_pass_ui.py -q
"""
import pytest

TOGGLE = "#action-bar .auto-pass-toggle input"


@pytest.fixture
def page(browser, server):  # noqa: F811
    """自動 pass 開啟的頁面(conftest 預設關閉;這裡在之後的 init script 改為開啟)。"""
    context = browser.new_context(viewport={"width": 1280, "height": 900}, reduced_motion="reduce", locale="zh-TW")
    # 只在分頁第一次載入時開啟(init script 每次載入都會執行,重新整理時不能蓋掉測試改過的設定)
    context.add_init_script("""localStorage.setItem('gash-spotlight', 'off');
        if (!sessionStorage.getItem('auto-pass-init')) {
            localStorage.setItem('gash-auto-pass', 'on'); sessionStorage.setItem('auto-pass-init', '1');
        }""")
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(server)
    page.wait_for_function("Object.keys(CARDS).length > 0")
    yield page
    context.close()
    assert not errors


def awaiting_non_turn(page, idle):
    """自由調查時間,戰鬥階段非戰鬥中輪到非回合玩家;send 記錄指令並讓狀態前進(事件數 +1、idle 清除)。"""
    page.evaluate("startLocal()")
    page.wait_for_function("S && S.phase && S.players[0].book")
    page.evaluate("Anim.idle()")
    page.evaluate("""(idle) => {
        window.SENT = [];
        send = (cmd) => { SENT.push(cmd); S = {...S, event_count: S.event_count + 1, idle: null}; render(); return Promise.resolve(); };
        S = {...S, phase: 'battle', battle: null, battle_in: null, pending: null,
             action_player: 1 - S.turn_player, idle};
        render();
    }""", idle)
    return page.evaluate("1 - S.turn_player")


AUTO = {"has_actions": False, "auto": {"type": "pass"}}


def sent(page):
    return page.evaluate("SENT")


def delay(page):
    """倒數時間(毫秒),測試依它推算等待時間,調整秒數不必改測試。"""
    return page.evaluate("AUTO_PASS_MS")


def test_toggle_default_on_and_hidden_for_spectators(browser, server):  # noqa: F811
    context = browser.new_context(viewport={"width": 1280, "height": 900}, reduced_motion="reduce", locale="zh-TW")
    context.add_init_script("localStorage.removeItem('gash-auto-pass')")   # 未設定:預設開啟
    p = context.new_page()
    p.goto(server)
    p.wait_for_function("Object.keys(CARDS).length > 0")
    awaiting_non_turn(p, None)
    assert p.locator(TOGGLE).is_checked()
    assert "無可用行動時自動 pass" in p.locator("#action-bar .auto-pass-toggle").text_content()
    p.evaluate("SESSION = {...SESSION, viewer: 'spectator'}; render()")
    assert p.locator(TOGGLE).count() == 0
    context.close()


def test_auto_sends_once_after_two_seconds(page):
    nt = awaiting_non_turn(page, AUTO)
    ms = delay(page)
    page.wait_for_timeout(ms * 0.4)
    assert sent(page) == []                                               # 還在倒數
    assert "即將自動 pass" in page.locator("#action-bar .auto-pass-toggle").text_content()
    page.wait_for_timeout(ms * 0.6 + 800)
    assert sent(page) == [{"type": "pass", "player": nt}]
    page.wait_for_timeout(ms + 500)
    assert len(sent(page)) == 1                                           # 不重複送出


def test_auto_enters_battle_and_no_defense(page):
    nt = awaiting_non_turn(page, {"has_actions": False, "auto": {"type": "no_defense"}})
    page.wait_for_timeout(delay(page) + 800)
    assert sent(page) == [{"type": "no_defense", "player": nt}]


def test_pause_while_zoom_open(page):
    awaiting_non_turn(page, AUTO)
    ms = delay(page)
    page.evaluate("zoom('S-001')")
    page.wait_for_timeout(ms + 1000)
    assert sent(page) == []                                               # 查看卡片時不送
    page.evaluate("closeZoom()")
    page.wait_for_timeout(ms * 0.5)
    assert sent(page) == []                                               # 關閉後重新倒數
    page.wait_for_timeout(ms * 0.5 + 800)
    assert len(sent(page)) == 1


def test_manual_pass_first_sends_once(page):
    nt = awaiting_non_turn(page, AUTO)
    page.locator("#action-bar button", has_text="Pass").click()
    page.wait_for_timeout(delay(page) + 1000)
    assert sent(page) == [{"type": "pass", "player": nt}]


def test_turning_off_stops_and_persists(page):
    awaiting_non_turn(page, AUTO)
    page.locator(TOGGLE).uncheck()
    page.wait_for_timeout(delay(page) + 1000)
    assert sent(page) == []
    assert page.evaluate("localStorage.getItem('gash-auto-pass')") == "off"
    page.reload()
    page.wait_for_function("Object.keys(CARDS).length > 0")
    awaiting_non_turn(page, AUTO)
    assert not page.locator(TOGGLE).is_checked()


def test_has_actions_hint_without_auto(page):
    awaiting_non_turn(page, {"has_actions": True, "auto": None})
    assert page.locator("#action-bar .idle-hint").text_content() == "有可以使用的效果或行動"
    page.wait_for_timeout(delay(page) + 800)
    assert sent(page) == []


def test_full_label_on_narrow_screen(page):
    """窄螢幕也顯示完整的句子(縮小、可換行),不超出畫面。"""
    page.set_viewport_size({"width": 390, "height": 844})
    awaiting_non_turn(page, None)
    label = page.locator("#action-bar .auto-pass-toggle")
    assert label.text_content().strip() == "無可用行動時自動 pass"
    box = label.bounding_box()
    assert box["x"] >= 0 and box["x"] + box["width"] <= 390
