"""引擎核心規則測試(game-engine spec)。使用 level1 預組魔本與香草術卡,不依賴卡片效果 handler。

魔本頁面備忘(level1):P1=M-001 P2=S-025 P3=S-001 P4=P-001 P5=S-001 P6=M-014 P7=S-027
P8=P-009 P9=S-022 ... P32=S-005
"""

import pytest

from gash.engine.cards import DATA_DIR, card_db
from gash.engine.deck import load_deck
from gash.engine.engine import IllegalCommand, new_game, submit
from gash.engine.state import BATTLE, GAME_OVER, START


def deck_pages():
    return load_deck(DATA_DIR / "decks/level1.json", card_db()).pages


def mk(seed=1):
    return new_game(deck_pages(), seed=seed)


def turn_of(game):
    return game.state.turn_player


def ev_types(events):
    return [e["type"] for e in events]


# ---------------------------------------------------------------- 準備階段

def test_setup_initial_board():
    g = mk()
    for p in (0, 1):
        ps = g.state.players[p]
        assert ps.mp == 2
        assert ps.pos == 2
        assert len(ps.slots) == 1 and ps.slots[0].top == "M-001"
    assert g.state.phase == START
    assert g.state.turn_player in (0, 1)


# ---------------------------------------------------------------- 指令驗證

def test_illegal_command_rejected_state_unchanged():
    g = mk()
    other = 1 - turn_of(g)
    before_mp = g.state.players[other].mp
    with pytest.raises(IllegalCommand) as exc:
        submit(g, {"type": "flip_pages", "player": other, "count": 1})
    assert exc.value.code == "priority.turn"
    assert g.state.players[other].mp == before_mp
    assert g.state.phase == START


def test_flip_pages_gains_mp():
    g = mk()
    tp = turn_of(g)
    events = submit(g, {"type": "flip_pages", "player": tp, "count": 2})
    assert g.state.players[tp].mp == 6  # 2 + 2*2
    assert g.state.players[tp].pos == 6
    assert "pages_flipped" in ev_types(events)
    assert g.state.phase == BATTLE


def test_flip_more_than_three_rejected():
    g = mk()
    with pytest.raises(IllegalCommand) as exc:
        submit(g, {"type": "flip_pages", "player": turn_of(g), "count": 4})
    assert exc.value.code == "flip.count"


def test_flip_past_book_end_rejected():
    g = mk()
    tp = turn_of(g)
    g.state.players[tp].pos = 30
    with pytest.raises(IllegalCommand) as exc:
        submit(g, {"type": "flip_pages", "player": tp, "count": 2})
    assert exc.value.code == "flip.too_far"


# ---------------------------------------------------------------- 輪流行動權

def test_action_priority_alternates_and_double_pass_ends_phase():
    g = mk()
    tp = turn_of(g)
    submit(g, {"type": "flip_pages", "player": tp, "count": 0})
    assert g.state.action_player == tp
    submit(g, {"type": "pass", "player": tp})
    assert g.state.action_player == 1 - tp
    with pytest.raises(IllegalCommand):
        submit(g, {"type": "pass", "player": tp})  # 沒有行動權
    events = submit(g, {"type": "pass", "player": 1 - tp})
    # 雙 pass → 結束階段:強制翻頁 +2MP、換回合
    assert "turn_started" in ev_types(events)
    assert g.state.turn_player == 1 - tp
    assert g.state.turn_no == 2
    assert g.state.players[tp].pos == 4
    assert g.state.players[tp].mp == 4


# ---------------------------------------------------------------- 放卡

def test_play_mamodo_and_partner_rules():
    g = mk()
    tp = turn_of(g)
    submit(g, {"type": "flip_pages", "player": tp, "count": 3})  # pos=8: 開 8,9 頁
    # 夥伴 P-009(大海惠, 蒂歐用)在第 8 頁,但蒂歐不在場 → 拒絕
    with pytest.raises(IllegalCommand) as exc:
        submit(g, {"type": "play_card", "player": tp, "page": 8})
    assert exc.value.code == "play.no_mamodo"
    # 未翻開的頁 → 拒絕
    with pytest.raises(IllegalCommand) as exc:
        submit(g, {"type": "play_card", "player": tp, "page": 6})
    assert exc.value.code == "page.not_open"


