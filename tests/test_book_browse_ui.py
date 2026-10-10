"""場上魔書翻閱的瀏覽器測試(battle-ui「場上魔書翻閱」「魔書翻閱的鍵盤操作」)。
需要 playwright 與 Chromium。以本機測試模式操作。

Run: python -m pytest tests/test_book_browse_ui.py -q
"""
from tests.test_cheat_editor import browser, page, server  # noqa: F401  共用 fixture(隔離的伺服器與瀏覽器)


def start_local(page):
    page.evaluate("startLocal()")
    page.wait_for_function("S && S.phase === 'start'")
    return page.evaluate("S.turn_player")


def block(page, p):
    return page.locator(f'.book-block[data-book-block="{p}"]')


def shown(page, p):
    """魔書區目前顯示的頁:[(頁碼, 卡號或 'back' / 'consumed')]。"""
    return [tuple(x) for x in page.evaluate("""(p) => [...document.querySelectorAll(`.book-block[data-book-block="${p}"] .book-pages [data-page]`)]
      .map((el) => [Number(el.dataset.page),
                    el.classList.contains('back') ? (el.classList.contains('consumed') ? 'consumed' : 'back') : el.dataset.card])""", p)]


def nav(page, p, which):
    return block(page, p).locator(f".book-{which}")


def book(page, p):
    return page.evaluate(f"S.players[{p}].book")


def test_browse_forward_and_return(page):
    tp = start_local(page)
    pos = page.evaluate(f"S.players[{tp}].pos")
    assert [pg for pg, _ in shown(page, tp)] == [pos, pos + 1]
    assert nav(page, tp, "current").is_disabled()
    nav(page, tp, "next").click()
    nav(page, tp, "next").click()
    cards = book(page, tp)
    assert shown(page, tp) == [(pos + 4, cards[pos + 3]), (pos + 5, cards[pos + 4])]
    assert nav(page, tp, "current").is_enabled()
    nav(page, tp, "current").click()
    assert [pg for pg, _ in shown(page, tp)] == [pos, pos + 1]
    assert nav(page, tp, "current").is_disabled()


def test_first_and_last_spreads_are_single(page):
    tp = start_local(page)
    while nav(page, tp, "prev").is_enabled():
        nav(page, tp, "prev").click()
    assert shown(page, tp) == [(1, "consumed")]                  # 第 1 頁的魔物已上場:卡背
    while nav(page, tp, "next").is_enabled():
        nav(page, tp, "next").click()
    assert shown(page, tp) == [(32, book(page, tp)[31])]


def test_browsed_card_zoom_has_no_actions(page):
    tp = start_local(page)
    nav(page, tp, "next").click()
    block(page, tp).locator(".book-pages .card[data-card]").first.click()
    page.wait_for_function("!document.getElementById('zoom-overlay').classList.contains('hidden')")
    assert page.locator("#zoom-actions button").count() == 0


def test_own_flip_returns_to_current_other_updates_keep(page):
    tp = start_local(page)
    pos = page.evaluate(f"S.players[{tp}].pos")
    nav(page, tp, "next").click()
    nav(page, tp, "next").click()
    page.evaluate(f"send({{type: 'flip_pages', player: {tp}, count: 1}})")      # 自己的魔書被翻動
    page.wait_for_function(f"S.players[{tp}].pos === {pos + 2}")
    page.wait_for_function(f"""document.querySelector('.book-block[data-book-block="{tp}"] .book-current').disabled""")
    assert [pg for pg, _ in shown(page, tp)] == [pos + 2, pos + 3]
    nav(page, tp, "next").click()
    page.evaluate(f"send({{type: 'pass', player: {tp}}})")                       # 其他更新:行動權改變
    page.wait_for_function(f"S.action_player === {1 - tp}")
    assert [pg for pg, _ in shown(page, tp)] == [pos + 4, pos + 5]


def test_no_browse_without_full_book(page):
    tp = start_local(page)
    op = 1 - tp
    page.evaluate(f"""S = {{...S, players: S.players.map((ps, i) => i === {op} ? {{...ps, book: undefined}} : ps)}}; render()""")
    assert nav(page, op, "next").count() == 0 and nav(page, op, "current").count() == 0
    assert nav(page, tp, "next").count() == 1


