"""語言選擇的瀏覽器測試(battle-ui「語言選擇」「錯誤訊息依錯誤碼顯示」「i18n 字典」、
battle-api「預組魔本探索」、deck-builder「即時合法性提示」)。需要 playwright 與 Chromium。

Run: python -m pytest tests/test_language_ui.py -q
"""
import json
import re
from pathlib import Path

import pytest

from tests.test_cheat_editor import browser, server  # noqa: F401  共用 fixture(隔離的伺服器與瀏覽器)

ROOT = Path(__file__).resolve().parents[1]


def dict_of(lang):
    return json.loads((ROOT / f"frontend/i18n/{lang}.json").read_text(encoding="utf-8"))


def loaded(page):
    page.wait_for_function("Object.keys(CARDS).length > 0 && document.getElementById('lang-toggle').textContent")


def open_lang(browser, server, locale, *, path="/"):  # noqa: F811
    """以瀏覽器語言 locale 開頁(未記住任何語言選擇)。"""
    context = browser.new_context(viewport={"width": 1280, "height": 900}, reduced_motion="reduce", locale=locale)
    context.add_init_script("localStorage.setItem('gash-spotlight', 'off')")
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(server + path)
    loaded(page)
    return context, page, errors


@pytest.fixture
def opened(browser, server):  # noqa: F811
    contexts = []

    def make(locale, **kw):
        context, page, errors = open_lang(browser, server, locale, **kw)
        contexts.append((context, errors))
        return page

    yield make
    for context, errors in contexts:
        context.close()
        assert not errors


def current_lang(page):
    return page.evaluate("document.documentElement.lang")


def pick_language(page, code):
    page.locator("#lang-toggle").click()
    with page.expect_navigation():
        page.locator(f'#info-body button[data-lang="{code}"]').click()
    loaded(page)


# ---------------------------------------------------------------- 預設與選擇

def test_default_follows_browser_japanese(opened):
    page = opened("ja-JP")
    assert current_lang(page) == "ja"
    assert "日本語" in page.locator("#lang-toggle").text_content()
    assert page.locator("#entry-npc .entry-title").text_content() == dict_of("ja")["ui.landing.npc"]


def test_default_follows_browser_chinese(opened):
    page = opened("zh-TW")
    assert current_lang(page) == "zh-TW"
    assert page.locator("#entry-npc .entry-title").text_content() == "NPC 對戰"


def test_other_browser_language_defaults_to_english(opened):
    page = opened("fr-FR")
    assert current_lang(page) == "en"
    assert "English" in page.locator("#lang-toggle").text_content()
    assert page.locator("#entry-npc .entry-title").text_content() == dict_of("en")["ui.landing.npc"]


def test_language_dialog_lists_languages_in_their_own_names(opened):
    page = opened("zh-TW")
    page.locator("#lang-toggle").click()
    buttons = page.locator("#info-body button[data-lang]")
    assert buttons.all_text_contents() == ["中文", "English", "日本語"]
    assert page.locator('#info-body button[data-lang="zh-TW"]').get_attribute("aria-pressed") == "true"


def test_choice_is_remembered(opened):
    page = opened("ja-JP")
    pick_language(page, "en")
    assert current_lang(page) == "en"
    assert page.evaluate("localStorage.getItem('gash-lang')") == "en"
    page.reload()
    loaded(page)
    assert current_lang(page) == "en"
    assert page.locator("#entry-npc .entry-title").text_content() == dict_of("en")["ui.landing.npc"]


def test_language_button_on_every_screen(opened):
    page = opened("en-US")
    page.locator("#entry-npc").click()
    assert page.locator("#lang-toggle").is_visible()
    page.locator("#setup-back").click()
    page.locator("#entry-builder").click()
    assert page.locator("#lang-toggle").is_visible()


# ---------------------------------------------------------------- 對局中切換、同房不同語言

