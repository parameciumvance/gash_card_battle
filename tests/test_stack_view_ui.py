"""疊放魔物的下方卡片(battle-ui「疊放魔物的下方卡片」)。

Run: python -m pytest tests/test_stack_view_ui.py -q
"""
from tests.test_cheat_editor import browser, page, server  # noqa: F401  共用 fixture
from tests.test_timing_ui import start_as

STACK = """(p) => {
    S = {...S, players: S.players.map((ps, i) => i !== p ? ps
        : {...ps, slots: ps.slots.map((s, j) => j === 0 ? {...s, stack: ['M-028', 'M-027'], top: 'M-027'} : s)})};
    render();
    const s = S.players[p].slots[0];
    zoom(s.top, {kind: 'slot', p, uid: s.uid});
}"""


def under(page):
    return page.evaluate("[...document.querySelectorAll('#zoom-overlay .zoom-stack [data-card]')].map(e => e.dataset.card)")


def test_stacked_mamodo_lists_cards_below_and_back(page):
    tp, _ = start_as(page, "all")
    page.evaluate(STACK, tp)
    assert under(page) == ["M-028"]
    page.locator("#zoom-overlay .zoom-stack [data-card='M-028']").click()
    assert page.evaluate("ZOOM.num") == "M-028" and page.evaluate("ZOOM.ctx") is None
    assert under(page) == []                                                    # 純展示,沒有疊放區
    page.locator("#zoom-actions button", has_text="返回").click()
    assert page.evaluate("ZOOM.num") == "M-027" and under(page) == ["M-028"]


def test_opponent_stack_visible_and_plain_has_none(page):
    tp, _ = start_as(page, "turn")
    page.evaluate(STACK, 1 - tp)
    assert under(page) == ["M-028"]
    page.evaluate("closeZoom()")
    s = page.evaluate(f"S.players[{tp}].slots[0]")
    page.evaluate(f"zoom('{s['top']}', {{kind: 'slot', p: {tp}, uid: {s['uid']}}})")
    assert page.locator("#zoom-overlay .zoom-stack").count() == 0
