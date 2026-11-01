"""放大檢視停用按鈕的原因(battle-ui「停用按鈕的原因」「卡片放大檢視」)。需要 playwright 與 Chromium。

level1 預組開局:場上ガッシュ・ベル(效果只能在戰鬥中使用,MP 1),翻開第 2 頁 S-025(防禦)、第 3 頁 S-001(攻防)。

Run: python -m pytest tests/test_disabled_reasons_ui.py -q
"""
from tests.test_timing_ui import send, start_as


def zoom_slot(page, p):
    page.evaluate("p => zoom(S.players[p].slots[0].top, {kind: 'slot', p, uid: S.players[p].slots[0].uid})", p)


def zoom_page(page, p, number):
    page.evaluate("([p, n]) => zoom(n, {kind: 'page', p, page: S.players[p].open_pages.find(e => e.card === n).page})",
                  [p, number])


def actions(page):
    """放大檢視的 [(按鈕文字, 啟用, 原因)]。"""
    return page.evaluate("""() => [...document.querySelectorAll('#zoom-actions .zoom-action')].map(row => {
        const b = row.querySelector('button'), why = row.querySelector('.zoom-reason');
        return [b.textContent, !b.disabled, why ? why.textContent : null];
    })""")


def tweak(page, code):
    page.evaluate("() => { " + code + "; render(); if (ZOOM) renderZoom(); }")


def usable_marked(page, p, page_no):
    return page.evaluate(f"""() => !!document.querySelector('[data-book-block="{p}"] .card.usable')
        && [...document.querySelectorAll('[data-book-block="{p}"] .card.usable')].some(el => el.dataset.card === S.players[{p}].book[{page_no} - 1])""")


def to_nonbattle(page, me):
    tp, mine = start_as(page, me)
    send(page, tp, {"type": "flip_pages", "count": 0})
    page.wait_for_function("S.phase === 'battle'")
    return tp, mine


def test_gash_effect_outside_battle(page):
    tp, me = to_nonbattle(page, "turn")
    assert page.evaluate(f"S.players[{me}].slots[0].ability_block") == "timing_battle"   # 伺服器的判斷
    zoom_slot(page, me)
    assert actions(page) == [["效果(MP 1)", False, "只能在戰鬥中使用"]]


def test_usable_card_waits_for_my_action(page):
    tp, me = to_nonbattle(page, "other")
    tweak(page, f"""const s = S.players[{me}].slots[0];
        s.ability = {{...s.ability, timing: 'nonbattle'}}; s.ability_block = null; S.players[{me}].mp = 5""")
    zoom_slot(page, me)
    assert actions(page)[0][1:] == [False, "輪到你行動時才能使用"]


def test_start_phase_and_pending_reasons(page):
    tp, me = start_as(page, "turn")
    tweak(page, f"""const s = S.players[{me}].slots[0];
        s.ability = {{...s.ability, timing: 'nonbattle'}}; s.ability_block = null""")
    zoom_slot(page, me)
    assert actions(page)[0][2] == "戰鬥階段才能使用"
    tweak(page, f"S.phase = 'battle'; S.pending = {{kind: 'x', player: {me}}}")
    assert actions(page)[0][2] == "請先完成目前的選擇"


def test_block_reasons_from_snapshot(page):
    tp, me = to_nonbattle(page, "turn")
    zoom_slot(page, me)
    tweak(page, f"S.players[{me}].slots[0].ability_block = 'mp'; S.players[{me}].mp = 0")
    assert actions(page)[0][2] == "MP 不足（目前 0，需要 1）"
    tweak(page, f"S.players[{me}].slots[0].ability_block = 'condition'")
    assert actions(page)[0][2] == page.evaluate("t('error.ability.condition')")
    tweak(page, f"S.players[{me}].slots[0].ability_block = 'mamodo_locked'")
    assert actions(page)[0][2] == page.evaluate("t('error.ability.mamodo_locked')")
    tweak(page, f"S.players[{me}].slots[0].ability_block = 'used'")
    assert actions(page)[0][2] == "本回合已使用"


def test_attack_spell_on_opponents_turn(page):
    tp, me = to_nonbattle(page, "other")
    tweak(page, f"S.players[{me}].open_pages[1] = {{...S.players[{me}].open_pages[1], card: 'S-004'}}")
    zoom_page(page, me, "S-004")
    assert actions(page) == [["攻擊", False, "只能在自己的回合攻擊"]]
    zoom_page(page, me, "S-025")                                          # 防禦戰術
    assert actions(page) == [["防禦", False, "對手攻擊時才能用來防禦"]]


def test_defense_spell_on_own_turn_does_not_glow(page):
    tp, me = to_nonbattle(page, "turn")
    zoom_page(page, me, "S-025")
    assert actions(page) == [["防禦", False, "對手攻擊時才能用來防禦"]]
    page.evaluate("closeZoom()")
    assert not usable_marked(page, me, 2)
    assert usable_marked(page, me, 3)                                     # 可攻擊的 S-001 照舊發光


def test_attack_spell_waits_for_my_action(page):
    tp, me = to_nonbattle(page, "turn")
    send(page, tp, {"type": "pass"})
    page.wait_for_function(f"S.action_player === {1 - tp}")
    zoom_page(page, me, "S-001")
    assert actions(page) == [["攻擊", False, "輪到你行動時才能使用"]]


def test_event_in_battle(page):
    tp, me = to_nonbattle(page, "turn")
    tweak(page, f"""S.players[{me}].open_pages[0] = {{...S.players[{me}].open_pages[0], card: 'E-001'}};
        S.battle = {{step: 'effects', attacker: {me}, effect_turn: {1 - me}}}""")
    zoom_page(page, me, "E-001")
    assert actions(page) == [["使用", False, "非戰鬥中才能使用"]]


def test_opponent_and_spectator_see_no_buttons(page):
    tp, me = to_nonbattle(page, "turn")
    page.evaluate(f"SESSION = {{...SESSION, viewer: {1 - me}}}; render();")
    zoom_slot(page, me)
    assert actions(page) == []
    page.evaluate("SESSION = {...SESSION, viewer: 'spectator'}; render();")
    zoom_slot(page, me)
    assert actions(page) == []
