"""盤面第 4 欄(MP 托盤、獨立卡區)與棄牌區格(battle-ui「牌桌佈局」「盤面框格與魔書對頁」「獨立卡區」「盤面的棄牌區格」)。
需要 playwright 與 Chromium。

Run: python -m pytest tests/test_board_side_zones_ui.py -q
"""
import pytest

from tests.test_timing_ui import start_as

DESKTOP = {"width": 1280, "height": 900}
PHONE = {"width": 390, "height": 1500}       # 拉高視窗,讓雙方場區都不被行動區蓋住
MJ = ["MJ-001", "MJ-002", "MJ-003", "MJ-004", "MJ-005", "MJ-006", "MJ-001"]


def open_game(browser, server, viewport):  # noqa: F811
    context = browser.new_context(viewport=viewport, reduced_motion="reduce", locale="zh-TW")
    context.add_init_script("localStorage.setItem('gash-spotlight', 'off')")
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(server)
    page.wait_for_function("Object.keys(CARDS).length > 0 && document.querySelector('#cheat-toggle').textContent")
    _, me = start_as(page, "turn")
    return context, page, errors, me


@pytest.fixture
def desk(browser, server):  # noqa: F811
    context, page, errors, me = open_game(browser, server, DESKTOP)
    yield page, me
    context.close()
    assert not errors


@pytest.fixture
def phone(browser, server):  # noqa: F811
    context, page, errors, me = open_game(browser, server, PHONE)
    yield page, me
    context.close()
    assert not errors


def zone(page, p):
    return page.locator(f'.player-zone[data-player="{p}"]')


def box(locator):
    b = locator.bounding_box()
    assert b is not None
    return b


def set_field_cards(page, p, cards):
    page.evaluate("""([p, cards]) => {
        S = {...S, players: S.players.map((ps, i) => i !== p ? ps
            : {...ps, field_cards: cards.map((c, k) => ({uid: 'f' + k, card: c}))})};
        render();
    }""", [p, cards])


def set_discard(page, p, cards):
    page.evaluate("""([p, cards]) => {
        S = {...S, players: S.players.map((ps, i) => i !== p ? ps : {...ps, discard: cards})};
        render();
    }""", [p, cards])


def zoom_num(page):
    page.wait_for_function("!document.getElementById('zoom-overlay').classList.contains('hidden')")
    return page.evaluate("ZOOM.num")


def close_zoom(page):
    page.keyboard.press("Escape")
    page.wait_for_function("document.getElementById('zoom-overlay').classList.contains('hidden')")


# ---------------------------------------------------------------- 第 4 欄與 MP 托盤

def test_side_column_diagonal_and_mp_aligned(desk):
    page, me = desk
    opp = 1 - me
    for p, right in ((me, True), (opp, False)):
        z = zone(page, p)
        mamodo = [box(c) for c in z.locator(".mamodo-row .mamodo-cell").all()]
        tray = box(z.locator(".mp-cell .mp-tray"))
        if right:
            assert tray["x"] >= max(c["x"] + c["width"] for c in mamodo)         # 我方:魔物列右側
        else:
            assert tray["x"] + tray["width"] <= min(c["x"] for c in mamodo)      # 對手:魔物列左側
        assert abs(tray["y"] - mamodo[0]["y"]) <= 1                              # 與魔物格上下對齊
        assert abs(tray["height"] - mamodo[0]["height"]) <= 1
        partners = [box(c) for c in z.locator(".partner-row .partner-cell").all()]
        field = box(z.locator(".field-cards"))
        assert (field["x"] >= max(c["x"] + c["width"] for c in partners)) if right \
            else (field["x"] + field["width"] <= min(c["x"] for c in partners))
        assert z.locator(".book-block .mp-tray").count() == 0                     # 魔書區不再有 MP 托盤


def test_phone_four_equal_columns(phone):
    page, me = phone
    for p in (me, 1 - me):
        row = zone(page, p).locator(".mamodo-row > .mcell, .mp-cell")
        assert row.count() == 4
        widths = [box(c)["width"] for c in row.all()]
        assert max(widths) - min(widths) <= 1
        assert max(box(c)["x"] + box(c)["width"] for c in row.all()) <= PHONE["width"]


# ---------------------------------------------------------------- 獨立卡區

def test_field_cards_empty_frame(desk):
    page, me = desk
    field = zone(page, me).locator(".field-cards")
    assert "empty" in field.get_attribute("class").split()
    assert field.locator(".card").count() == 0