def test_switch_language_in_game_and_rooms_with_different_languages(opened, server):  # noqa: F811
    host = opened("zh-TW")
    host.locator("#entry-friend").click()
    host.locator("#friend-submit").click()
    host.wait_for_function("document.getElementById('waiting-code').textContent")
    code = host.locator("#waiting-code").text_content()

    guest = opened("en-US", path=f"/?join={code}")
    guest.locator("#friend-submit").click()
    guest.wait_for_function("S && !document.getElementById('layout').classList.contains('hidden')", timeout=15000)
    host.wait_for_function("S && !document.getElementById('layout').classList.contains('hidden')", timeout=15000)

    zh, en, ja = dict_of("zh-TW"), dict_of("en"), dict_of("ja")
    first_log = "document.querySelector('#log .ev') && document.querySelector('#log .ev').textContent"
    assert host.evaluate(first_log) == zh["log.game_started"]
    guest.wait_for_function(f"{first_log} === {json.dumps(en['log.game_started'])}")

    guest.evaluate("window.notReloaded = true")
    turn_before = host.evaluate("S.turn_no")
    pick_language(host, "ja")
    host.wait_for_function("S && !document.getElementById('layout').classList.contains('hidden')", timeout=15000)
    assert current_lang(host) == "ja"
    assert host.evaluate("SESSION.code") == code and host.evaluate("S.turn_no") == turn_before
    host.wait_for_function(f"{first_log} === {json.dumps(ja['log.game_started'])}")
    names = host.locator("#board .card .cname").all_text_contents()
    ja_texts = json.loads((ROOT / "data/cards.ja.json").read_text(encoding="utf-8"))
    assert "ガッシュ・ベル" in names or any(n in names for n in (c["name"] for c in ja_texts.values()))

    assert guest.evaluate("window.notReloaded") is True                     # 對手畫面不受影響
    assert current_lang(guest) == "en"
    assert guest.evaluate(first_log) == en["log.game_started"]


# ---------------------------------------------------------------- 錯誤碼、預組名稱、卡片文字、構築器

def test_error_message_follows_language(opened):
    page = opened("en-US")
    page.locator("#entry-friend").click()
    page.locator('#friend-mode [data-mode="join"]').click()
    page.fill("#join-code", "ZZZZZZ")
    page.locator("#friend-submit").click()
    page.wait_for_function("!document.getElementById('toast').classList.contains('hidden') && document.getElementById('toast').textContent")
    toast = page.locator("#toast").text_content()
    assert dict_of("en")["error.room.not_found"] in toast
    assert "房間不存在" not in toast


def test_unknown_error_code_falls_back_to_server_message(opened):
    page = opened("en-US")
    msg = page.evaluate("""async () => {
        const orig = window.fetch;
        window.fetch = async () => new Response(JSON.stringify({detail: {code: 'no.such_code', message: '伺服器原文'}}),
                                                 {status: 400, headers: {'Content-Type': 'application/json'}});
        try { await api('/api/whatever'); } catch (err) { return err.message; } finally { window.fetch = orig; }
    }""")
    assert msg == "伺服器原文"


def test_preset_names_follow_language(opened):
    page = opened("en-US")
    page.locator("#entry-npc").click()
    options = page.locator("#deck-npc option").all_text_contents()
    en = dict_of("en")
    assert any(en["deck.level1"] in o for o in options)
    assert any(en["deck.level2"] in o for o in options)


def test_japanese_card_text(opened):
    page = opened("ja-JP")
    page.evaluate("zoom('M-001')")
    card = page.locator("#zoom-card .card")
    assert card.locator(".cname").text_content() == "ガッシュ・ベル《やさしい王様》"
    effect_ja = next(c for c in json.loads((ROOT / "data/cards.json").read_text(encoding="utf-8"))
                     if c["number"] == "M-001")["effect_ja"]
    assert card.locator(".ceffect").text_content() == effect_ja
    assert card.locator(".cname-ja").count() == 0 or not card.locator(".cname-ja").text_content()


def test_english_card_text_shows_japanese_subtitle(opened):
    page = opened("en-US")
    page.evaluate("zoom('M-001')")
    card = page.locator("#zoom-card .card")
    assert card.locator(".cname").text_content() == "Zatch Bell (Kind King)"
    assert card.locator(".cname-ja").text_content() == "ガッシュ・ベル"


def test_builder_violations_follow_language(opened):
    page = opened("en-US")
    page.locator("#entry-builder").click()
    page.wait_for_function("document.getElementById('builder-validation').textContent")
    text = page.locator("#builder-validation").text_content()
    expected = page.evaluate("validateDeckPages(B.deck.pages).map((e) => t(e.key, e.params))")
    assert expected and all(e in text for e in expected)
    assert not re.search(r"[\u4e00-\u9fff]", text)                      # 不是中文
