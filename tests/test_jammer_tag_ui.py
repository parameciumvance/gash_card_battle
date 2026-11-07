"""資訊列的干擾標籤(battle-ui「資訊列的干擾標籤」)與英文的 CUT-IN 用語。需要 playwright 與 Chromium。

Run: python -m pytest tests/test_jammer_tag_ui.py -q
"""
import json

import pytest

from tests.conftest import ROOT

DESKTOP = {"width": 1280, "height": 900}


def open_builder(browser, server, locale="zh-TW"):
    context = browser.new_context(viewport=DESKTOP, reduced_motion="reduce", locale=locale)
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(server + "/?builder=1")
    page.wait_for_function("Object.keys(CARDS).length > 0 && document.querySelector('#pool-grid .card')")
    return context, page, errors


def pool_card(page, num):
    return page.locator(f'#pool-grid .card[aria-label^="{num} "]')


def zoom_tags(page, num):
    page.evaluate(f"zoom('{num}')")
    return page.locator("#zoom-card .cmeta .ctag-jammer").all_text_contents()


@pytest.mark.parametrize("num", ["M-026", "M-032", "M-065", "Ex-034"])
def test_jammer_card_has_tag(browser, server, num):
    context, page, errors = open_builder(browser, server)
    assert zoom_tags(page, num) == ["干擾"]
    assert pool_card(page, num).locator(".cmeta .ctag-jammer").all_text_contents() == ["干擾"]
    context.close()
    assert not errors


def test_two_icon_card_has_one_tag_and_plain_card_none(browser, server):
    context, page, errors = open_builder(browser, server)
    assert pool_card(page, "M-080").locator(".cmeta .ctag-jammer").count() == 1   # 《乱入》干擾、《バトル乱入》BATTLE
    assert zoom_tags(page, "M-001") == []
    assert pool_card(page, "S-001").locator(".ctag-jammer").count() == 0
    context.close()
    assert not errors


def test_english_tag_is_cut_in(browser, server):
    context, page, errors = open_builder(browser, server, locale="en")
    page.wait_for_function("LANG === 'en'")
    assert zoom_tags(page, "M-026") == ["CUT-IN"]
    context.close()
    assert not errors


def _values(node):
    if isinstance(node, dict):
        for v in node.values():
            yield from _values(v)
    elif isinstance(node, list):
        for v in node:
            yield from _values(v)
    elif isinstance(node, str):
        yield node


def test_english_texts_use_cut_in():
    # 英文顯示文字一律稱 CUT-IN(英文版卡面圖示的印刷文字),不用 Jammer;鍵名等識別字不在此限
    for path in ("frontend/i18n/en.json", "frontend/i18n/rules.en.json", "data/cards.en.json"):
        texts = _values(json.loads((ROOT / path).read_text(encoding="utf-8")))
        bad = [x for x in texts if "jammer" in x.replace("{jammer}", "").lower()]   # {jammer} 是佔位符
        assert not bad, (path, bad)
