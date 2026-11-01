"""查閱賽季範圍(battle-ui「規則頁的賽季段落」「設定頁的賽季選單」、deck-builder「魔書的賽季標示」)。

Run: python -m pytest tests/test_season_reference_ui.py -q
"""
import pytest

from tests.test_rules_ui import CURRENT, section_in_view


def season_rows(page):
    """規則頁賽季表的每一列:{賽季: [各欄文字]}。"""
    return page.evaluate("""() => Object.fromEntries([...document.querySelectorAll('#rules-sec-seasons tbody tr')]
        .map((tr) => [tr.dataset.season, [...tr.children].map((td) => td.textContent.trim())]))""")


def headers(page):
    return page.locator("#rules-sec-seasons thead th").all_text_contents()


def test_rules_page_lists_season_ranges_and_products(page):
    page.evaluate("openRules('seasons')")
    page.wait_for_function("document.querySelector('#rules-sec-seasons tbody tr')")
    assert page.locator(CURRENT).get_attribute("data-section") == "seasons"
    assert section_in_view(page, "seasons")
    head = headers(page)
    rows = season_rows(page)
    assert set(rows) == {"1", "2", "3"}
    col = {h: i for i, h in enumerate(head)}
    s1, s3 = rows["1"], rows["3"]
    assert s1[col["M"]] == "001–015" and s1[col["S"]] == "001–028" and s1[col["PR"]] == "001–002"
    assert s1[col["Ex"]] == "—"                                             # 第 1 賽季沒有 Ex 卡
    assert s3[col["M"]] == "001–069" and s3[col["Ex"]] == "001–048"
    product = page.evaluate("(k) => t(k)", "product.level-1")
    assert s1[-1] == product                                                # 第 1 賽季新增 LEVEL:1
    assert page.evaluate("(k) => t(k)", "product.level-3") in s3[-1]
    assert page.evaluate("(k) => t(k)", "product.ex-sheet-2") in s3[-1]
    assert page.evaluate("(k) => t(k)", "product.level-1") not in s3[-1]   # 只列新增的產品
    note = page.locator("#rules-sec-seasons .rules-season-note").text_content()
    assert "Ex-000" in note and "4" in note


def test_season_table_follows_definition(page):
    page.evaluate("""() => {
        SEASONS = {...SEASONS, seasons: {...SEASONS.seasons, 3: {...SEASONS.seasons[3], M: 70}}};
        document.getElementById('rules-body').replaceChildren();
        delete document.getElementById('rules-body').dataset.built;
        openRules('seasons');
    }""")
    page.wait_for_function("document.querySelector('#rules-sec-seasons tbody tr')")
    col = headers(page).index("M")
    assert season_rows(page)["3"][col] == "001–070"


@pytest.mark.parametrize("entry,select", [("npc", "season-npc"), ("friend", "season-friend"),
                                          ("local", "season-local"), ("tables", "season-tables")])
def test_season_select_help_opens_rules(page, entry, select):
    page.locator(f"#entry-{entry}").click()
    page.locator(f"#{select}").select_option("2")
    help_btn = page.locator(f"#{select}-label .season-help")
    assert help_btn.is_visible()
    help_btn.click()
    assert page.locator("#rules-overlay").is_visible()
    assert page.locator(CURRENT).get_attribute("data-section") == "seasons"
    page.locator("#rules-close").click()
    assert page.locator(f"#{select}").input_value() == "2"                 # 選擇不變


def test_builder_season_tag_opens_rules(page):
    page.locator("#entry-builder").click()
    page.evaluate("B.deck.pages[0] = B.deck.pages[0] || 'M-030'; renderValidation()")   # 有卡才顯示賽季標示
    page.wait_for_function("!document.getElementById('builder-season').classList.contains('hidden')")
    before = page.evaluate("JSON.stringify(B.deck.pages)")
    page.locator("#builder-season").click()
    assert page.locator("#rules-overlay").is_visible()
    assert page.locator(CURRENT).get_attribute("data-section") == "seasons"
    page.locator("#rules-close").click()
    assert page.evaluate("JSON.stringify(B.deck.pages)") == before


CONTRAST = """(sel) => {
    // WCAG 對比度:文字色對元素自身背景(背景透明時往上找第一個不透明的祖先)
    const rgb = (c) => c.match(/[\\d.]+/g).map(Number);
    const lum = ([r, g, b]) => [r, g, b].map((v) => { v /= 255; return v <= .03928 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4; })
        .reduce((a, v, i) => a + v * [.2126, .7152, .0722][i], 0);
    const node = document.querySelector(sel);
    let bg = null;
    for (let e = node; e && !bg; e = e.parentElement) {
        const c = getComputedStyle(e).backgroundColor, v = rgb(c);
        if (v.length < 4 || v[3] > 0) bg = v;
    }
    const [a, b] = [lum(rgb(getComputedStyle(node).color)), lum(bg || [255, 255, 255])].sort((x, y) => y - x);
    return (a + .05) / (b + .05);
}"""


def test_builder_season_tag_is_readable(page):
    page.locator("#entry-builder").click()
    page.evaluate("B.deck.pages[0] = B.deck.pages[0] || 'M-030'; renderValidation()")
    page.wait_for_function("!document.getElementById('builder-season').classList.contains('hidden')")
    assert page.evaluate(CONTRAST, "#builder-season") >= 4.5