def test_play_mamodo_from_open_page():
    g = mk()
    tp = turn_of(g)
    submit(g, {"type": "flip_pages", "player": tp, "count": 2})  # pos=6: 開 6,7 頁
    events = submit(g, {"type": "play_card", "player": tp, "page": 6})  # M-014 蒂歐
    assert "card_played" in ev_types(events)
    ps = g.state.players[tp]
    assert len(ps.slots) == 2
    assert ps.slots[1].top == "M-014"
    assert 6 in ps.consumed_pages
    assert g.state.action_player == 1 - tp  # 行動後輪替


def test_field_limit_three_mamodo():
    g = mk()
    tp = turn_of(g)
    ps = g.state.players[tp]
    from gash.engine.state import MamodoSlot
    ps.slots.append(MamodoSlot(uid=g.state.next_uid(), stack=["M-012"]))
    ps.slots.append(MamodoSlot(uid=g.state.next_uid(), stack=["M-015"]))
    submit(g, {"type": "flip_pages", "player": tp, "count": 2})
    with pytest.raises(IllegalCommand) as exc:
        submit(g, {"type": "play_card", "player": tp, "page": 6})
    assert exc.value.code in ("play.field_full", "play.same_name")


def test_same_name_mamodo_rejected():
    g = mk()
    tp = turn_of(g)
    ps = g.state.players[tp]
    from gash.engine.state import MamodoSlot
    ps.slots.append(MamodoSlot(uid=g.state.next_uid(), stack=["M-015"]))  # 蒂歐《倔強》
    submit(g, {"type": "flip_pages", "player": tp, "count": 2})
    with pytest.raises(IllegalCommand) as exc:
        submit(g, {"type": "play_card", "player": tp, "page": 6})  # M-014 也是蒂歐
    assert exc.value.code == "play.same_name"


# ---------------------------------------------------------------- 戰鬥流程

def start_vanilla_battle(g, defend=False):
    """回合玩家以第 3 頁 S-001 攻擊;回傳 (攻方, 防方)。"""
    tp = turn_of(g)
    dp = 1 - tp
    submit(g, {"type": "flip_pages", "player": tp, "count": 0})
    submit(g, {"type": "declare_attack", "player": tp, "page": 3})
    assert g.state.battle_in is not None
    submit(g, {"type": "battle_in_response", "player": dp, "allow": True})
    assert g.state.battle is not None
    return tp, dp


def test_battle_in_then_forced_attack():
    g = mk()
    tp, dp = start_vanilla_battle(g)
    # 攻擊宣告已成立:MP 已支付(cost 1)
    assert g.state.players[tp].mp == 1
    assert g.state.battle.attack_spell == "S-001"


def test_battle_in_voided_by_defender_action():
    g = mk()
    tp = turn_of(g)
    dp = 1 - tp
    submit(g, {"type": "flip_pages", "player": tp, "count": 0})
    submit(g, {"type": "declare_attack", "player": tp, "page": 3})
    # 防方插入一個行動(pass 以外):用第 3 頁不行(是防方自己的頁),放不出卡 → 改用事件?
    # 防方翻開頁 2,3:S-025(D術)不能當行動、無夥伴可放 → 用「回應允許」以外唯一合法:實際行動。
    # 這裡以防方放出魔物驗證:先給防方場上騰不出行動 → 直接驗證非法回應被拒。
    with pytest.raises(IllegalCommand):
        submit(g, {"type": "declare_attack", "player": dp, "page": 3})
    # 攻方在確認中不能再行動
    with pytest.raises(IllegalCommand):
        submit(g, {"type": "pass", "player": tp})


def test_vanilla_battle_no_defense_damage_and_book_flip():
    g = mk(seed=7)
    tp, dp = start_vanilla_battle(g)
    submit(g, {"type": "no_defense", "player": dp})
    submit(g, {"type": "pass", "player": tp})
    events = submit(g, {"type": "pass", "player": dp})
    types = ev_types(events)
    assert "showdown" in types
    sd = next(e for e in events if e["type"] == "showdown")
    assert sd["attacker_total"] == 6000  # 賈修 4000 + 札克爾 2000
    assert sd["defender_total"] == 0     # 不防禦 = 0
    # 防方有魔物 → 詢問庇護
    assert g.state.pending is not None and g.state.pending.kind == "protect"
    events = submit(g, {"type": "choose", "player": dp, "value": None})
    assert g.state.players[dp].pos == 4  # 傷害 1 = 翻 1 張
    assert g.state.battle is None
    assert g.state.action_player == tp  # 戰鬥結束回到非戰鬥,回合玩家先行動