def test_desktop_field_cards_side_by_side_then_overlap(desk):
    page, me = desk
    set_field_cards(page, me, MJ[:2])
    cards = [box(c) for c in zone(page, me).locator(".field-cards .card").all()]
    assert len(cards) == 2 and cards[0]["x"] + cards[0]["width"] <= cards[1]["x"]   # 並排不重疊
    set_field_cards(page, me, MJ[:6])
    field = box(zone(page, me).locator(".field-cards"))
    locs = zone(page, me).locator(".field-cards .card").all()
    boxes = [box(c) for c in locs]
    assert all(b["x"] >= field["x"] - 1 and b["x"] + b["width"] <= field["x"] + field["width"] + 1 for b in boxes)
    assert boxes[-1]["x"] == max(b["x"] for b in boxes)                         # 最新一張在最右邊
    for i, b in enumerate(boxes):                                               # 每張露出的部分都點得到
        x = b["x"] + 3 if i < len(boxes) - 1 else b["x"] + b["width"] / 2
        hit = page.evaluate("([x, y]) => document.elementFromPoint(x, y).closest('.card')?.dataset.fieldUid",
                            [x, b["y"] + b["height"] / 2])
        assert hit == f"f{i}"
    page.mouse.click(boxes[2]["x"] + 3, boxes[2]["y"] + boxes[2]["height"] / 2)
    assert zoom_num(page) == "MJ-003"


@pytest.mark.parametrize("n, grid", [(1, None), (3, "2x2"), (4, "2x2"), (5, "2x3"), (6, "2x3")])
def test_phone_field_cards_icons(phone, n, grid):
    page, me = phone
    set_field_cards(page, me, MJ[:n])
    field = zone(page, me).locator(".field-cards")
    if grid is None:
        assert field.locator(".card").count() == 1 and field.locator(".field-icon").count() == 0
        return
    assert grid in field.get_attribute("data-grid")
    icons = field.locator(".field-icon")
    assert icons.count() == n and field.locator(".field-more").count() == 0
    area = box(field)
    for ic in icons.all():                                                       # 全部在格內可見、方形
        b = box(ic)
        assert abs(b["width"] - b["height"]) <= 1
        assert b["x"] >= area["x"] - 1 and b["y"] >= area["y"] - 1
        assert b["x"] + b["width"] <= area["x"] + area["width"] + 1
        assert b["y"] + b["height"] <= area["y"] + area["height"] + 1
    icons.nth(n - 1).click()
    assert zoom_num(page) == MJ[n - 1]


def test_phone_field_cards_more(phone):
    page, me = phone
    set_field_cards(page, me, MJ[:7])
    field = zone(page, me).locator(".field-cards")
    assert field.locator(".field-icon:not(.field-more)").count() == 5
    more = field.locator(".field-more")
    assert more.inner_text().strip() == "+2"
    more.click()
    page.wait_for_function("!document.getElementById('dialog-overlay').classList.contains('hidden')")
    assert page.locator("#dialog-overlay .card").count() == 7


# ---------------------------------------------------------------- 棄牌區格

def test_discard_pile_empty_and_last_card(desk):
    page, me = desk
    pile = zone(page, me).locator(".discard-pile")
    assert "empty" in pile.get_attribute("class").split()
    assert pile.locator(".discard-label").inner_text().strip() == "棄牌區"
    set_discard(page, me, ["S-001", "M-001"])
    assert "empty" not in pile.get_attribute("class").split()
    assert pile.locator(".card").get_attribute("data-card") == "M-001"         # 最後進入的卡
    assert pile.locator(".discard-count").inner_text().strip() == "×2"
    assert pile.locator(".discard-label").inner_text().strip() == "棄牌區"       # 有卡時標籤也常駐
    opacity = pile.locator(".card").evaluate("(el) => parseFloat(getComputedStyle(el).opacity)")
    filt = pile.locator(".card").evaluate("(el) => getComputedStyle(el).filter")
    assert opacity < 1 or "brightness" in filt                                  # 調暗
    pile.click()
    page.wait_for_function("!document.getElementById('dialog-overlay').classList.contains('hidden')")
    assert page.locator("#dialog-overlay .card").count() == 2


def test_header_has_no_discard_entry(desk):
    page, me = desk
    assert page.locator(".discard-btn").count() == 0


def test_desktop_discard_pile_between_book_and_centerline(desk):
    page, me = desk
    for p, above in ((me, True), (1 - me, False)):
        z = zone(page, p)
        pile, book = box(z.locator(".discard-pile")), box(z.locator(".book-cover"))
        if above:
            assert pile["y"] + pile["height"] <= book["y"] + 1                  # 我方:魔書上方(朝中線)
        else:
            assert pile["y"] >= book["y"] + book["height"] - 1                  # 對手:魔書下方(朝中線)
        assert pile["x"] < book["x"] + book["width"] and book["x"] < pile["x"] + pile["width"]


