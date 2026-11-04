"""棄權與對手沒有回應的畫面(battle-ui「棄權」「對手沒有回應的提示」「房間關閉」)。需要 playwright 與 Chromium。

Run: python -m pytest tests/test_forfeit_absence_ui.py -q
"""
from tests.test_npc_ui import start_npc
from tests.test_timing_ui import start_as

FORFEIT = "#forfeit"


def test_forfeit_button_and_confirm(page):
    start_npc(page)
    assert page.locator(FORFEIT).is_visible() and page.locator(FORFEIT).text_content() == "棄權"
    page.locator(FORFEIT).click()
    page.wait_for_selector("#dialog-overlay:not(.hidden)")
    assert "確定要棄權嗎" in page.locator("#dialog-title").text_content()
    page.locator("#dialog-options button", has_text="取消").click()               # 取消:什麼都不發生
    assert page.evaluate("S.phase") != "game_over"
    page.locator(FORFEIT).click()
    page.locator("#dialog-options button", has_text="棄權").click()
    page.wait_for_function("S.phase === 'game_over'")
    assert page.evaluate("S.winner") == 1 and page.evaluate("S.end_reason") == "forfeit"
    page.wait_for_selector("#info-overlay:not(.hidden)")                           # 結算面板
    assert page.evaluate("t('ui.reason.forfeit', {player: pname(0)})") in page.locator("#info-overlay").text_content()
    assert page.locator(FORFEIT).is_hidden()                                      # 結束後不再顯示


def test_no_forfeit_in_local_or_spectator(page):
    start_as(page, "all")
    assert page.locator(FORFEIT).is_hidden()
    page.evaluate("SESSION = {...SESSION, mode: 'online', viewer: 'spectator'}; render();")
    assert page.locator(FORFEIT).is_hidden()


def test_absence_prompt_and_choices(page):
    start_npc(page)
    page.evaluate("wsWanted = false; if (ws) ws.close();")
    page.evaluate("R = {...R, unresponsive: [false, true]}; render();")
    prompt = page.locator("#action-bar .absence-prompt")
    assert "對手沒有回應" in prompt.text_content()
    bodies = []
    page.route("**/absence", lambda route: (bodies.append(route.request.post_data_json),
                                            route.fulfill(json={"room": page.evaluate("R"), "state": page.evaluate("S")})))
    prompt.locator("button", has_text="繼續等").click()
    page.wait_for_function("true")
    prompt.locator("button", has_text="結束對局").click()
    page.wait_for_timeout(300)
    assert bodies == [{"action": "wait"}, {"action": "end"}]
    page.evaluate("R = {...R, unresponsive: [true, false]}; render();")           # 自己被判定沒回應:不顯示
    assert page.locator("#action-bar .absence-prompt").count() == 0


def test_room_closed_goes_home(page):
    start_npc(page)
    code = page.evaluate("SESSION.code")
    page.evaluate("ws.onclose({code: 4404})")
    page.wait_for_function("!SESSION && !document.getElementById('landing').classList.contains('hidden')")
    assert page.evaluate(f"localStorage.getItem('gash-room-{code}')") is None
    assert "房間已關閉" in page.locator("#toast").text_content()
