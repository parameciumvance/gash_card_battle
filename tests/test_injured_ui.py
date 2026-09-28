"""負傷魔物橫放樣式的瀏覽器測試(battle-ui「負傷魔物的橫放樣式」)。需要 playwright 與 Chromium。

Run: python -m pytest tests/test_injured_ui.py -q
"""
import pytest

from tests.test_cheat_editor import browser, page, server  # noqa: F401  共用 fixture(隔離的伺服器與瀏覽器)

MEASURE = """(injured) => {
  const rect = (el) => { const r = el.getBoundingClientRect();
    return {w: r.width, h: r.height, cx: r.left + r.width / 2, cy: r.top + r.height / 2,
            top: r.top, bottom: r.bottom, left: r.left, right: r.right}; };
  S.players[1].slots[0].injured = injured;
  render();
  const card = document.querySelector('#zone-top [data-zone-kind="mamodo"]');
  const cell = card.parentElement;
  const frame = cell.querySelector('.injured-frame');
  const healthy = document.querySelector('#zone-bottom [data-zone-kind="mamodo"]');
  return {card: rect(card), cell: rect(cell), frame: frame && rect(frame), healthy: rect(healthy)};
}"""


@pytest.fixture
def phone(browser, server):  # noqa: F811
    context = browser.new_context(viewport={"width": 390, "height": 844}, reduced_motion="reduce")
    context.add_init_script("localStorage.setItem('gash-spotlight', 'off')")  # 聚焦遮罩會擋住操作;聚焦測試另開
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(server)
    page.wait_for_function("Object.keys(CARDS).length > 0 && document.querySelector('#cheat-toggle').textContent")
    yield page
    context.close()
    assert not errors


def start_local(page):
    page.evaluate("startLocal()")
    page.wait_for_function("S && S.players[1].slots.length > 0")


@pytest.mark.parametrize("which", ["desktop", "phone"])
def test_injured_card_lies_across_a_portrait_frame(which, page, phone):
    view = page if which == "desktop" else phone
    start_local(view)
    m = view.evaluate(MEASURE, True)
    card, cell, frame, healthy = m["card"], m["cell"], m["frame"], m["healthy"]
    assert 1.35 <= card["w"] / card["h"] <= 1.45                       # 實卡比例的橫卡
    assert card["w"] <= cell["w"] + 0.5                                  # 不超出魔物欄
    assert frame is not None                                             # 虛線直框
    assert abs(frame["w"] - healthy["w"]) < 1 and abs(frame["h"] - healthy["h"]) < 1
    assert abs(frame["cx"] - card["cx"]) < 1 and abs(frame["cy"] - card["cy"]) < 1
    assert frame["top"] < card["top"] and frame["bottom"] > card["bottom"]   # 上下兩端露出:十字
    assert card["left"] < frame["left"] and card["right"] > frame["right"]
    assert abs(cell["w"] - view.evaluate(MEASURE, False)["cell"]["w"]) < 0.5  # 欄位尺寸不變


def test_healed_card_stands_upright_without_frame(page):
    start_local(page)
    page.evaluate(MEASURE, True)
    m = page.evaluate(MEASURE, False)
    assert m["frame"] is None
    assert abs(m["card"]["w"] - m["healthy"]["w"]) < 1 and abs(m["card"]["h"] - m["healthy"]["h"]) < 1


ART_RATIOS = """() => {
  S.players[1].slots[0].injured = true;
  render();
  const ratio = (sel) => { const img = document.querySelector(sel + ' [data-zone-kind="mamodo"] img.art');
    return img.offsetWidth / img.offsetHeight; };    // 版面尺寸(不受旋轉影響)
  return {injured: ratio('#zone-top'), healthy: ratio('#zone-bottom')};
}"""


@pytest.mark.parametrize("which", ["desktop", "phone"])
def test_injured_card_art_shows_same_region_as_upright(which, page, phone):
    """卡圖以 cover 從上方裁切:框的長寬比相同,裁到的範圍才相同。"""
    view = page if which == "desktop" else phone
    start_local(view)
    r = view.evaluate(ART_RATIOS)
    assert abs(r["injured"] - r["healthy"]) < 0.02, r
