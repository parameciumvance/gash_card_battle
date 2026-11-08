"""決策開始時自動開啟棄牌區 / 魔書(battle-ui「選擇畫面自動開啟」):目標都在同一處、場上沒有目標時自動開啟,
每個決策只自動開啟一次。以合成的決策批次模擬 M-025(先從棄牌區選魔物,再選魔書的空頁)。

Run: python -m pytest tests/test_auto_open_pick_ui.py -q
"""
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
    page.evaluate(PUSH, ["pick_card_in_own_discard", [{"zone": "discard", "player": "me", "index": 0, "value": 0},
                                              {"value": None, "label": "skip"}]])
    page.wait_for_function("!document.getElementById('dialog-overlay').classList.contains('hidden')")
    assert page.locator("#dialog-overlay .pickable").count() == 1              # 棄牌區自動開啟,目標可選
    page.evaluate("document.getElementById('dialog-overlay').classList.add('hidden'); render()")
    page.wait_for_timeout(200)
    assert not is_open(page, "dialog-overlay")                                  # 同一決策關閉後不再自動跳出
    page.evaluate(PUSH, ["pick_own_empty_page", [{"zone": "book", "player": "me", "page": 20, "value": 20}]])
    page.wait_for_function("!document.getElementById('book-review-overlay').classList.contains('hidden')")
    assert page.locator('#book-review-grid .review-cell.pickable[data-page="20"]').count() == 1


def test_field_targets_do_not_auto_open(page):
    tp, _ = start_as(page, "all")
    uid = page.evaluate(f"S.players[{tp}].slots[0].uid")
    page.evaluate(PUSH, ["protect", [{"value": None, "label": "no_protect"},
                                     {"zone": "slot", "player": "me", "slot": uid, "value": uid}]])
    page.wait_for_timeout(400)
    assert not is_open(page, "dialog-overlay") and not is_open(page, "book-review-overlay")


# ---------------------------------------------------------------- 選擇提示(battle-ui「選擇畫面的提示文字」)

def test_book_grid_shows_what_to_pick(page):
    tp, _ = start_as(page, "all")
    page.evaluate(PUSH, ["pick_mamodo_in_own_book", [{"zone": "book", "player": "me", "page": 20, "value": 20}]])
    page.wait_for_function("!document.getElementById('book-review-overlay').classList.contains('hidden')")
    hint = page.locator("#book-review-hint")
    assert hint.is_visible()
    assert "選擇自己魔書中的魔物卡" in hint.text_content()
    assert page.evaluate("cname('M-025')") in hint.text_content()            # 來源卡


def test_discard_pick_shows_what_to_pick(page):
    tp, _ = start_as(page, "all")
    page.evaluate(f"S.players[{tp}].discard.push('M-024'); render()")
    page.evaluate(PUSH, ["pick_card_in_own_discard", [{"zone": "discard", "player": "me", "index": 0, "value": 0}]])
    page.wait_for_function("!document.getElementById('dialog-overlay').classList.contains('hidden')")
    notes = page.locator("#dialog-notes").text_content()
    assert page.evaluate("t('choice.title.pick_card_in_own_discard')") in notes
    assert page.evaluate("cname('M-025')") in page.locator("#dialog-source").text_content()


def test_plain_review_has_no_pick_hint(page):
    tp, _ = start_as(page, "all")
    page.evaluate(f"showBookReview({tp})")
    assert not page.locator("#book-review-hint").is_visible()


# ---------------------------------------------------------------- 演出播完才自動開啟;棄牌飛向棄牌區(動畫開啟)

from tests.test_spotlight_ui import open_page  # noqa: E402


def motion_page(browser, server):  # noqa: F811
    context, page, errors = open_page(browser, server, motion="no-preference", prefs={"spotlight": "off"})
    return context, page, errors


