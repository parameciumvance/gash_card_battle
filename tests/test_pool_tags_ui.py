"""卡池的「其他」類型與標籤篩選(deck-builder「卡池圖示篩選列」「卡池篩選的選取方式」「卡池標籤篩選」)。
需要 playwright 與 Chromium。

Run: python -m pytest tests/test_pool_tags_ui.py -q
"""
from tests.test_cheat_editor import open_local
from tests.test_pool_filters_ui import builder, cards_where, menu, panel, pool_numbers, tile, type_badge  # noqa: F401

ATTRS = ["雷", "重力", "土", "風", "水", "氷", "木", "火"]


def test_other_type_shows_only_mj12(builder):  # noqa: F811
    type_badge(builder, "other").click()
    assert pool_numbers(builder) == [f"MJ-{n:03d}" for n in range(1, 7)]
    assert builder.evaluate("t('builder.type.other')") in type_badge(builder, "other").inner_text()


def test_type_badge_shows_check_when_selected(builder):  # noqa: F811
    badge = type_badge(builder, "spell")
    assert not badge.locator(".filter-check").is_visible()
    badge.click()
    assert badge.locator(".filter-check").is_visible()                    # 多選:勾選的項目打勾


def test_tag_grid_lists_tags(builder):  # noqa: F811
    menu(builder, "tag").click()
    keys = panel(builder, "tag").locator(".filter-tile[data-key]").evaluate_all("(ts) => ts.map((t) => t.dataset.key)")
    assert keys == ["jammer", "intermediate", "superior"] + [f"attr:{a}" for a in ATTRS]
    assert tile(builder, "tag", "attr:氷").inner_text().strip().endswith("冰")      # 屬性名依語言


def pressed(page, key):
    return tile(page, "tag", key).get_attribute("aria-pressed") == "true"


def test_tags_multi_select_with_check(builder):  # noqa: F811
    menu(builder, "tag").click()
    tile(builder, "tag", "superior").click()
    assert panel(builder, "tag").is_visible()                                # 多選:網格保持展開
    tile(builder, "tag", "attr:雷").click()
    expected = cards_where(builder, "c.class === 'superior' && c.attr_name === '雷'")   # 不同組同時符合
    assert len(expected) == 5 and pool_numbers(builder) == expected
    for key in ("superior", "attr:雷"):
        assert pressed(builder, key) and tile(builder, "tag", key).locator(".filter-check").is_visible()
    assert not tile(builder, "tag", "intermediate").locator(".filter-check").is_visible()
    assert "2" in menu(builder, "tag").locator(".filter-summary").inner_text()
    tile(builder, "tag", "attr:雷").click()                                  # 再點一次取消該項
    assert pool_numbers(builder) == cards_where(builder, "c.class === 'superior'")
    assert menu(builder, "tag").locator(".filter-summary").inner_text().strip() == builder.evaluate("t('card.class.superior')")
    panel(builder, "tag").locator(".filter-all").click()                     # 「全部」清除
    assert menu(builder, "tag").locator(".filter-summary").inner_text().strip() == builder.evaluate("t('builder.filter.all')")


def test_tags_exclusive_within_group(builder):  # noqa: F811
    # 中級 / 上級、各屬性之間互斥;干擾與其他組可以同時勾
    menu(builder, "tag").click()
    tile(builder, "tag", "intermediate").click()
    tile(builder, "tag", "superior").click()
    assert pressed(builder, "superior") and not pressed(builder, "intermediate")
    tile(builder, "tag", "attr:雷").click()
    tile(builder, "tag", "attr:水").click()
    assert pressed(builder, "attr:水") and not pressed(builder, "attr:雷")
    tile(builder, "tag", "jammer").click()
    assert pressed(builder, "jammer") and pressed(builder, "superior") and pressed(builder, "attr:水")
    assert pool_numbers(builder) == []                                       # 沒有同時是干擾、上級、水屬性的卡


def test_attr_tag_with_type(builder):  # noqa: F811
    type_badge(builder, "spell").click()
    menu(builder, "tag").click()
    tile(builder, "tag", "attr:雷").click()
    expected = cards_where(builder, "c.type === 'spell' && c.attr_name === '雷'")
    assert expected and pool_numbers(builder) == expected


def test_cheat_pool_has_tag_filter(page):
    open_local(page)
    filters = page.locator("#cheat-filters")
    filters.locator(".filter-menu[data-group=tag]").click()
    filters.locator(".filter-panel[data-group=tag] .filter-tile[data-key=intermediate]").click()
    numbers = page.locator("#cheat-pool-grid .card .cnum").all_text_contents()
    assert numbers and all(page.evaluate(f"CARDS['{n}'].class") == "intermediate" for n in numbers)
