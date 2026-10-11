"""決策開始時自動開啟棄牌區 / 魔書(battle-ui「選書對話框」):目標都在同一處、場上沒有目標時自動開啟,
每個決策只自動開啟一次。以合成的決策批次模擬 M-025(先從棄牌區選魔物,再選魔書的空頁)。

Run: python -m pytest tests/test_auto_open_pick_ui.py -q
"""
from tests.test_cheat_editor import browser, page, server  # noqa: F401  共用 fixture
from tests.test_timing_ui import start_as

PUSH = """([kind, options]) => {
    const me = S.turn_player;
    const opts = options.map((o) => ({...o, player: o.player === 'me' ? me : o.player}));
    applyPayload({state: {...S, pending: {kind, player: me, source: 'M-025', options: opts}}, actor: me,
                  events: [{type: 'choice_required', kind, player: me, seq: animSeq}]});
    return me;
}"""


def is_open(page, el_id):
    return page.evaluate(f"!document.getElementById('{el_id}').classList.contains('hidden')")


def test_m025_discard_then_book_open_automatically(page):
    tp, _ = start_as(page, "all")
    page.evaluate(f"S.players[{tp}].discard.push('M-024'); render()")
    page.evaluate(PUSH, ["pick_own_discard", [{"zone": "discard", "player": "me", "index": 0, "value": 0},
                                              {"value": None, "label": "skip"}]])
    page.wait_for_function("!document.getElementById('dialog-overlay').classList.contains('hidden')")
    assert page.locator("#dialog-overlay .pickable").count() == 1              # 棄牌區自動開啟,目標可選
    page.evaluate("document.getElementById('dialog-overlay').classList.add('hidden'); render()")
    page.wait_for_timeout(200)
    assert not is_open(page, "dialog-overlay")                                  # 同一決策關閉後不再自動跳出
    page.evaluate(PUSH, ["pick_empty_page", [{"zone": "book", "player": "me", "page": 20, "value": 20}]])
    page.wait_for_function("!document.getElementById('book-review-overlay').classList.contains('hidden')")
    assert page.locator('#book-review-grid .review-cell.pickable[data-page="20"]').count() == 1


def test_field_targets_do_not_auto_open(page):
    tp, _ = start_as(page, "all")
    uid = page.evaluate(f"S.players[{tp}].slots[0].uid")
    page.evaluate(PUSH, ["protect", [{"value": None, "label": "no_protect"},
                                     {"zone": "slot", "player": "me", "slot": uid, "value": uid}]])
    page.wait_for_timeout(400)
    assert not is_open(page, "dialog-overlay") and not is_open(page, "book-review-overlay")
