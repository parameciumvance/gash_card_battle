"""MJ12 的放出與效果操作(battle-ui「MJ12 的放出與效果操作」)。需要 playwright 與 Chromium。

Run: python -m pytest tests/test_season4_mj12_ui.py -q
"""
from tests.test_choice_ui import pick_in_zoom, sent, set_pending, start
from tests.test_level3_ui import debug_edit
from tests.test_timing_ui import send, start_as

ABILITY_MP = {"mode": "mp", "mp_cost": 1, "timing": "nonbattle", "own_turn": False, "per_game": False}


def set_field(page, p, cards):
    """把 p 的獨立卡區換成 cards:[(uid, 卡號, ability_block)]。"""
    page.evaluate("""([p, cards, ability]) => {
        S = {...S, players: S.players.map((ps, i) => i !== p ? ps : {...ps, field_cards: cards.map(([uid, card, block]) =>
            ({uid, card, ability, ability_used: block === 'used' ? 'turn' : false, ability_block: block}))})};
        render();
    }""", [p, cards, ABILITY_MP])


def zoom_buttons(page):
    page.wait_for_function("!document.getElementById('zoom-overlay').classList.contains('hidden')")
    return page.locator("#zoom-actions button")


def test_play_and_use_mj12_end_to_end(page):
    tp, _ = start_as(page, "all")
    debug_edit(page, f"data.players[{tp}].book[1] = 'MJ-004'; data.players[{tp}].mp = 5;")
    send(page, tp, {"type": "flip_pages", "count": 0})
    page.wait_for_function(f"S.phase === 'battle' && S.players[{tp}].open_pages.some((e) => e.card === 'MJ-004')")
    page.evaluate(f"zoom('MJ-004', {{kind: 'page', p: {tp}, page: 2}})")
    play = zoom_buttons(page).filter(has_text=page.evaluate("t('ui.play')"))
    assert play.count() == 1 and play.is_enabled()
    play.click()
    page.wait_for_function(f"S.players[{tp}].field_cards.length === 1")
    uid = page.evaluate(f"S.players[{tp}].field_cards[0].uid")
    card = page.locator(f'.field-cards [data-field-uid="{uid}"]')
    assert card.count() == 1
    send(page, 1 - tp, {"type": "pass"})
    page.wait_for_function(f"S.action_player === {tp}")
    page.evaluate(f"zoom('MJ-004', {{kind: 'field', p: {tp}, uid: {uid}}})")
    use = zoom_buttons(page).filter(has_text=page.evaluate("t('ui.ability_mp', {n: 1})"))
    assert use.count() == 1 and use.is_enabled()
    use.click()
    page.wait_for_function(f"S.players[{tp}].mp === 4")


def test_used_field_ability_disabled_with_reason(page):
    p = start(page)
    set_field(page, p, [(900, "MJ-004", "used")])
    page.evaluate(f"zoom('MJ-004', {{kind: 'field', p: {p}, uid: 900}})")
    btn = zoom_buttons(page).filter(has_text=page.evaluate("t('ui.ability_mp', {n: 1})"))
    assert btn.count() == 1 and not btn.is_enabled()
    assert page.evaluate("t('ui.ability.used_turn')") in page.locator("#zoom-actions").inner_text()


def test_opponent_field_card_has_no_buttons(page):
    p = start(page)
    set_field(page, 1 - p, [(901, "MJ-004", None)])
    page.evaluate("SESSION = {...SESSION, viewer: %d}; render()" % p)
    page.evaluate(f"zoom('MJ-004', {{kind: 'field', p: {1 - p}, uid: 901}})")
    page.wait_for_function("!document.getElementById('zoom-overlay').classList.contains('hidden')")
    assert page.locator("#zoom-actions button").filter(has_text=page.evaluate("t('ui.ability_mp', {n: 1})")).count() == 0


def test_pick_target_in_field_zone(page):
    # Ex-074:對手獨立卡區的 MJ12 發光,點開選擇
    p = start(page)
    set_field(page, 1 - p, [(901, "MJ-001", None), (902, "MJ-006", None)])
    set_pending(page, {"kind": "pick_opponent_field_card", "player": p, "source": "Ex-074",
                       "options": [{"value": 901, "card": "MJ-001", "zone": "field", "player": 1 - p, "uid": 901},
                                   {"value": 902, "card": "MJ-006", "zone": "field", "player": 1 - p, "uid": 902}]})
    card = page.locator(f'.player-zone[data-player="{1 - p}"] .field-cards [data-field-uid="902"]')
    assert "pickable" in card.get_attribute("class").split()
    assert page.locator("#action-bar .choice-prompt").inner_text().find(page.evaluate(
        "t('choice.title.pick_opponent_field_card')")) >= 0
    card.click()
    pick_in_zoom(page)
    assert sent(page) == [{"type": "choose", "player": p, "value": 902}]


def test_log_lines(page):
    start(page)
    text = page.evaluate("logLine({type: 'field_card_effect', player: 1, card: 'MJ-006', amount: 3})")
    assert "MJ" not in text and page.evaluate("cname('MJ-006')") in text and "3" in text
    played = page.evaluate("logLine({type: 'card_played', player: 0, card: 'MJ-004', zone: 'field', field_uid: 5})")
    assert page.evaluate("cname('MJ-004')") in played


def test_fly_card_into_field_zone(browser, server):  # noqa: F811
    from tests.test_auto_open_pick_ui import motion_page
    context, page, errors = motion_page(browser, server)
    tp, _ = start_as(page, "all")
    res = page.evaluate("""async () => {
        const me = S.turn_player;
        const after = {...S, players: S.players.map((ps, i) => i !== me ? ps
            : {...ps, field_cards: [{uid: 950, card: 'MJ-004', ability: null, ability_used: false}]})};
        applyPayload({state: after, actor: me, events: [{type: 'card_played', player: me, card: 'MJ-004',
            zone: 'field', field_uid: 950, seq: animSeq}]});
        await new Promise((r) => setTimeout(r, 60));
        const ghost = document.querySelector('#anim-overlay .fx-fly-card');
        return !!ghost;
    }""")
    assert res
    context.close()
    assert not errors
