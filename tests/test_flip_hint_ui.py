"""開始階段的翻頁提醒(battle-ui「開始階段的翻頁提醒」)。需要 playwright 與 Chromium。

Run: python -m pytest tests/test_flip_hint_ui.py -q
"""
from tests.test_book_browse_ui import nav, start_local
from tests.test_turn_dial_ui import note_of

GLOW = "flip-glow"


def glowing(page, p):
    return GLOW in (nav(page, p, "next").get_attribute("class") or "")


def test_note_and_glow_at_start(page):
    tp = start_local(page)
    max_flip = page.evaluate(f"Math.min(3, Math.floor((32 - S.players[{tp}].pos) / 2))")
    assert max_flip == 3
    assert note_of(page, "不翻頁") == "按魔書的 › 往後翻閱,選擇翻幾張(最多 3 張)"
    assert glowing(page, tp)


def test_glow_stops_at_max(page):
    tp = start_local(page)
    for _ in range(2):
        nav(page, tp, "next").click()
        assert glowing(page, tp)                                          # 還能再往後
    nav(page, tp, "next").click()                                         # 翻 3 張:上限
    assert not glowing(page, tp)
    assert page.locator("#action-bar button", has_text="翻 3 張").count() == 1


def test_no_hint_on_last_spread(page):
    tp = start_local(page)
    page.evaluate(f"""() => {{
        S = {{...S, players: S.players.map((x, i) => i === {tp} ? {{...x, pos: 32}} : x)}};
        render();
    }}""")
    btn = page.locator("#action-bar button", has_text="不翻頁")
    assert btn.locator(".btn-note").count() == 0
    assert not glowing(page, tp)


def test_no_glow_in_battle_or_on_opponent_book(page):
    tp = start_local(page)
    if nav(page, 1 - tp, "next").count():                                # 對手(非回合玩家)的魔書不發光
        assert not glowing(page, 1 - tp)
    page.locator("#action-bar button", has_text="不翻頁").click()
    page.wait_for_function("S.phase === 'battle'")
    assert not glowing(page, tp)