def test_keyboard_browses_awaited_players_book(page):
    tp = start_local(page)
    op = 1 - tp
    pos = page.evaluate(f"S.players[{tp}].pos")
    other = shown(page, op)
    page.keyboard.press("ArrowRight")
    assert [pg for pg, _ in shown(page, tp)] == [pos + 2, pos + 3]
    assert shown(page, op) == other                                              # 只翻行動中一方的魔書
    page.keyboard.press("Home")
    assert [pg for pg, _ in shown(page, tp)] == [pos, pos + 1]
    page.keyboard.press("ArrowRight")
    page.keyboard.press("Escape")
    assert [pg for pg, _ in shown(page, tp)] == [pos, pos + 1]
    page.evaluate("zoom('S-001')")                                               # 視窗開著:不翻閱
    page.keyboard.press("ArrowRight")
    assert [pg for pg, _ in shown(page, tp)] == [pos, pos + 1]


def test_book_pick_target_selectable_while_browsing(page):
    # 從魔書挑頁的決策(例如 S-048 選 M-027):翻閱到目標頁時,該頁發光,點開可按「選擇」
    tp = start_local(page)
    pos = page.evaluate(f"S.players[{tp}].pos")
    target = pos + 6
    page.evaluate(f"""() => {{
      S = {{...S, pending: {{kind: 'pick_mamodo_in_own_book', player: {tp}, source: 'S-048',
        options: [{{value: {target}, zone: 'book', player: {tp}, page: {target}, card: S.players[{tp}].book[{target - 1}]}}]}}}};
      render();
    }}""")
    page.evaluate("() => { window.__sent = []; send = (c) => { window.__sent.push(c); return Promise.resolve(); }; }")
    while not page.locator(f'.book-block[data-book-block="{tp}"] .book-pages [data-page="{target}"]').count():
        nav(page, tp, "next").click()
    card = page.locator(f'.book-block[data-book-block="{tp}"] .book-pages [data-page="{target}"]')
    assert "pickable" in card.get_attribute("class")
    card.click()
    page.locator("#zoom-actions button", has_text="選擇").click()
    assert page.evaluate("window.__sent") == [{"type": "choose", "player": tp, "value": target}]


# ---------------------------------------------------------------- 開始階段依翻閱選擇翻頁張數

def flip_buttons(page):
    return [t for t in page.locator("#action-bar button").all_text_contents() if t.startswith(("翻", "不翻頁"))]


def test_start_phase_flip_follows_browse(page):
    tp = start_local(page)
    pos = page.evaluate(f"S.players[{tp}].pos")
    assert flip_buttons(page) == ["不翻頁"]
    for n, mp in ((1, 2), (2, 4), (3, 6)):
        nav(page, tp, "next").click()
        assert flip_buttons(page) == [f"翻 {n} 張(MP +{mp})"]
    nav(page, tp, "prev").click()
    page.locator("#action-bar button", has_text="翻 2 張").click()
    page.wait_for_function(f"S.players[{tp}].pos === {pos + 4} && S.phase === 'battle'")
    assert [pg for pg, _ in shown(page, tp)] == [pos + 4, pos + 5]          # 回到新的目前頁
    assert nav(page, tp, "current").is_disabled()


def test_start_phase_out_of_range_shows_hint(page):
    tp = start_local(page)
    nav(page, tp, "prev").click()                                            # 往前
    assert flip_buttons(page) == []
    assert "最多翻 3 張" in page.locator("#action-bar").inner_text()
    nav(page, tp, "current").click()
    for _ in range(4):                                                       # 往後 4 個對頁
        nav(page, tp, "next").click()
    assert flip_buttons(page) == []
    assert "用左右鍵選擇要翻到的頁" in page.locator("#action-bar").inner_text()


def test_start_phase_limited_by_remaining_pages(page):
    tp = start_local(page)
    page.evaluate(f"S = {{...S, players: S.players.map((ps, i) => i === {tp} ? {{...ps, pos: 30}} : ps)}}; render()")
    nav(page, tp, "next").click()
    assert flip_buttons(page) == ["翻 1 張(MP +2)"]
    assert nav(page, tp, "next").is_disabled()                               # 翻閱與張數同樣以第 32 頁為界
