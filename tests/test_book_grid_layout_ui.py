"""魔本網格排版的瀏覽器測試(battle-ui「查閱己方魔本」、deck-builder「對頁編輯」、金手指共用網格)。
需要 playwright 與 Chromium。

Run: python -m pytest tests/test_book_grid_layout_ui.py -q
"""
import pytest

from tests.test_cheat_editor import browser, server  # noqa: F401  共用 fixture(隔離的伺服器與瀏覽器)

DESKTOP = {"width": 1280, "height": 900}
PHONE = {"width": 390, "height": 844}


def open_page(browser, server, viewport, path="/"):  # noqa: F811
    context = browser.new_context(viewport=viewport, reduced_motion="reduce", locale="zh-TW")
    context.add_init_script("localStorage.setItem('gash-spotlight', 'off')")
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(server + path)
    page.wait_for_function("Object.keys(CARDS).length > 0")
    return context, page, errors


def spreads(page, grid, cls):
    return page.evaluate(f"""[...document.querySelectorAll('#{grid} > .{cls}')].map((el) => {{
        const r = el.getBoundingClientRect();
        return {{left: Math.round(r.left), right: Math.round(r.right), top: Math.round(r.top),
                 single: el.classList.contains('single')}};
    }})""")


def assert_aligned(items):
    """17 個欄位(P1、15 組對頁、P32)排成固定欄:各列對頁的左緣一致,P1 靠第一欄右側,P32 在最後一列第一欄左側。"""
    assert len(items) == 17
    first, *doubles, last = items
    assert first["single"] and last["single"] and not any(d["single"] for d in doubles)
    rows = sorted({d["top"] for d in items})
    cols = len([d for d in items if d["top"] == rows[0]])
    assert cols >= 1
    width = doubles[0]["right"] - doubles[0]["left"]
    lefts = {}
    for i, d in enumerate(items):
        col = i % cols
        assert d["top"] == rows[i // cols]                                # 依序填滿每列
        if not d["single"]:
            assert d["right"] - d["left"] == width
            lefts.setdefault(col, d["left"])
            assert d["left"] == lefts[col]                                # 同欄上下對齊
    col0_left = lefts[0]
    assert first["right"] == col0_left + width                            # P1 靠第一欄右側
    assert last["left"] == lefts[16 % cols]                               # P32 靠所在欄左側
    return cols


@pytest.mark.parametrize("viewport", [DESKTOP, PHONE], ids=["desktop", "phone"])
def test_builder_grid_is_aligned(browser, server, viewport):  # noqa: F811
    context, page, errors = open_page(browser, server, viewport, "/?builder")
    page.wait_for_selector("#book-grid .spread")
    cols = assert_aligned(spreads(page, "book-grid", "spread"))
    if viewport is DESKTOP:
        assert cols >= 3
    context.close()
    assert not errors


def test_cheat_grid_is_aligned(browser, server):  # noqa: F811
    context, page, errors = open_page(browser, server, DESKTOP)
    page.evaluate("startLocal()")
    page.wait_for_function("S && S.phase === 'start'")
    page.locator("#cheat-toggle").click()
    page.wait_for_selector("#cheat-book-grid .spread")
    assert_aligned(spreads(page, "cheat-book-grid", "spread"))
    heights = page.evaluate("""[...document.querySelectorAll('#cheat-book-grid .spread')].map((sp) =>
        [...sp.querySelectorAll('.page-slot .card')].map((c) => Math.round(c.getBoundingClientRect().height)))""")
    for pair in heights:
        assert len(set(pair)) <= 1, pair                                  # 同一對頁的兩張卡等高
    context.close()
    assert not errors


@pytest.mark.parametrize("viewport", [DESKTOP, PHONE], ids=["desktop", "phone"])
def test_book_review_rows_are_aligned_and_cards_equal_height(browser, server, viewport):  # noqa: F811
    context, page, errors = open_page(browser, server, viewport)
    page.evaluate("startLocal()")
    page.wait_for_function("S && S.phase === 'start'")
    page.evaluate("""async () => {                                        // 放出 P1 的魔物:P1 變成已上場的卡背
        await send({type: 'flip_pages', player: S.turn_player, count: 0});
        await send({type: 'play_card', player: S.turn_player, page: 1});
    }""")
    page.wait_for_function("S.players[S.turn_player].consumed_pages.includes(1)")
    page.evaluate("showBookReview(S.turn_player)")
    page.evaluate("document.getElementById('book-review').scrollTop = 0")
    assert_aligned(spreads(page, "book-review-grid", "review-spread"))
    heights = page.evaluate("""() => {
        const rows = {};
        for (const el of document.querySelectorAll('#book-review-grid .review-cell .card')) {
            const r = el.getBoundingClientRect();
            const top = Math.round(el.closest('.review-spread').getBoundingClientRect().top);
            (rows[top] = rows[top] || []).push(Math.round(r.height));
        }
        return Object.values(rows);
    }""")
    assert heights
    for row in heights:
        assert max(row) - min(row) <= 1, row                              # 同一列的卡片等高
    widths = page.evaluate("""[...document.querySelectorAll('#book-review-grid .review-spread')].map((sp) => {
        const box = sp.getBoundingClientRect();
        return [...sp.querySelectorAll('.card')].every((c) => {
            const r = c.getBoundingClientRect();
            return r.left >= box.left && r.right <= box.right;
        });
    })""")
    assert all(widths)                                                    # 卡片(含已上場的卡背)不超出對頁框
    context.close()
    assert not errors
