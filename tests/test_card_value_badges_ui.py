"""數值徽章是魔力與費用的唯一呈現(battle-ui「文字卡面與卡圖」「魔力與費用的分色」「卡片放大檢視」)。
測試環境沒有安裝卡圖,同時驗證缺卡圖時徽章仍在。需要 playwright 與 Chromium。"""
from tests.test_builder_card_info_ui import builder  # noqa: F401
from tests.test_effect_visibility_ui import slot_card, zoom_slot
from tests.test_spell_user_ui import start_local


def pool_card(page, num):
    return page.locator("#pool-grid .card", has=page.locator(".cnum", has_text=num)).first


def test_pool_shows_values_only_in_badges(builder):  # noqa: F811
    gash, zaker = pool_card(builder, "M-001"), pool_card(builder, "S-001")
    assert gash.locator(".val-badge.val-power").inner_text() == "4000"          # 小卡面只寫數值
    assert zaker.locator(".val-badge.val-cost").inner_text() == "1"
    assert zaker.locator(".val-badge.val-power").inner_text() == "+2000"        # 戰術的魔力加值也用魔力徽章
    assert pool_card(builder, "S-025").locator(".val-badge.val-power").inner_text() == "特殊"
    meta = zaker.locator(".cmeta").inner_text()
    assert "費用" not in meta and "魔力" not in meta and "+2000" not in meta
    assert "傷害 1" in meta and "AD" in meta
    assert "魔力" not in gash.locator(".cmeta").inner_text()


def test_board_badge_shows_number_only(page):
    tp = start_local(page)
    uid = page.evaluate(f"S.players[{tp}].slots[0].uid")
    power = page.evaluate(f"S.players[{tp}].slots[0].power")
    badge = slot_card(page, uid).locator(".val-badge.val-power")
    assert badge.inner_text() == str(power)
    box, name = badge.bounding_box(), slot_card(page, uid).locator(".cname").bounding_box()
    assert box["y"] >= name["y"] + name["height"] - 1                           # 不蓋住卡名


def test_zoom_shows_two_line_power_badge(page):
    tp = start_local(page)
    uid = page.evaluate(f"S.players[{tp}].slots[0].uid")
    zoom_slot(page, tp, uid)
    badge = page.locator("#zoom-card .val-badge.val-power")
    assert badge.is_visible()
    assert badge.inner_text().split() == ["魔力", "4000"]
    assert badge.locator(".val-label").bounding_box()["y"] < badge.locator(".val-num").bounding_box()["y"]
    assert "魔力" not in page.locator("#zoom-card .cmeta").inner_text()


def test_card_number_does_not_overlap_cost_badge(builder):  # noqa: F811
    # 卡號標籤在右下角,費用徽章在右上角的費用格(battle-ui「文字卡面與卡圖」)
    card = pool_card(builder, "S-001")
    num, cost = card.locator(".cnum").bounding_box(), card.locator(".val-badge.val-cost").bounding_box()
    box = card.bounding_box()
    assert num["y"] + num["height"] > box["y"] + box["height"] - 24                # 在底部預留列
    assert cost["y"] + cost["height"] <= num["y"]                                  # 不重疊


def test_zoom_card_number_aligned_with_power_badge(page):
    # 放大檢視的卡號以深色底標籤在最底下右側,與左側的魔力徽章底部對齊、字級相同(battle-ui「放大檢視顯示卡號」)
    tp = start_local(page)
    zoom_slot(page, tp, page.evaluate(f"S.players[{tp}].slots[0].uid"))
    num, badge = page.locator("#zoom-card .cnum"), page.locator("#zoom-card .val-badge.val-power")
    nb, bb = num.bounding_box(), badge.bounding_box()
    assert abs((nb["y"] + nb["height"]) - (bb["y"] + bb["height"])) <= 1
    assert nb["x"] > bb["x"] + bb["width"]
    size = "e => getComputedStyle(e).fontSize"
    assert num.evaluate(size) == badge.evaluate(size)
    assert num.evaluate("e => getComputedStyle(e).backgroundColor") not in ("rgba(0, 0, 0, 0)", "transparent")


def test_zoom_spell_power_badge(page):
    start_local(page)
    page.evaluate("zoom('S-001')")
    assert page.locator("#zoom-card .val-badge.val-power").inner_text().split() == ["魔力", "+2000"]
    assert "魔力" not in page.locator("#zoom-card .cmeta").inner_text()