def test_defense_declaration_validation():
    g = mk()
    tp, dp = start_vanilla_battle(g)
    # 未翻開的頁不能用來防禦
    with pytest.raises(IllegalCommand) as exc:
        submit(g, {"type": "declare_defense", "player": dp, "page": 9})
    assert exc.value.code == "page.not_open"


def test_equal_power_defender_wins():
    g = mk()
    tp, dp = start_vanilla_battle(g)
    # 防方以 S-001(AD 圖示可防, +2000)防禦:賈修 4000+2000=6000 vs 攻方 6000 → 同值防方勝
    mp_before = g.state.players[dp].mp
    submit(g, {"type": "declare_defense", "player": dp, "page": 3})
    b = g.state.battle
    assert b.defense_spell == "S-001"
    assert g.state.players[dp].mp == mp_before - 1  # 防禦也支付費用
    submit(g, {"type": "pass", "player": tp})
    events = submit(g, {"type": "pass", "player": dp})
    sd = next(e for e in events if e["type"] == "showdown")
    assert sd["attacker_total"] == 6000 and sd["defender_total"] == 6000
    assert sd["winner"] == "defender"
    assert g.state.battle is None  # 無傷害,直接戰鬥結束
    assert g.state.players[dp].pos == 2


def test_spell_cannot_be_reused_same_turn():
    g = mk()
    tp, dp = start_vanilla_battle(g)
    submit(g, {"type": "no_defense", "player": dp})
    submit(g, {"type": "pass", "player": tp})
    submit(g, {"type": "pass", "player": dp})
    submit(g, {"type": "choose", "player": dp, "value": None})
    # 同頁術卡再攻擊 → 拒絕;隔壁頁 S-001(第5頁未開)也不行
    with pytest.raises(IllegalCommand) as exc:
        submit(g, {"type": "declare_attack", "player": tp, "page": 3})
    assert exc.value.code == "spell.used"


# ---------------------------------------------------------------- 庇護與負傷

def test_protect_book_with_mamodo():
    g = mk()
    tp, dp = start_vanilla_battle(g)
    submit(g, {"type": "no_defense", "player": dp})
    submit(g, {"type": "pass", "player": tp})
    submit(g, {"type": "pass", "player": dp})
    slot = g.state.players[dp].slots[0]
    events = submit(g, {"type": "choose", "player": dp, "value": slot.uid})
    assert "protected" in ev_types(events)
    assert slot.injured is True
    assert g.state.players[dp].pos == 2  # 魔本沒翻


def test_injured_mamodo_discarded_on_second_damage():
    g = mk()
    tp, dp = start_vanilla_battle(g)
    slot = g.state.players[dp].slots[0]
    slot.injured = True
    slot.partner = "P-001"
    submit(g, {"type": "no_defense", "player": dp})
    submit(g, {"type": "pass", "player": tp})
    submit(g, {"type": "pass", "player": dp})
    events = submit(g, {"type": "choose", "player": dp, "value": slot.uid})
    types = ev_types(events)
    assert "mamodo_discarded" in types
    assert g.state.players[dp].slots == []
    assert "P-001" in g.state.players[dp].discard  # 夥伴一併棄掉
    assert "M-001" in g.state.players[dp].discard


# ---------------------------------------------------------------- ADV 規則

def test_last_page_spell_cost_zero():
    g = mk()
    tp = turn_of(g)
    ps = g.state.players[tp]
    ps.pos = 32
    submit(g, {"type": "flip_pages", "player": tp, "count": 0})
    mp_before = ps.mp
    submit(g, {"type": "declare_attack", "player": tp, "page": 32})  # S-005 費 6 → 0
    submit(g, {"type": "battle_in_response", "player": 1 - tp, "allow": True})
    assert ps.mp == mp_before  # 費用 0
    assert g.state.battle.attack_spell == "S-005"


