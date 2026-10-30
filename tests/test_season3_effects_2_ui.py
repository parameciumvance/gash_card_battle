"""第 3 賽季效果第 2 批的前端顯示(battle-ui「個別卡片效果的記錄與作用中效果」「操作與決策互動」)。"""

from tests.test_choice_ui import start


def test_option_labels(page):
    start(page)
    labels = page.evaluate("""['heal_all_injured', 'restrict_both_effects_spells', 'coin_redirect_damage',
        'opponent_no_defense_spell', 'opponent_no_protect'].map((label) => choiceLabel({value: label, label}))""")
    assert labels == ["自己場上的負傷魔物全部回復健康", "本回合雙方都不能使用魔物效果與戰術",
                      "擲幣:正面改傷害對手 1 隻魔物,反面這個戰術無效", "對手不能使用選定魔物的防禦戰術",
                      "對手不能以選定魔物保護"]


def test_effect_texts(page):
    start(page)
    texts = page.evaluate("""(() => {
        const base = {owner: 0, target_player: 1, target_slot: null, duration: 'turn', created_turn: S.turn_no};
        return [
          effectText({...base, type: 'modifier', kind: 'restriction', flag: 'no_events', source: 'P-042'}),
          effectText({...base, type: 'modifier', kind: 'restriction', flag: 'no_named_spells', source: 'PR-009',
                      target_player: 0, mamodo: 'ガッシュ・ベル'}),
          effectText({...base, type: 'modifier', kind: 'named_immune', source: 'PR-009', target_player: 0,
                      mamodo: 'ガッシュ・ベル'}),
          effectText({type: 'standby', kind: 'battle_lock', source: 'P-042', owner: 0, mamodo: 'ダニー',
                      expires: 'next_battle'}),
          effectText({type: 'static', kind: 'event_lock', source: 'P-038', owner: 0, target_player: 1,
                      target_slot: null}),
        ];
    })()""")
    p1, p0 = page.evaluate("[pname(1), pname(0)]")
    assert texts[0] == f"{p1} 不能使用事件卡"
    assert texts[2].startswith(f"{p0} 的魔書與 ") and texts[2].endswith(" 不受傷害")
    assert texts[3].startswith("下一場戰鬥:以 ") and texts[3].endswith(" 攻擊時,對手不能使用搭檔效果與事件卡")
    assert texts[4] == f"{p1} 在對手的戰鬥階段不能使用事件卡"
    assert all("{" not in t for t in texts)


def test_log_lines(page):
    start(page)
    lines = page.evaluate("""[
        logLine({type: 'protect_forced', player: 1, slot: 1, card: 'M-001', source: 'Ex-047'}),
        logLine({type: 'attack_redirected', player: 0, slot: 1, card: 'M-001', source: 'M-055'}),
        logLine({type: 'mamodo_injured', player: 1, slot: 1, card: 'M-001', source: 'M-059', reason: 'effect'}),
    ]""")
    assert all(line and "{" not in line for line in lines)
    assert "不是傷害" in lines[2]
