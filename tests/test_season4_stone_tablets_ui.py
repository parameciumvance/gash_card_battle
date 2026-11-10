"""資訊列的石版標籤(battle-ui「資訊列的石版標籤」,season4-stone-tablets)。"""
from tests.test_jammer_tag_ui import open_builder, pool_card


def test_stone_tablet_tag(browser, server):
    context, page, errors = open_builder(browser, server)
    page.evaluate("zoom('Ex-056')")
    assert page.locator("#zoom-card .cmeta .ctag-stone").all_text_contents() == ["石版"]
    assert pool_card(page, "Ex-057").locator(".cmeta .ctag-stone").all_text_contents() == ["石版"]
    page.evaluate("zoom('M-001')")
    assert page.locator("#zoom-card .cmeta .ctag-stone").count() == 0
    context.close()
    assert not errors
