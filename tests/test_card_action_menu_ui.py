"""卡片行動選單(battle-ui「卡片行動選單」「卡片放大檢視」)。需要 playwright 與 Chromium。

level1 預組開局:場上ガッシュ・ベル,翻開第 2 頁 S-025(防禦)、第 3 頁 S-001(攻防,攻擊用)。

Run: python -m pytest tests/test_card_action_menu_ui.py -q
"""
from tests.test_timing_ui import send, start_as

MENU = "#card-menu:not(.hidden)"


def to_battle(page, me="turn"):
    tp, mine = start_as(page, me)
    send(page, tp, {"type": "flip_pages", "count": 0})
    page.wait_for_function("S.phase === 'battle'")
    return tp, mine


def page_card(page, p, page_no):
    return page.locator(f'[data-book-block="{p}"] [data-page="{page_no}"]').first


def slot_card(page, p):
    zone = "#zone-top" if page.evaluate(f"topPlayerIndex() === {p}") else "#zone-bottom"
    return page.locator(f'{zone} .card[data-zone-kind="mamodo"]').first


def menu_items(page):
    """選單的 [(按鈕文字, 啟用, 原因)]。"""
    return page.evaluate("""() => [...document.querySelectorAll('#card-menu .card-menu-item')].map(row => {
        const b = row.querySelector('button'), why = row.querySelector('.card-menu-reason');
        return [b.textContent, !b.disabled, why ? why.textContent : null];
    })""")


def test_attack_from_menu(page):
    tp, me = to_battle(page)
    page_card(page, me, 3).click()
    page.wait_for_selector(MENU)
    assert menu_items(page) == [["攻擊", True, None], ["詳情", True, None]]
    assert not page.locator("#zoom-overlay").is_visible()                 # 不再直接開放大檢視
    page.locator("#card-menu button", has_text="攻擊").click()
    page.wait_for_function("S.battle_in")
    assert page.locator(MENU).count() == 0


def test_disabled_item_shows_reason_and_details_opens_zoom(page):
    tp, me = to_battle(page)
    page_card(page, me, 2).click()                                        # S-025:只有防禦圖示
    page.wait_for_selector(MENU)
    assert menu_items(page) == [["防禦", False, "對手攻擊時才能用來防禦"], ["詳情", True, None]]
    page.locator("#card-menu button", has_text="詳情").click()
    page.wait_for_selector("#zoom-overlay:not(.hidden)")
    assert page.locator(MENU).count() == 0
    assert page.locator("#zoom-actions button", has_text="防禦").is_disabled()   # 放大檢視照舊有按鈕


def test_card_without_actions_opens_zoom_directly(page):
    tp, me = to_battle(page)
    page.evaluate(f"SESSION = {{...SESSION, viewer: {me}}}; render();")
    slot_card(page, 1 - me).click()                                       # 對手的魔物:沒有行動
    page.wait_for_selector("#zoom-overlay:not(.hidden)")
    assert page.locator(MENU).count() == 0


def test_switch_and_close(page):
    tp, me = to_battle(page)
    page_card(page, me, 3).click()
    page.wait_for_selector(MENU)
    page_card(page, me, 2).click()                                        # 換成另一張卡
    assert menu_items(page)[0][0] == "防禦"
    page.mouse.click(5, 300)                                              # 點空白處
    assert page.locator(MENU).count() == 0
    page_card(page, me, 3).click()
    page.wait_for_selector(MENU)
    page.keyboard.press("Escape")
    assert page.locator(MENU).count() == 0


def test_menu_stays_inside_viewport_on_narrow_screen(page):
    page.set_viewport_size({"width": 390, "height": 800})
    tp, me = to_battle(page)
    for page_no in (2, 3):
        page_card(page, me, page_no).click()
        page.wait_for_selector(MENU)
        box = page.locator("#card-menu").bounding_box()
        assert box["x"] >= 0 and box["x"] + box["width"] <= 390
        assert box["y"] >= 0 and box["y"] + box["height"] <= 800


def test_pick_target_from_menu(page):
    tp, me = to_battle(page)
    page.evaluate(f"""() => {{
        const e = S.players[{me}].open_pages.find(x => x.page === 3);
        e.users = [e.users[0], {{...e.users[0], slot_uid: 99}}];      // 兩隻可用:要在場上選
        S.players[{me}].slots.push({{...S.players[{me}].slots[0], uid: 99}});
        render();
    }}""")
    page_card(page, me, 3).click()
    page.locator("#card-menu button", has_text="攻擊").click()
    page.wait_for_function("PICK && PICK.local")
    slot_card(page, me).click()
    page.wait_for_selector(MENU)
    items = menu_items(page)
    assert items[0][0].startswith("選擇") and items[0][1] and items[-1][0] == "詳情"
    page.evaluate("window.picked = null; LOCAL_PICK.onpick = (v) => { window.picked = v; }")
    page.locator("#card-menu button").first.click()
    page.wait_for_function("window.picked !== null")
    assert page.locator(MENU).count() == 0


def test_menu_in_book_grid(page):
    tp, me = to_battle(page)
    page.evaluate(f"""() => {{
        S.players[{me}].any_page_spells = [{{page: 5, card: S.players[{me}].book[4], cost: 1,
            users: S.players[{me}].open_pages.find(x => x.page === 3).users}}];
        render(); showBookReview({me});
    }}""")
    page.locator('#book-review-overlay .review-cell[data-page="5"] .card').click()
    page.wait_for_selector(MENU)
    assert menu_items(page)[0][0] == "攻擊"
    assert page.evaluate("getComputedStyle(document.getElementById('card-menu')).zIndex") > \
        page.evaluate("getComputedStyle(document.getElementById('book-review-overlay')).zIndex")


def test_menu_closes_when_card_leaves(page):
    tp, me = to_battle(page)
    page_card(page, me, 3).click()
    page.wait_for_selector(MENU)
    page.evaluate(f"S.players[{me}].open_pages = S.players[{me}].open_pages.filter(e => e.page !== 3); render();")
    assert page.locator(MENU).count() == 0


def test_menu_updates_with_state(page):
    tp, me = to_battle(page)
    page_card(page, me, 3).click()
    page.wait_for_selector(MENU)
    page.evaluate(f"S.players[{me}].mp = 0; render();")
    assert menu_items(page)[0][1:] == [False, "MP 不足（目前 0，需要 1）"]


def test_menu_blocked_while_sending(page):
    tp, me = to_battle(page)
    page_card(page, me, 3).click()
    page.wait_for_selector(MENU)
    page.evaluate("document.body.classList.add('sending')")
    assert page.evaluate("getComputedStyle(document.querySelector('#card-menu button')).pointerEvents") == "none"
