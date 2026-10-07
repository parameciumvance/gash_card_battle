"""更新內容的瀏覽器測試(battle-ui「更新內容」)。
以 route 換成固定的測試資料,不隨實際發布的版本變動;已確認的版本由各測試自己設定,
不沿用共用 fixture 的預設(預設把 repo 中最新一版記為已確認)。需要 playwright 與 Chromium。

Run: python -m pytest tests/test_release_notes_ui.py -q
"""
import json

import pytest

from tests.test_cheat_editor import browser, server  # noqa: F401  共用 fixture(隔離的伺服器與瀏覽器)

POPUP = "#info-overlay:not(.hidden)"
RELEASES = {
    "zh-TW": {"releases": [
        {"version": "v0.10.0", "date": "2026-10-08",
         "items": [{"kind": "new", "text": "對局加入音效"}, {"kind": "fix", "text": "魔本網格對齊"}]},
        {"version": "v0.9.3", "date": "2026-10-06", "items": [{"kind": "change", "text": "圖片顯示速度優化"}]},
        {"version": "v0.9.2", "date": "2026-10-06", "title": "公開上線", "items": []},
    ]},
    "ja": {"releases": [
        {"version": "v0.10.0", "date": "2026-10-08",
         "items": [{"kind": "new", "text": "効果音を追加"}, {"kind": "fix", "text": "魔本の表示を整列"}]},
        {"version": "v0.9.3", "date": "2026-10-06", "items": [{"kind": "change", "text": "カード画像の表示を高速化"}]},
        {"version": "v0.9.2", "date": "2026-10-06", "title": "公開開始", "items": []},
    ]},
}


def open_page(browser, server, *, locale="zh-TW", seen=None, path="/"):  # noqa: F811
    context = browser.new_context(viewport={"width": 1280, "height": 900}, locale=locale)
    context.add_init_script("localStorage.setItem('gash-spotlight', 'off')")
    # 第一次載入時設定(或清除)已確認的版本,蓋過共用 fixture 的預設;重新整理不再覆蓋
    value = f"localStorage.setItem('gash-release-seen', '{seen}')" if seen else "localStorage.removeItem('gash-release-seen')"
    context.add_init_script(f"if (!sessionStorage.getItem('seeded')) {{ {value}; sessionStorage.setItem('seeded', '1'); }}")
    lang = "ja" if locale == "ja" else "zh-TW"
    context.route("**/static/i18n/releases.*.json", lambda route: route.fulfill(
        status=200, content_type="application/json", body=json.dumps(RELEASES[lang], ensure_ascii=False)))
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(server + path)
    page.wait_for_function("Object.keys(CARDS).length > 0")
    return context, page, errors


def lines(page):
    return page.locator("#info-body li").all_text_contents()


def test_latest_release_pops_up_on_landing(browser, server):  # noqa: F811
    context, page, errors = open_page(browser, server)
    page.wait_for_selector(POPUP)
    assert "v0.10.0" in page.locator("#info-title").text_content()
    assert lines(page) == ["[新功能] 對局加入音效", "[修正] 魔本網格對齊"]
    assert "v0.9.3" not in page.locator("#info-body").text_content()     # 只顯示最新一版
    assert page.locator("#info-close").text_content() == "確認"
    context.close()
    assert not errors


def test_confirm_stops_popup_until_newer_release(browser, server):  # noqa: F811
    context, page, errors = open_page(browser, server)
    page.wait_for_selector(POPUP)
    page.locator("#info-close").click()
    assert page.evaluate("localStorage.getItem('gash-release-seen')") == "v0.10.0"
    page.reload()
    page.wait_for_function("Object.keys(CARDS).length > 0")
    page.wait_for_selector("#landing:not(.hidden)")
    page.wait_for_timeout(300)
    assert page.locator(POPUP).count() == 0
    context.close()
    assert not errors


def test_older_confirmed_version_pops_up_again(browser, server):  # noqa: F811
    context, page, errors = open_page(browser, server, seen="v0.9.3")
    page.wait_for_selector(POPUP)
    assert "v0.10.0" in page.locator("#info-title").text_content()
    context.close()
    assert not errors


def test_closing_without_confirm(browser, server):  # noqa: F811
    context, page, errors = open_page(browser, server)
    page.wait_for_selector(POPUP)
    page.mouse.click(5, 300)                                               # 點遮罩關閉,沒有按確認
    assert page.locator(POPUP).count() == 0
    assert page.evaluate("localStorage.getItem('gash-release-seen')") is None
    page.evaluate("openSetup('npc')")
    page.evaluate("show('landing')")
    page.wait_for_timeout(200)
    assert page.locator(POPUP).count() == 0                               # 同一次載入不重複跳出
    page.reload()
    page.wait_for_selector(POPUP)                                          # 重新整理後再跳出
    context.close()
    assert not errors


def test_room_link_does_not_pop_up_until_back_to_landing(browser, server):  # noqa: F811
    context, page, errors = open_page(browser, server, seen="v0.10.0")
    page.evaluate("startLocal()")
    page.wait_for_function("S && S.phase === 'start'")
    page.evaluate("localStorage.removeItem('gash-release-seen')")
    page.reload()                                                          # 網址帶 ?room=,直接回到對局
    page.wait_for_function("S && !document.getElementById('layout').classList.contains('hidden')")
    page.wait_for_timeout(300)
    assert page.locator(POPUP).count() == 0
    page.evaluate("leaveRoom()")
    page.wait_for_selector(POPUP)
    assert "v0.10.0" in page.locator("#info-title").text_content()
    context.close()
    assert not errors


def test_starting_a_game_closes_the_popup(browser, server):  # noqa: F811
    context, page, errors = open_page(browser, server)
    page.wait_for_selector(POPUP)
    page.evaluate("startLocal()")
    page.wait_for_function("S && S.phase === 'start'")
    assert page.locator(POPUP).count() == 0                               # 對局中不顯示
    context.close()
    assert not errors


def test_history_lists_all_releases(browser, server):  # noqa: F811
    context, page, errors = open_page(browser, server, seen="v0.10.0")
    page.wait_for_selector("#landing:not(.hidden)")
    page.locator("#release-open").click()
    page.wait_for_selector(POPUP)
    sections = page.locator("#info-body .release")
    assert sections.count() == 3
    heads = sections.locator("h4 > span:first-child").all_text_contents()
    assert heads == ["v0.10.0", "v0.9.3", "v0.9.2 公開上線"]                 # 新的在上;標題接在版本後
    assert sections.nth(2).locator("li").count() == 0                     # 只有標題,沒有條目
    assert "2026-10-06" in sections.nth(2).text_content()
    assert page.locator("#info-close").text_content() == "關閉"
    page.locator("#info-close").click()
    assert page.locator(POPUP).count() == 0
    assert page.evaluate("localStorage.getItem('gash-release-seen')") == "v0.10.0"
    context.close()
    assert not errors


@pytest.mark.parametrize("locale", ["ja"])
def test_release_in_japanese(browser, server, locale):  # noqa: F811
    context, page, errors = open_page(browser, server, locale=locale)
    page.wait_for_selector(POPUP)
    assert lines(page) == ["[新機能] 効果音を追加", "[修正] 魔本の表示を整列"]
    assert page.locator("#info-close").text_content() == "確認"
    context.close()
    assert not errors