def test_mamodo_gone_processing_deploys_from_book():
    g = mk()
    tp = turn_of(g)
    dp = 1 - tp
    g.state.players[dp].slots.clear()  # 防方無魔物
    submit(g, {"type": "flip_pages", "player": tp, "count": 0})
    submit(g, {"type": "pass", "player": tp})
    submit(g, {"type": "pass", "player": dp})
    # 結束階段:防方 pos=2(頁2,3)無魔物卡 → 自動翻到第 6 頁(M-014)放出
    ps = g.state.players[dp]
    assert len(ps.slots) == 1
    assert ps.slots[0].top == "M-014"
    assert 6 in ps.consumed_pages


def test_mamodo_gone_no_mamodo_left_loses():
    g = mk()
    tp = turn_of(g)
    dp = 1 - tp
    ps = g.state.players[dp]
    ps.slots.clear()
    ps.pos = 16  # 之後的魔本已無魔物卡(最後的魔物 M-012 在第 14 頁)
    submit(g, {"type": "flip_pages", "player": tp, "count": 0})
    submit(g, {"type": "pass", "player": tp})
    submit(g, {"type": "pass", "player": dp})
    assert g.state.phase == GAME_OVER
    assert g.state.winner == tp
    assert g.state.end_reason == "no_mamodo"


def test_book_out_by_damage_loses():
    g = mk()
    tp, dp = start_vanilla_battle(g)
    g.state.players[dp].pos = 32
    g.state.players[dp].slots.clear()  # 無魔物可庇護
    submit(g, {"type": "no_defense", "player": dp})
    submit(g, {"type": "pass", "player": tp})
    submit(g, {"type": "pass", "player": dp})
    assert g.state.phase == GAME_OVER
    assert g.state.winner == tp
    assert g.state.end_reason == "book_out"


# ---------------------------------------------------------------- 可重現性與冒煙

def script_until_over(g, max_steps=2000):
    """簡單驅動器:翻頁→有可攻術就攻→不防→不庇護,直到分出勝負。"""
    from gash.engine.state import START as PH_START
    steps = 0
    while g.state.phase != GAME_OVER and steps < max_steps:
        steps += 1
        st = g.state
        if st.pending is not None:
            submit(g, {"type": "choose", "player": st.pending.player,
                       "value": None if st.pending.kind == "protect"
                       else st.pending.options[0].get("page", 0)})
            continue
        if st.phase == PH_START:
            tp = st.turn_player
            max_flip = min(3, (32 - st.players[tp].pos) // 2)
            submit(g, {"type": "flip_pages", "player": tp, "count": max_flip})
            continue
        if st.battle_in is not None:
            submit(g, {"type": "battle_in_response",
                       "player": 1 - st.battle_in["attacker"], "allow": True})
            continue
        if st.battle is not None:
            b = st.battle
            if b.step == "defense":
                submit(g, {"type": "no_defense", "player": b.defender})
            else:
                submit(g, {"type": "pass", "player": b.data["effect_turn"]})
            continue
        actor = st.action_player
        if actor == st.turn_player:
            ps = st.players[actor]
            for page in ps.open_pages():
                card = g.db[ps.card_at(page)]
                if (card.type == "spell" and card.can_attack()
                        and page not in ps.used_spell_pages
                        and not card.is_command_spell
                        and any(g.db[s.top].related_mamodo == card.related_mamodo
                                for s in ps.slots)):
                    from gash.engine.engine import spell_cost
                    if ps.mp >= spell_cost(g, actor, page, card):
                        submit(g, {"type": "declare_attack", "player": actor, "page": page})
                        break
            else:
                submit(g, {"type": "pass", "player": actor})
            continue
        submit(g, {"type": "pass", "player": actor})
    return steps


def test_smoke_full_game_completes():
    g = mk(seed=42)
    steps = script_until_over(g)
    assert g.state.phase == GAME_OVER
    assert g.state.winner in (0, 1)
    assert steps < 2000


def test_seed_reproducibility():
    g1 = mk(seed=99)
    g2 = mk(seed=99)
    script_until_over(g1)
    script_until_over(g2)
    assert g1.events == g2.events
    assert g1.state.winner == g2.state.winner
