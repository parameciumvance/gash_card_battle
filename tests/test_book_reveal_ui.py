"""檢視對手魔書(M-011 / E-016 / E-017)的網格顯示整本(battle-ui「檢視對手魔書」)。
以合成的事件批次測前端:快照中對手沒有 book(線上視角),book_revealed 帶整本內容(只送給檢視者)。

Run: python -m pytest tests/test_book_reveal_ui.py -q
"""
from tests.test_timing_ui import start_as

SETUP = """(pending) => {
    const me = S.turn_player, opp = 1 - me;
    SESSION = {...SESSION, viewer: me};
    const players = S.players.map((ps, i) => {
        if (i !== opp) return ps;
        const {book, ...rest} = ps;                                  // 線上視角:看不到對手的 book
        return rest;
    });
    const cards = [];
    for (let pg = 2; pg <= 32; pg++) cards.push({page: pg, card: pg === 5 ? 'M-004' : 'S-029'});
    const state = {...S, players, pending: pending ? {kind: 'pick_opponent_book_card', player: me, source: 'M-011',
        options: [{value: 5, zone: 'book', player: opp, page: 5, card: 'M-004'}]}
      : {kind: 'end_book_review', player: me, source: 'M-011',
         options: [{value: null, label: 'end_review', player: opp, cards}]}};
    applyPayload({state, actor: me,
        events: [{type: 'book_revealed', player: opp, viewer: me, cards, seq: animSeq}]});
    return opp;
}"""


def grid(page):
    return page.evaluate("""() => ({
        open: !document.getElementById('book-review-overlay').classList.contains('hidden'),
        title: document.getElementById('book-review-title').textContent,
        faces: [...document.querySelectorAll('#book-review-grid .review-cell [data-card]')].length,
        pickable: [...document.querySelectorAll('#book-review-grid .review-cell.pickable')].map(c => Number(c.dataset.page)),
    })""")


def test_no_target_opens_whole_book_and_end_button(page):
    start_as(page, "all")
    opp = page.evaluate(SETUP, False)
    page.wait_for_function("!document.getElementById('book-review-overlay').classList.contains('hidden')")
    g = grid(page)
    assert g["faces"] == 31 and g["pickable"] == []                              # 整本卡面,沒有可選的頁
    assert "沒有可選的卡" in g["title"] and page.evaluate(f"pname({opp})") in g["title"]
    page.locator("#book-review-close").click()                                   # 關掉網格仍可從提示再開
    buttons = page.locator("#action-bar .choice-options button").all_inner_texts()
    assert "結束檢視" in buttons and any("魔書" in b for b in buttons)
    page.locator("#action-bar .choice-options button", has_text="魔書").click()
    assert grid(page)["open"] and grid(page)["faces"] == 31
    page.evaluate("S = {...S, pending: null}; render()")                          # 結束檢視後網格關閉
    assert not grid(page)["open"]


def test_with_target_grid_shows_whole_book_and_candidates_glow(page):
    start_as(page, "all")
    opp = page.evaluate(SETUP, True)
    page.wait_for_function("!document.getElementById('book-review-overlay').classList.contains('hidden')")
    g = grid(page)                                                               # 目標都在對手魔書:自動開啟
    assert g["faces"] == 31 and g["pickable"] == [5]                             # 非候選頁也顯示卡面
    assert "沒有可選的卡" not in g["title"]
