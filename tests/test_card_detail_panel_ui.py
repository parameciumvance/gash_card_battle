"""寬螢幕的卡片詳情面板(battle-ui「寬螢幕的卡片詳情面板」)。需要 playwright 與 Chromium。

level1 預組開局:場上ガッシュ・ベル,翻開第 2 頁 S-025、第 3 頁 S-001(攻擊戰術,預估合計魔力 6000)。

Run: python -m pytest tests/test_card_detail_panel_ui.py -q
"""
from tests.test_timing_ui import send, start_as, zone_of

PANEL = "#detail-panel"


def to_battle(page, me="turn"):
    tp, mine = start_as(page, me)
    send(page, tp, {"type": "flip_pages", "count": 0})
    page.wait_for_function("S.phase === 'battle'")
    return tp, mine


def page_card(page, p, page_no):
    return page.locator(f'[data-book-block="{p}"] [data-page="{page_no}"]').first


def slot_card(page, p):
    return page.locator(f'{zone_of(page, p)} .card[data-zone-kind="mamodo"]').first


def panel_card(page):
    """面板目前顯示的卡號(沒有則 None)。"""
    return page.evaluate("(() => { const c = document.querySelector('#detail-panel .card'); return c ? c._num : null; })()")


def panel_text(page):
    return page.locator(PANEL).text_content()


def test_placeholder_on_wide_and_hidden_on_narrow(page):
    to_battle(page)
    assert page.locator(PANEL).is_visible()
    assert "點選或指向卡片,這裡會顯示詳情" in panel_text(page)
    assert page.locator("#log").is_visible()
    page.set_viewport_size({"width": 390, "height": 800})
    assert page.locator(PANEL).is_hidden()


def test_click_selects_card_and_menu_still_opens(page):
    tp, me = to_battle(page)
    page_card(page, me, 3).click()
    page.wait_for_selector("#card-menu:not(.hidden)")
    assert panel_card(page) == "S-001"
    assert "預估合計魔力 6000" in panel_text(page)
    assert page.locator(f"{PANEL} button", has_text="攻擊").count() == 0          # 面板沒有行動按鈕


def test_hover_shows_temporarily(page):
    tp, me = to_battle(page)
    page_card(page, me, 3).click()
    page.keyboard.press("Escape")
    slot_card(page, 1 - me).hover()
    assert panel_card(page) == "M-001"
    page.mouse.move(640, 5)                                                       # 移開
    assert panel_card(page) == "S-001"


def test_hover_log_card_name(page):
    to_battle(page)
    page.locator("#log .card-ref").first.hover()
    assert panel_card(page) == page.evaluate("[...document.querySelectorAll('#log .card-ref')][0]._num")


def test_card_back_does_not_change_panel(page):
    tp, me = to_battle(page)
    page.evaluate(f"""SESSION = {{...SESSION, viewer: {me}}};
        S.players[{1 - me}].open_pages = S.players[{1 - me}].open_pages.map(e => ({{page: e.page}}));   // 對手視角:只有頁碼
        render();""")
    page_card(page, me, 3).click()
    page.keyboard.press("Escape")
    assert "back" in page_card(page, 1 - me, 2).get_attribute("class")
    page_card(page, 1 - me, 2).hover()                                            # 對手的頁:卡背
    assert panel_card(page) == "S-001"


def test_panel_updates_with_state_and_drops_position_details(page):
    tp, me = to_battle(page)
    page_card(page, me, 3).click()
    page.keyboard.press("Escape")
    page.evaluate(f"""() => {{ const e = S.players[{me}].open_pages.find(x => x.page === 3);
        e.users = e.users.map(u => ({{...u, power: 9000, power_breakdown: [{{kind: 'mamodo', source: 'M-001', amount: 9000}}]}}));
        render(); }}""")
    assert "預估合計魔力 9000" in panel_text(page)
    page.evaluate(f"S.players[{me}].open_pages = S.players[{me}].open_pages.filter(e => e.page !== 3); render();")
    assert panel_card(page) == "S-001" and "預估合計魔力" not in panel_text(page)


def test_panel_card_opens_zoom_and_cleared_on_leave(page):
    tp, me = to_battle(page)
    page_card(page, me, 3).click()
    page.keyboard.press("Escape")
    page.locator(f"{PANEL} .card").click()
    page.wait_for_selector("#zoom-overlay:not(.hidden)")
    page.evaluate("closeZoom(); leaveRoom()")
    page.evaluate("startLocal()")
    page.wait_for_function("S && S.phase === 'start'")
    assert panel_card(page) is None