def test_phone_discard_pile_beside_book(phone):
    page, me = phone
    for p in (me, 1 - me):
        z = zone(page, p)
        pile, book = box(z.locator(".discard-pile")), box(z.locator(".book-cover"))
        assert pile["x"] >= book["x"] + book["width"] - 1                       # 魔書同列、在魔書旁
        assert pile["y"] < book["y"] + book["height"] and book["y"] < pile["y"] + pile["height"]
        assert pile["x"] + pile["width"] <= PHONE["width"]


def test_discard_pile_glows_for_discard_target(desk):
    page, me = desk
    set_discard(page, me, ["M-024"])
    pile = zone(page, me).locator(".discard-pile")
    assert "pickable" not in pile.get_attribute("class").split()
    page.evaluate("""(me) => applyPayload({state: {...S, pending: {kind: 'pick_card_in_own_discard', player: me,
        source: 'M-025', options: [{zone: 'discard', player: me, index: 0, value: 0}, {value: null, label: 'skip'}]}},
        actor: me, events: [{type: 'choice_required', kind: 'pick_card_in_own_discard', player: me, seq: animSeq}]})""", me)
    page.wait_for_function(f"document.querySelector('.player-zone[data-player=\"{me}\"] .discard-pile.pickable')")


# ---------------------------------------------------------------- 雙方魔物欄對齊

def mamodo_centers(page, p):
    return [b["x"] + b["width"] / 2 for b in (box(c) for c in zone(page, p).locator(".mamodo-row .mamodo-cell").all())]


def assert_columns_aligned(page, me):
    mine, theirs = mamodo_centers(page, me), mamodo_centers(page, 1 - me)
    assert len(mine) == len(theirs) == 3
    assert all(abs(a - b) <= 1 for a, b in zip(mine, theirs)), (mine, theirs)


def test_desktop_mamodo_columns_face_each_other(desk):
    page, me = desk
    assert_columns_aligned(page, me)


@pytest.mark.parametrize("width", [760, 1024, 1199])
def test_mid_width_book_row_and_aligned_columns(browser, server, width):  # noqa: F811
    context, page, errors, me = open_game(browser, server, {"width": width, "height": 1400})
    assert_columns_aligned(page, me)
    for p, below in ((me, True), (1 - me, False)):
        z = zone(page, p)
        book, field = box(z.locator(".book-cover")), box(z.locator(".field-block"))
        if below:
            assert book["y"] >= field["y"] + field["height"] - 1               # 我方魔書列在場區下方
        else:
            assert book["y"] + book["height"] <= field["y"] + 1                # 對手魔書列在場區上方
        mamodo = [box(c) for c in z.locator(".mamodo-row .mamodo-cell").all()]
        tray = box(z.locator(".mp-tray"))
        right = p == me                                                        # 寬螢幕維持對角
        assert (tray["x"] >= mamodo[-1]["x"] + mamodo[-1]["width"]) if right \
            else (tray["x"] + tray["width"] <= mamodo[0]["x"])
    assert page.evaluate("document.querySelector('.player-zone .zone-body').scrollWidth"
                         " <= document.querySelector('.player-zone .zone-body').clientWidth + 1")
    context.close()
    assert not errors


def test_phone_side_column_right_for_both_and_aligned(phone):
    page, me = phone
    assert_columns_aligned(page, me)
    for p in (me, 1 - me):
        mamodo = [box(c) for c in zone(page, p).locator(".mamodo-row .mamodo-cell").all()]
        tray = box(zone(page, p).locator(".mp-tray"))
        assert tray["x"] >= mamodo[-1]["x"] + mamodo[-1]["width"]              # 手機雙方都在右側


# ---------------------------------------------------------------- 標題列與查閱魔書入口(header-cleanup)

def test_names_in_center_row(desk):
    page, me = desk
    assert page.locator(".pz-head").count() == 0                               # 玩家區沒有標題列
    track = box(page.locator("#timing-track"))
    mine, theirs = page.locator(f'.stage-name[data-player="{me}"]'), page.locator(f'.stage-name[data-player="{1 - me}"]')
    assert page.evaluate(f"pname({me})") in mine.inner_text() and "(你)" in mine.inner_text()
    assert page.evaluate(f"pname({1 - me})") in theirs.inner_text()
    m, o = box(mine), box(theirs)
    assert m["x"] + m["width"] <= track["x"] and o["x"] >= track["x"] + track["width"]   # 我方在左、對手在右
    for b in (m, o):                                                           # 與時機指示同一列
        assert b["y"] < track["y"] + track["height"] and track["y"] < b["y"] + b["height"]
    assert "active" in mine.get_attribute("class").split()                    # 行動方的名稱也標示
    assert "active" not in theirs.get_attribute("class").split()


