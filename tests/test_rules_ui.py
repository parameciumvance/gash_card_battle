"""規則頁的瀏覽器測試(battle-ui「規則頁」「首頁入口」「回合與時機指示」的連結)。需要 playwright 與 Chromium。

Run: python -m pytest tests/test_rules_ui.py -q
"""
from tests.test_cheat_editor import browser, page, server  # noqa: F401  共用 fixture(聚焦預設關閉)
from tests.test_spotlight_ui import open_page

CURRENT = "#rules-toc .current"


def section_in_view(page, sid):
    """段落已捲到規則內容區的頂端附近。"""
    return page.evaluate(f"""() => {{
        const body = document.getElementById('rules-body');
        const sec = document.getElementById('rules-sec-{sid}');
        const top = sec.getBoundingClientRect().top - body.getBoundingClientRect().top;
        return Math.abs(top) < 40;
    }}""")


def test_landing_entry_opens_and_closes_rules(page):
    page.locator("#entry-rules button").click()
    assert page.locator("#rules-overlay").is_visible()
    assert page.locator("#rules-body .rules-section").count() >= 11
    page.locator("#rules-close").click()
    assert not page.locator("#rules-overlay").is_visible()
    assert page.locator("#landing").is_visible()


def test_jump_to_section_marks_toc(page):
    page.evaluate("openRules('battle')")
    page.wait_for_function("document.querySelector('#rules-toc .current')")
    assert page.locator(CURRENT).get_attribute("data-section") == "battle"
    assert section_in_view(page, "battle")


def test_timing_step_and_hint_link_open_matching_section(page):
    page.evaluate("startLocal()")
    page.wait_for_function("S && S.phase === 'start'")
    page.evaluate("send({type: 'flip_pages', player: S.turn_player, count: 0})")
    page.wait_for_function("S.phase === 'battle'")
    page.locator('#timing-track [data-step="nonbattle"]').click()
    assert page.locator(CURRENT).get_attribute("data-section") == "actions"
    page.locator("#rules-close").click()
    if not page.locator("#action-bar .hint-details").count():
        page.locator("#action-bar .hint-toggle").click()
    page.locator("#action-bar .hint-details li", has_text="宣告攻擊").locator(".rule-link").click()
    assert page.locator(CURRENT).get_attribute("data-section") == "battle"
    assert section_in_view(page, "battle")


def test_rules_in_game_do_not_block_play(browser, server):  # noqa: F811
    context, page, errors = open_page(browser, server, prefs={"spotlight": "off"})
    page.select_option("#npc-level", "dummy")
    page.locator("#entry-npc button").click()
    page.wait_for_function("SESSION && SESSION.mode === 'npc' && S && R && R.awaited_player === 0", timeout=20000)
    page.locator("#rules-toggle").click()
    assert page.locator("#rules-overlay").is_visible()
    before = page.evaluate("S.event_count")
    page.evaluate("""async () => {
        if (S.phase === 'start') await send({type: 'flip_pages', player: 0, count: 0});
        await send({type: 'pass', player: 0});
    }""")
    page.wait_for_function(f"S.event_count > {before} + 2", timeout=20000)   # NPC 照常回應並推送
    assert page.locator("#rules-overlay").is_visible()
    page.locator("#rules-close").click()
    assert not page.locator("#rules-overlay").is_visible()
    context.close()
    assert not errors


def test_icons_use_installed_card_art(page):
    page.evaluate("openRules('icons')")
    page.wait_for_function("document.querySelectorAll('#rules-body .icon-crop').length >= 5")
    assert page.locator("#rules-body .rules-figure img").count() >= 1
    assert page.locator("#rules-body .rules-missing-art").count() == 0


def test_icons_fall_back_to_text_without_card_art(browser, server):  # noqa: F811
    context = browser.new_context(viewport={"width": 1280, "height": 900}, reduced_motion="reduce")
    context.route("**/static/assets/cards/**", lambda route: route.fulfill(status=404))
    page = context.new_page()
    page.goto(server)
    page.wait_for_function("Object.keys(CARDS).length > 0 && RULES")
    page.evaluate("openRules('icons')")
    page.wait_for_function("document.querySelector('#rules-body .rules-missing-art')")
    assert page.locator("#rules-body .icon-crop").count() == 0
    labels = page.locator("#rules-body .icon-fallback").all_text_contents()
    assert {"A", "D", "NO BATTLE", "BATTLE", "CUT-IN"} <= set(labels)
    assert page.locator("#rules-body .rules-section").count() >= 11       # 其餘段落照常
    context.close()