def test_auto_open_waits_for_card_flight(browser, server):  # noqa: F811
    context, page, errors = motion_page(browser, server)
    tp, _ = start_as(page, "all")
    page.evaluate("""() => {
        window.__openedAt = null;
        const ov = document.getElementById('book-review-overlay');
        new MutationObserver(() => { if (!ov.classList.contains('hidden') && window.__openedAt === null)
            window.__openedAt = performance.now(); }).observe(ov, {attributes: true});
    }""")
    t0 = page.evaluate("""() => {
        const me = S.turn_player, s = S.players[me].slots[0];
        window.__t0 = performance.now();
        applyPayload({state: {...S, pending: {kind: 'pick_mamodo_in_own_book', player: me, source: 'S-043',
            options: [{zone: 'book', player: me, page: 20, value: 20}]}}, actor: me,
            events: [{type: 'card_played', player: me, card: s.top, slot: s.uid, zone: 'mamodo', seq: animSeq}]});
        return window.__t0;
    }""")
    page.wait_for_function("window.__openedAt !== null", timeout=5000)
    assert page.evaluate("window.__openedAt") - t0 >= 450                     # 第一張的飛卡播完才跳第二次選擇
    context.close()
    assert not errors


def test_discarded_partner_flies_to_discard_pile(browser, server):  # noqa: F811
    context, page, errors = motion_page(browser, server)
    tp, _ = start_as(page, "all")
    res = page.evaluate("""async () => {
        const me = S.turn_player, s = S.players[me].slots[0];
        S = {...S, players: S.players.map((ps, i) => i !== me ? ps
            : {...ps, slots: ps.slots.map((x) => x.uid === s.uid ? {...x, partner: 'P-001'} : x)})};
        render();
        const after = {...S, players: S.players.map((ps, i) => i !== me ? ps
            : {...ps, discard: [...ps.discard, 'P-001'], slots: ps.slots.map((x) => ({...x, partner: null}))})};
        applyPayload({state: after, actor: me, events: [{type: 'card_discarded', player: me, card: 'P-001',
            zone: 'partner', reason: 'TEST', slot: s.uid, seq: animSeq}]});
        await Anim.idle();
        const ghost = document.querySelector('#anim-overlay .fx-to-discard[data-card="P-001"]');
        await new Promise((r) => setTimeout(r, 650));
        const pile = document.querySelector(`.player-zone[data-player="${me}"] .discard-pile`).getBoundingClientRect();
        const g = ghost && ghost.getBoundingClientRect();
        return {ghost: !!ghost, gone: !document.querySelector('#anim-overlay .fx-to-discard'),
                pile: {x: pile.left + pile.width / 2, y: pile.top + pile.height / 2},
                last: g && {x: g.left + g.width / 2, y: g.top + g.height / 2}};
    }""")
    assert res["ghost"] and res["gone"]                                         # 出現後播完移除
    context.close()
    assert not errors


def test_borrowed_partner_flies_to_owner_discard_pile(browser, server):  # noqa: F811
    # M-058 借來的搭檔離場時進持有者(對手)的捨て札:飛向對手的棄牌區
    context, page, errors = motion_page(browser, server)
    tp, _ = start_as(page, "all")
    res = page.evaluate("""async () => {
        const me = S.turn_player, opp = 1 - me, s = S.players[me].slots[0];
        S = {...S, players: S.players.map((ps, i) => i !== me ? ps
            : {...ps, slots: ps.slots.map((x) => x.uid === s.uid ? {...x, partner: 'P-002', partner_owner: opp} : x)})};
        render();
        const after = {...S, players: S.players.map((ps, i) =>
            i === opp ? {...ps, discard: [...ps.discard, 'P-002']}
            : {...ps, slots: ps.slots.map((x) => ({...x, partner: null, partner_owner: null}))})};
        applyPayload({state: after, actor: me, events: [{type: 'card_discarded', player: me, owner: opp,
            card: 'P-002', zone: 'partner', reason: 'cost', slot: s.uid, seq: animSeq}]});
        await Anim.idle();
        const ghost = document.querySelector('#anim-overlay .fx-to-discard[data-card="P-002"]');
        const center = (p) => {
            const r = document.querySelector(`.player-zone[data-player="${p}"] .discard-pile`).getBoundingClientRect();
            return {x: r.left + r.width / 2, y: r.top + r.height / 2};
        };
        const g = ghost && {x: parseFloat(ghost.style.left) + parseFloat(ghost.style.width) / 2,
                            y: parseFloat(ghost.style.top) + parseFloat(ghost.style.height) / 2};
        return {ghost: g, own: center(me), owner: center(opp)};
    }""")
    g = res["ghost"]
    assert g is not None
    dist = lambda c: abs(c["x"] - g["x"]) + abs(c["y"] - g["y"])  # noqa: E731
    assert dist(res["owner"]) < 2 and dist(res["own"]) > 50                    # 目的地是持有者的棄牌區
    context.close()
    assert not errors


