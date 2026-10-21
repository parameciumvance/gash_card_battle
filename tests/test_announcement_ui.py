"""維護公告橫幅(battle-ui「維護公告橫幅」)。以 route 攔截 /api/announcement 決定伺服器的公告。

Run: python -m pytest tests/test_announcement_ui.py -q
"""
import json

from tests.test_timing_ui import start_as

ANN = {"id": "m1", "message": {"zh-TW": "今晚 22:00 維護", "en": "Maintenance tonight"}, "until": None}


def serve(page, ann):
    page.unroute("**/api/announcement")
    page.route("**/api/announcement", lambda route: route.fulfill(
        status=200, content_type="application/json", body=json.dumps({"announcement": ann})))
    page.evaluate("refreshAnnouncement()")


def banner(page):
    return page.evaluate("""() => {
        const el = document.getElementById('announcement');
        return el.classList.contains('hidden') ? null : el.querySelector('.ann-text').textContent;
    }""")


def test_banner_on_landing_and_in_game_then_withdrawn(page):
    serve(page, ANN)
    assert banner(page) == "今晚 22:00 維護"                                     # 首頁
    start_as(page, "all")
    assert banner(page) == "今晚 22:00 維護"                                     # 對局畫面
    serve(page, None)
    assert banner(page) is None                                                  # 撤下後移除


def test_dismissed_stays_hidden_until_new_id(page):
    serve(page, ANN)
    page.locator("#announcement .ann-close").click()
    assert banner(page) is None
    page.reload()
    page.wait_for_function("Object.keys(CARDS).length > 0")
    serve(page, ANN)
    assert banner(page) is None                                                  # 同一則不再顯示
    serve(page, {**ANN, "id": "m2"})
    assert banner(page) == "今晚 22:00 維護"                                     # 新的公告再顯示


def test_message_follows_language_and_polls(page):
    page.evaluate("LANG = 'en'")
    serve(page, ANN)
    assert banner(page) == "Maintenance tonight"
    assert page.evaluate("ANN_POLL_MS") == 120000
