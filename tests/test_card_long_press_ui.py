"""長按 / 右鍵直接開啟放大檢視(battle-ui「長按看詳情」)。需要 playwright 與 Chromium。

觸控以 pointer 事件模擬(pointerType touch),放開後的 click 由測試送出,與瀏覽器順序相同。

Run: python -m pytest tests/test_card_long_press_ui.py -q
"""
import pytest

from tests.test_card_action_menu_ui import MENU, page_card, to_battle

ZOOM = "#zoom-overlay:not(.hidden)"


def touch(card, event, dx=0):
    box = card.bounding_box()
    card.dispatch_event(event, {"pointerType": "touch", "isPrimary": True, "bubbles": True,
                                "clientX": box["x"] + 20 + dx, "clientY": box["y"] + 20})


def press(page, card, ms, dx=0):
    """按住 ms 毫秒(期間移動 dx)後放開,再送出放開後的 click。"""
    touch(card, "pointerdown")
    if dx:
        touch(card, "pointermove", dx)
    page.wait_for_timeout(ms)
    touch(card, "pointerup", dx)
    card.dispatch_event("click")


def test_long_press_opens_zoom_without_menu(page):
    tp, me = to_battle(page)
    card = page_card(page, me, 3)                                       # 有「攻擊」的戰術
    touch(card, "pointerdown")
    page.wait_for_selector(ZOOM, timeout=2000)                          # 還沒放開就開啟
    touch(card, "pointerup")
    card.dispatch_event("click")                                        # 放開後的 click 不開選單
    page.wait_for_timeout(100)
    assert page.locator(ZOOM).count() == 1 and page.locator(MENU).count() == 0
    assert page.evaluate("ZOOM.num") == page.evaluate(f"S.players[{me}].book[2]")


def test_short_tap_still_opens_menu(page):
    tp, me = to_battle(page)
    press(page, page_card(page, me, 3), 100)
    page.wait_for_selector(MENU)
    assert page.locator(ZOOM).count() == 0


def test_moving_finger_cancels_long_press(page):
    tp, me = to_battle(page)
    card = page_card(page, me, 3)
    touch(card, "pointerdown")
    touch(card, "pointermove", 30)                                      # 捲動
    page.wait_for_timeout(700)
    assert page.locator(ZOOM).count() == 0


def test_next_tap_after_long_press_works(page):
    tp, me = to_battle(page)
    card = page_card(page, me, 3)
    touch(card, "pointerdown")
    page.wait_for_selector(ZOOM, timeout=2000)
    touch(card, "pointerup")                                            # 放開後沒有 click(例如被瀏覽器吞掉)
    page.evaluate("closeZoom()")
    press(page, card, 100)                                              # 下一次點擊照常開選單
    page.wait_for_selector(MENU)


@pytest.mark.parametrize("pointer", ["mouse", "touch"])
def test_context_menu(page, pointer):
    tp, me = to_battle(page)
    card = page_card(page, me, 3)
    prevented = card.evaluate("""(el, pointer) => {
        const ev = new PointerEvent('contextmenu', {pointerType: pointer, bubbles: true, cancelable: true});
        el.dispatchEvent(ev);
        return ev.defaultPrevented;
    }""", pointer)
    assert prevented                                                    # 不出瀏覽器的選單
    if pointer == "mouse":                                              # 右鍵直接放大
        page.wait_for_selector(ZOOM, timeout=2000)
    else:                                                               # 觸控的長按交給長按計時
        page.wait_for_timeout(100)
        assert page.locator(ZOOM).count() == 0


def test_cards_not_selectable(page):
    # 長按不選取文字;iOS 的 -webkit-touch-callout 在 Chromium 讀不到,無法在此驗證
    to_battle(page)
    assert page.evaluate("getComputedStyle(document.querySelector('#zone-bottom .card')).userSelect") == "none"
