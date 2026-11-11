"""開始階段的翻頁提醒(battle-ui「開始階段的翻頁提醒」)。需要 playwright 與 Chromium。

Run: python -m pytest tests/test_flip_hint_ui.py -q
"""
from tests.test_book_browse_ui import nav, start_local
from tests.test_turn_dial_ui import note_of

GLOW = "flip-glow"


def glowing(page, p, which="next"):
    return GLOW in (nav(page, p, which).get_attribute("class") or "")


def test_note_and_glow_at_start(page):
    tp = start_local(page)
    max_flip = page.evaluate(f"Math.min(3, Math.floor((32 - S.players[{tp}].pos) / 2))")
    assert max_flip == 3
    assert note_of(page, "不翻頁") == "按魔書的 › 往後翻閱,選擇翻幾張(最多 3 張)"
    assert glowing(page, tp)
    assert not glowing(page, tp, "prev")                                  # 往前沒有合法位置


def test_glow_stops_at_max(page):
    tp = start_local(page)
    for _ in range(2):
        nav(page, tp, "next").click()
        assert glowing(page, tp)                                          # 還能再往後
    nav(page, tp, "next").click()                                         # 翻 3 張:上限
    assert not glowing(page, tp)
    assert glowing(page, tp, "prev")                                      # 往前還有合法位置
    assert page.locator("#action-bar button", has_text="翻 3 張").count() == 1


def test_both_glow_in_middle(page):
    # 依方向:往該方向還有合法的翻閱位置就發光(ui-hint-polish)
    tp = start_local(page)
    nav(page, tp, "next").click()                                         # 翻 1 張
    assert glowing(page, tp) and glowing(page, tp, "prev")


def test_prev_glows_beyond_max(page):
    tp = start_local(page)
    for _ in range(4):                                                    # 超過最多 3 張
        nav(page, tp, "next").click()
    assert glowing(page, tp, "prev") and not glowing(page, tp)
    assert page.locator("#action-bar .flip-hint").count() == 1


def test_next_glows_before_current(page):
    tp = start_local(page)
    nav(page, tp, "prev").click()                                         # 目前頁之前
    assert glowing(page, tp) and not glowing(page, tp, "prev")


def test_no_hint_on_last_spread(page):
    tp = start_local(page)
    page.evaluate(f"""() => {{
        S = {{...S, players: S.players.map((x, i) => i === {tp} ? {{...x, pos: 32}} : x)}};
        render();
    }}""")
    btn = page.locator("#action-bar button", has_text="不翻頁")
    assert btn.locator(".btn-note").count() == 0
    assert not glowing(page, tp) and not glowing(page, tp, "prev")


def test_no_glow_in_battle_or_on_opponent_book(page):
    tp = start_local(page)
    if nav(page, 1 - tp, "next").count():                                # 對手(非回合玩家)的魔書不發光
        assert not glowing(page, 1 - tp)
    page.locator("#action-bar button", has_text="不翻頁").click()
    page.wait_for_function("S.phase === 'battle'")
    assert not glowing(page, tp)


# ---------------------------------------------------------------- 魔書網格的目前頁顏色

def test_review_current_page_differs_from_pickable(page):
    tp = start_local(page)
    page.evaluate(f"showBookReview({tp})")
    cell = page.locator("#book-review-grid .review-cell.open").first
    outline = cell.evaluate("(el) => getComputedStyle(el).outlineColor")
    tag = page.locator("#book-review-grid .review-tag.cur").first.evaluate(
        "(el) => getComputedStyle(el).backgroundColor")
    blue = "rgb(108, 196, 255)"                                           # --accent-blue
    assert outline == blue and tag == blue
    glow = page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--glow').trim()")
    assert glow == "#ffd166"                                              # 可選的卡維持金色


# ---------------------------------------------------------------- 手機:提示開關緊鄰提示清單

def test_phone_hint_toggle_next_to_details(page):
    page.set_viewport_size({"width": 390, "height": 844})
    start_local(page)
    toggle = page.locator("#action-bar .hint-toggle")
    if "收起" not in toggle.inner_text():
        toggle.click()
    details = page.locator("#action-bar .hint-details")
    flip = page.locator("#action-bar button", has_text="不翻頁")
    tb, db, fb = toggle.bounding_box(), details.bounding_box(), flip.bounding_box()
    assert fb["y"] < tb["y"] < db["y"]                                    # 翻頁按鈕在前,開關緊接著清單
    assert db["y"] - (tb["y"] + tb["height"]) < 16
