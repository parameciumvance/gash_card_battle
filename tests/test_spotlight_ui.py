"""對手行動聚焦展示與演出設定的瀏覽器測試(battle-ui「對手行動聚焦展示」「演出設定」「事件動畫」)。
需要 playwright 與 Chromium。以本機測試模式操作,並把視角設為某一方,另一方的指令即為「對手」。

Run: python -m pytest tests/test_spotlight_ui.py -q
"""
import pytest

from tests.test_cheat_editor import browser, server  # noqa: F401  共用 fixture(隔離的伺服器與瀏覽器)

SPOT = "#spotlight:not(.hidden)"


def open_page(browser, server, *, motion="reduce", prefs=None):  # noqa: F811
    context = browser.new_context(viewport={"width": 1280, "height": 900}, reduced_motion=motion)
    if prefs:
        script = "".join(f"localStorage.setItem('gash-{k}', '{v}');" for k, v in prefs.items())
        context.add_init_script(script)
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(server)
    page.wait_for_function("Object.keys(CARDS).length > 0")
    return context, page, errors


@pytest.fixture
def spot(browser, server):  # noqa: F811
    """聚焦為標準、系統減少動態效果(動畫跳過,聚焦照常)。"""
    context, page, errors = open_page(browser, server, prefs={"spotlight": "normal"})
    yield page
    context.close()
    assert not errors


def start_as(page, me):
    """開本機房,視角設為 me:'defender'(非回合玩家,回合玩家即對手)或 'turn'。回傳對手的玩家編號。"""
    page.evaluate("startLocal()")
    page.wait_for_function("S && S.phase === 'start'")
    return page.evaluate(f"""() => {{
        const tp = S.turn_player;
        const me = '{me}' === 'turn' ? tp : 1 - tp;
        SESSION = {{...SESSION, viewer: me}};
        render();
        return 1 - me;
    }}""")


def send(page, player, command):
    page.evaluate("([p, c]) => send({...c, player: p})", [player, command])


def test_opponent_card_use_is_spotlighted_before_board_updates(spot):
    opp = start_as(spot, "defender")
    send(spot, opp, {"type": "flip_pages", "count": 0})
    send(spot, opp, {"type": "declare_attack", "page": 3})               # S-001
    spot.wait_for_selector(SPOT)
    assert spot.locator("#spotlight .spot-name").text_content() == spot.evaluate("cname('S-001')")
    assert spot.locator("#spotlight .spot-effect").text_content() == spot.evaluate("ZH['S-001'].effect")
    assert spot.locator("#spotlight").get_attribute("data-ms") == "1000"
    assert spot.locator("#battle-stage.open").count() == 0                # 播完才重繪
    spot.wait_for_selector("#spotlight.hidden", state="attached")
    spot.wait_for_selector("#battle-stage.open")


def test_opponent_pass_is_shown_briefly(spot):
    opp = start_as(spot, "defender")
    send(spot, opp, {"type": "flip_pages", "count": 0})
    send(spot, opp, {"type": "pass"})
    spot.wait_for_selector(SPOT)
    assert "pass" in spot.locator("#spotlight").text_content()
    assert spot.locator("#spotlight").get_attribute("data-ms") == "500"


def test_own_action_is_not_spotlighted(spot):
    me = 1 - start_as(spot, "turn")
    send(spot, me, {"type": "flip_pages", "count": 0})
    send(spot, me, {"type": "declare_attack", "page": 3})
    spot.wait_for_selector("#battle-stage.open")
    spot.wait_for_timeout(300)
    assert spot.locator(SPOT).count() == 0


