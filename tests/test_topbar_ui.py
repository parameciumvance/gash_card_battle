"""頂欄排版的瀏覽器測試(窄螢幕):沒有內容的狀態欄位不佔位置。
需要 playwright 與 Chromium。

Run: python -m pytest tests/test_topbar_ui.py -q
"""
from tests.test_cheat_editor import browser, server  # noqa: F401  共用 fixture(隔離的伺服器與瀏覽器)


def test_phone_landing_topbar_buttons_fit_in_one_row(browser, server):  # noqa: F811
    context = browser.new_context(viewport={"width": 390, "height": 844}, locale="zh-TW")
    page = context.new_page()
    page.goto(server)
    page.wait_for_selector("#landing:not(.hidden)")
    boxes = page.evaluate("""[...document.querySelectorAll('#topbar > button')]
        .filter((b) => !b.classList.contains('hidden'))
        .map((b) => { const r = b.getBoundingClientRect(); return [Math.round(r.top), Math.round(r.left)]; })""")
    assert len(boxes) == 4
    assert len({top for top, _ in boxes}) == 1                             # 同一列,不換行
    assert boxes[0][1] <= 12                                               # 從左側內距開始,前面沒有空欄位的間距
    context.close()