def test_names_are_text_not_markup(desk):
    page, me = desk
    page.evaluate("R = {...(R || {}), names: ['<b>x</b>', '<i>y</i>']}; render()")
    assert page.locator(".stage-name").count() == 2
    assert page.locator(".stage-name b, .stage-name i").count() == 0
    assert "<b>x</b>" in page.locator(".stage-name").all_inner_texts()[0] + page.locator(".stage-name").all_inner_texts()[1]


def test_phone_names_one_row_above_track(phone):
    page, me = phone
    track = box(page.locator("#timing-track"))
    m, o = (box(page.locator(f'.stage-name[data-player="{p}"]')) for p in (me, 1 - me))
    assert abs(m["y"] - o["y"]) <= 2 and m["x"] < o["x"]                      # 同一列,我方在左
    assert m["y"] + m["height"] <= track["y"] + 1
    assert o["x"] + o["width"] <= PHONE["width"]


def test_review_book_button_on_cover(desk):
    page, me = desk
    cover = zone(page, me).locator(".book-cover")
    btn = cover.locator(".book-review")
    assert btn.inner_text().strip() == "查閱魔書"
    b, c = box(btn), box(cover)
    assert b["y"] + b["height"] / 2 >= c["y"] + c["height"] - 2               # 在書皮下緣
    btn.click()
    page.wait_for_function("!document.getElementById('book-review-overlay').classList.contains('hidden')")
    assert page.evaluate("BOOK_VIEW") == me


def test_opponent_book_has_no_review_button(desk):
    page, me = desk
    page.evaluate("SESSION = {...SESSION, viewer: %d}; render()" % me)
    page.evaluate("""(opp) => { S = {...S, players: S.players.map((ps, i) => i === opp ? {...ps, book: null} : ps)};
        render(); }""", 1 - me)
    assert zone(page, 1 - me).locator(".book-review").count() == 0
    assert zone(page, me).locator(".book-review").count() == 1


def test_phone_review_button_clear_of_discard_pile(phone):
    page, me = phone
    for p in (me, 1 - me):
        b, d = box(zone(page, p).locator(".book-review")), box(zone(page, p).locator(".discard-pile"))
        assert b["x"] + b["width"] <= d["x"] or d["x"] + d["width"] <= b["x"] \
            or b["y"] + b["height"] <= d["y"] or d["y"] + d["height"] <= b["y"]


def test_topbar_has_no_game_status(desk):
    page, me = desk
    for el in ("identity", "turn-info", "phase-info", "acting-info"):
        assert page.locator(f"#{el}").count() == 0
    assert "回合" not in page.locator("#topbar").inner_text()


def test_turn_number_in_center_row(desk):
    page, me = desk
    page.evaluate("S = {...S, turn_no: 7}; render()")
    turn, track = page.locator("#stage-turn"), box(page.locator("#timing-track"))
    assert turn.inner_text().strip() == "第 7 回合"
    b = box(turn)
    assert b["y"] < track["y"] + track["height"] and track["y"] < b["y"] + b["height"]
    assert b["x"] + b["width"] <= track["x"] + 1                                # 接在時機指示之前


def test_spectator_label_in_center_row(desk):
    page, me = desk
    page.evaluate("SESSION = {...SESSION, viewer: 'spectator'}; render()")
    assert "觀戰中" in page.locator("#stage-turn").inner_text()
    assert all("(你)" not in t for t in page.locator(".stage-name").all_inner_texts())


def test_opponent_deciding_note_in_action_bar(desk):
    page, me = desk
    page.evaluate("""(me) => { S = {...S, pending: {kind: 'protect', player: 1 - me, source: null, info: {}, options: []}};
        SESSION = {...SESSION, viewer: me}; render(); }""", me)
    assert "對手決策中" in page.locator("#action-bar .waiting-note").inner_text()


def test_phone_turn_number_on_name_row(phone):
    page, me = phone
    turn = box(page.locator("#stage-turn"))
    m, o = (box(page.locator(f'.stage-name[data-player="{p}"]')) for p in (me, 1 - me))
    assert m["x"] + m["width"] <= turn["x"] + 1 and turn["x"] + turn["width"] <= o["x"] + 1   # 名稱之間
    assert abs((turn["y"] + turn["height"] / 2) - (m["y"] + m["height"] / 2)) <= 3