def test_own_unfavorable_result_is_spotlighted(spot):
    opp = start_as(spot, "defender")
    me = 1 - opp
    send(spot, opp, {"type": "flip_pages", "count": 0})
    send(spot, opp, {"type": "declare_attack", "page": 3})
    send(spot, me, {"type": "battle_in_response", "allow": True})
    send(spot, me, {"type": "no_defense"})
    send(spot, opp, {"type": "pass"})
    send(spot, me, {"type": "pass"})                                     # 自己的 pass 觸發魔力勝負
    send(spot, me, {"type": "choose", "value": None})                    # 不保護 → 自己的魔本受傷
    spot.wait_for_function("""() => {
        const el = document.querySelector('#spotlight:not(.hidden)');
        return el && el.textContent.includes('魔本受到');
    }""", timeout=15000)


def test_click_skips_current_spotlight(spot):
    opp = start_as(spot, "defender")
    send(spot, opp, {"type": "flip_pages", "count": 0})
    send(spot, opp, {"type": "declare_attack", "page": 3})
    spot.wait_for_selector(SPOT)
    spot.locator("#spotlight").click()
    assert spot.locator(SPOT).count() == 0                                # 立即結束,不等 1 秒
    spot.wait_for_selector("#battle-stage.open")


def test_backlog_speeds_up(spot):
    opp = start_as(spot, "defender")
    passes = spot.evaluate(f"""() => {{
        const ms = [];
        new MutationObserver(() => {{
            const el = document.getElementById('spotlight');
            if (!el.classList.contains('hidden')) ms.push(el.dataset.ms);
        }}).observe(document.getElementById('spotlight'), {{attributes: true}});
        window.__ms = ms;
        const ev = (seq) => [{{seq, type: 'passed', player: {opp}}}];
        for (const seq of [90001, 90002, 90003]) Anim.apply(ev(seq), S, render, {opp});
        return true;
    }}""")
    assert passes
    spot.wait_for_function("window.__ms.length >= 3", timeout=5000)
    assert spot.evaluate("window.__ms[0]") == "250"                       # 排隊 3 批:加快(pass 為一半)
    spot.evaluate(f"Anim.apply([{{seq: 90004, type: 'passed', player: {opp}}}], S, render, {opp})")
    spot.wait_for_function("window.__ms.length >= 4", timeout=5000)
    assert spot.evaluate("window.__ms[3]") == "500"                       # 追上後恢復


def test_prefs_are_remembered_and_motion_follows_system(browser, server):  # noqa: F811
    context, page, errors = open_page(browser, server)                    # 系統減少動態效果、無預設
    assert page.evaluate("spotlightMode()") == "normal"
    assert page.evaluate("motionOff()") is True                           # 未設定:跟隨系統
    page.locator("#prefs-toggle").click()
    page.locator(".prefs-options button", has_text="快").click()
    page.locator(".prefs-options button", has_text="開").click()
    assert page.evaluate("motionOff()") is False
    assert page.evaluate("document.documentElement.classList.contains('motion-off')") is False
    page.reload()
    page.wait_for_function("Object.keys(CARDS).length > 0")
    assert page.evaluate("[spotlightMode(), motionOff()]") == ["fast", False]
    page.locator("#prefs-toggle").click()
    pressed = page.locator(".prefs-options button[aria-pressed='true']").all_text_contents()
    assert pressed == ["快", "開"]
    page.locator(".prefs-options button", has_text="關").first.click()   # 聚焦:關
    assert page.evaluate("spotlightMode()") == "off"
    context.close()
    assert not errors


@pytest.mark.parametrize("motion", ["off", "system"])
def test_in_game_motion_switch(motion, browser, server):  # noqa: F811
    """系統未要求減少動態效果:遊戲內關閉動畫時不播翻頁;跟隨系統時照常播。"""
    context, page, errors = open_page(browser, server, motion="no-preference",
                                      prefs={"spotlight": "off", "motion": motion})
    page.evaluate("startLocal()")
    page.wait_for_function("S && S.phase === 'start'")
    page.evaluate("send({type: 'flip_pages', player: S.turn_player, count: 1})")
    page.wait_for_function("S.phase === 'battle'")
    flaps = page.evaluate("document.querySelectorAll('#anim-overlay .fx-page-flap').length")
    assert (flaps == 0) == (motion == "off")
    context.close()
    assert not errors