FROM_DISCARD = """async (borrowed) => {
    // 搭檔自棄牌區上場(E-011 / E-022;M-058 借用時是對手的棄牌區):飛卡的起點是那一方的棄牌區
    const me = S.turn_player, opp = 1 - me, src = borrowed ? opp : me, s = S.players[me].slots[0];
    S = {...S, players: S.players.map((ps, i) => i !== src ? ps : {...ps, discard: [...ps.discard, 'P-002']})};
    render();
    const after = {...S, players: S.players.map((ps, i) => {
        let x = i === src ? {...ps, discard: ps.discard.slice(0, -1)} : ps;
        if (i === me) x = {...x, slots: x.slots.map((y) => y.uid === s.uid
            ? {...y, partner: 'P-002', partner_owner: borrowed ? opp : null} : y)};
        return x;
    })};
    const ev = {type: 'card_played', player: me, card: 'P-002', slot: s.uid, zone: 'partner',
                from_discard: true, seq: animSeq};
    if (borrowed) ev.owner = opp;
    const center = (r) => ({x: r.left + r.width / 2, y: r.top + r.height / 2});
    const pile = (p) => center(document.querySelector(`.player-zone[data-player="${p}"] .discard-pile`)
        .getBoundingClientRect());
    const piles = {src: pile(src), other: pile(1 - src)};
    let start = null;                             // 飛卡加入時的位置(之後同步改成終點)
    const ov = document.getElementById('anim-overlay'), append = ov.appendChild;
    ov.appendChild = function (g) {
        if (!start && g.classList.contains('fx-fly-card'))
            start = {x: parseFloat(g.style.left) + parseFloat(g.style.width) / 2,
                     y: parseFloat(g.style.top) + parseFloat(g.style.height) / 2};
        return append.call(this, g);
    };
    applyPayload({state: after, actor: me, events: [ev]});
    await Anim.idle();
    delete ov.appendChild;
    return {start, ...piles};
}"""


import pytest  # noqa: E402


@pytest.mark.parametrize("borrowed", [False, True])
def test_partner_from_discard_flies_from_discard_pile(browser, server, borrowed):  # noqa: F811
    context, page, errors = motion_page(browser, server)
    start_as(page, "all")
    res = page.evaluate(FROM_DISCARD, borrowed)
    s = res["start"]
    assert s is not None
    dist = lambda c: abs(c["x"] - s["x"]) + abs(c["y"] - s["y"])  # noqa: E731
    assert dist(res["src"]) < 2 and dist(res["other"]) > 50
    context.close()
    assert not errors


def test_auto_open_waits_even_when_batch_arrives_twice(browser, server):  # noqa: F811
    # 同一批事件經 HTTP 回應與 WS 推送各到一次:第二次沒有新事件,也不能提早開啟
    context, page, errors = motion_page(browser, server)
    tp, _ = start_as(page, "all")
    page.evaluate("""() => {
        window.__openedAt = null;
        const ov = document.getElementById('book-review-overlay');
        new MutationObserver(() => { if (!ov.classList.contains('hidden') && window.__openedAt === null)
            window.__openedAt = performance.now(); }).observe(ov, {attributes: true});
    }""")
    t0 = page.evaluate("""() => {
        const me = S.turn_player, s = S.players[me].slots[0];
        const body = {state: {...S, pending: {kind: 'pick_mamodo_in_own_book', player: me, source: 'S-043',
            options: [{zone: 'book', player: me, page: 20, value: 20}]}}, actor: me,
            events: [{type: 'card_played', player: me, card: s.top, slot: s.uid, zone: 'mamodo', seq: animSeq}]};
        window.__t0 = performance.now();
        applyPayload(body);
        applyPayload(body);                                                   // WS 推送的同一批
        return window.__t0;
    }""")
    page.wait_for_function("window.__openedAt !== null", timeout=5000)
    assert page.evaluate("window.__openedAt") - t0 >= 450
    context.close()
    assert not errors
