"""第 3 賽季效果第 1 批的前端顯示(battle-ui「個別卡片效果的記錄與作用中效果」「操作與決策互動」)。"""

from tests.test_choice_ui import start


def test_option_labels(page):
    start(page)
    labels = page.evaluate("""['gain_mp_3', 'reduce_opponent_mp_3', 'both_mp_plus_2', 'both_mp_minus_2']
        .map((label) => choiceLabel({value: label, label}))""")
    assert labels == ["自己的 MP +3", "對手的 MP -3", "雙方的 MP 各 +2", "雙方的 MP 各 -2"]


def test_effect_texts(page):
    start(page)
    assert page.evaluate("""effectText({type: 'modifier', kind: 'power_per_own_mamodo', source: 'E-048', owner: 0,
        target_player: 0, target_slot: null, amount: 1000, duration: 'until_end_next_turn'})""") \
        == "自己的魔物 魔力 +(場上魔物數 × +1000)"
    named = page.evaluate("""effectText({type: 'modifier', kind: 'spell_named', source: 'PR-010', owner: 0,
        target_player: 0, target_slot: null, mamodo: 'ガッシュ・ベル', name: 'ザケル', cost: -1, power: 2000,
        duration: 'turn'})""")
    assert "「ザケル」" in named and "本來費用 -1" in named and "魔力 +2000" in named
    assert "本來費用為 0" in page.evaluate("""effectText({type: 'standby', kind: 'spell_bonus', source: 'Ex-007',
        owner: 0, mamodo: 'ガッシュ・ベル', base_zero: true, expires: 'next_battle'})""")
    assert "本來費用 -5" in page.evaluate("""effectText({type: 'standby', kind: 'spell_bonus', source: 'Ex-035',
        owner: 0, mamodo: 'ブラゴ', base_delta: -5, expires: 'next_battle'})""")
    assert page.evaluate("effectWhen({type: 'modifier', duration: 'game', created_turn: S.turn_no})") == "本場遊戲中"
    assert page.evaluate("effectWhen({type: 'standby', expires: 'own_start'})") == "使用者的下一個回合開始時"


def test_breakdown_labels(page):
    start(page)
    texts = page.evaluate("""['static_spell', 'spell_named', 'static_total', 'per_mamodo', 'base_delta']
        .map((kind) => t(`breakdown.${kind}`, {card: 'X'}))""")
    assert all("X" in s and not s.startswith("breakdown.") for s in texts)


def test_vanilla_mamodo_has_no_effect_ui(page):
    p = start(page)
    result = page.evaluate("""(p) => {
        S = {...S, phase: 'battle', turn_player: p, action_player: p, battle: null, battle_in: null, pending: null,
             players: S.players.map((x, i) => i !== p ? x : {...x, mp: 10, slots: x.slots.map((s, j) => j !== 0 ? s :
               {...s, stack: ['Ex-001'], top: 'Ex-001', partner: null, ability: null, partner_ability: null,
                mamodo_attack: null, mamodo_defense: null, action_discard: false})})};
        render();
        const uid = S.players[p].slots[0].uid;
        return [zoomActions({kind: 'slot', p, uid}).buttons.length, TEXT['Ex-001'].effect];
    }""", p)
    assert result == [0, ""]


def test_mamodo_attack_button_until_per_turn_used(page):
    # M-068:每回合 2 次,快照在用滿前不標示已使用
    p = start(page)
    labels = page.evaluate("""(p) => {
        S = {...S, phase: 'battle', turn_player: p, action_player: p, battle: null, battle_in: null, pending: null,
             players: S.players.map((x, i) => i !== p ? x : {...x, mp: 10, slots: x.slots.map((s, j) => j !== 0 ? s :
               {...s, stack: ['M-068'], top: 'M-068', ability: null,
                mamodo_attack: {mp_cost: 1, power: 6000, damage: 1, per_turn: 2}, mamodo_attack_used: false})})};
        render();
        return zoomActions({kind: 'slot', p, uid: S.players[p].slots[0].uid}).buttons.map((b) => b.disabled);
    }""", p)
    assert labels == [False]
