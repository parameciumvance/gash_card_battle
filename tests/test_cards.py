"""逐卡效果測試(card-effects spec):每張非香草卡至少一個行為測試,
e/j 差異卡驗證為日版 j 行為。硬幣以腳本化 RNG 控制(<0.5 = 正面)。"""

import pytest

from gash.engine.cards import DATA_DIR, card_db
from gash.engine.deck import load_deck
from gash.engine.engine import IllegalCommand, new_game, slot_power, spell_cost, submit
from gash.engine.state import GAME_OVER, MamodoSlot


class Rng:
    """腳本化 RNG:random() 依序回傳 seq,之後固定 0.9(反面)。"""

    def __init__(self, *seq):
        self.seq = list(seq)

    def random(self):
        return self.seq.pop(0) if self.seq else 0.9

    def randint(self, a, b):
        return a


HEADS, TAILS = 0.1, 0.9


def deck_pages():
    return load_deck(DATA_DIR / "decks/level1.json", card_db()).pages


def book(first="M-001", p2=None, p3=None, fill="S-001", last="S-005", **pages):
    b = [fill] * 32
    b[0] = first
    b[31] = last
    if p2:
        b[1] = p2
    if p3:
        b[2] = p3
    for k, v in pages.items():  # p10="E-001" 形式
        b[int(k[1:]) - 1] = v
    return b


def game(book0=None, book1=None, turn=0, coins=()):
    g = new_game(deck_pages(), seed=1,
                 decks=(list(book0 or deck_pages()), list(book1 or deck_pages())))
    g.state.turn_player = turn
    g.rng = Rng(*coins)
    return g


def slot0(g, p):
    return g.state.players[p].slots[0]


def give(g, p, number, injured=False, partner=None):
    s = MamodoSlot(uid=g.state.next_uid(), stack=[number], injured=injured, partner=partner)
    g.state.players[p].slots.append(s)
    return s


def start_attack(g, page, slot_uid=None, flip=0):
    tp = g.state.turn_player
    submit(g, {"type": "flip_pages", "player": tp, "count": flip})
    cmd = {"type": "declare_attack", "player": tp, "page": page}
    if slot_uid is not None:
        cmd["slot_uid"] = slot_uid
    submit(g, cmd)
    submit(g, {"type": "battle_in_response", "player": 1 - tp, "allow": True})
    return tp, 1 - tp


def both_pass(g):
    b = g.state.battle
    out = []
    out += submit(g, {"type": "pass", "player": b.data["effect_turn"]})
    if g.state.battle is not None:
        out += submit(g, {"type": "pass", "player": g.state.battle.data["effect_turn"]})
    return out


def showdown_of(events):
    return next(e for e in events if e["type"] == "showdown")


def end_turn(g):
    st = g.state
    if st.phase == "start":
        submit(g, {"type": "flip_pages", "player": st.turn_player, "count": 0})
    submit(g, {"type": "pass", "player": st.action_player})
    submit(g, {"type": "pass", "player": st.action_player})


# ================================================================ 魔物

def test_m001_attack_power_boost():
    g = game()
    tp, dp = start_attack(g, 3)  # S-001
    g.state.players[tp].mp = 5
    submit(g, {"type": "no_defense", "player": dp})
    submit(g, {"type": "use_field_ability", "player": tp, "zone": "mamodo",
               "slot_uid": slot0(g, tp).uid})
    submit(g, {"type": "pass", "player": dp})
    events = submit(g, {"type": "pass", "player": tp})
    assert showdown_of(events)["attacker_total"] == 7000  # 4000+1000+2000


def test_m002_start_phase_mp():
    g = game(book0=book(first="M-002"))
    tp = g.state.turn_player
    assert g.state.players[tp].mp == 2
    submit(g, {"type": "flip_pages", "player": tp, "count": 0})
    assert g.state.players[tp].mp == 3  # MP≤2 → +1


def test_m003_injured_bonus():
    g = game(book0=book(first="M-003"))
    s = slot0(g, 0)
    assert slot_power(g, 0, s) == 4000
    s.injured = True
    assert slot_power(g, 0, s) == 5000


def test_m004_partner_bonus():
    g = game(book0=book(first="M-004"))
    s = slot0(g, 0)
    assert slot_power(g, 0, s) == 3000
    s.partner = "P-002"
    assert slot_power(g, 0, s) == 4000


def test_m005_damage_boost():
    g = game(book0=book(first="M-005", p3="S-008"))
    g.state.players[0].mp = 10
    tp, dp = start_attack(g, 3)  # S-008 dam2
    submit(g, {"type": "no_defense", "player": dp})
    submit(g, {"type": "use_field_ability", "player": tp, "zone": "mamodo",
               "slot_uid": slot0(g, tp).uid})
    submit(g, {"type": "pass", "player": dp})
    submit(g, {"type": "pass", "player": tp})
    submit(g, {"type": "choose", "player": dp, "value": None})
    assert g.state.players[dp].pos == 2 + 2 * 3  # 傷害 2+1=3


def test_m006_opponent_no_spells_on_entry():
    g = game(book0=book(p2="M-006"))
    tp = g.state.turn_player
    dp = 1 - tp
    submit(g, {"type": "flip_pages", "player": tp, "count": 0})
    submit(g, {"type": "play_card", "player": tp, "page": 2})
    # 對手本回合不能使用術卡:防禦宣告也會被拒
    submit(g, {"type": "pass", "player": dp})
    submit(g, {"type": "declare_attack", "player": tp, "page": 3})
    submit(g, {"type": "battle_in_response", "player": dp, "allow": True})
    with pytest.raises(IllegalCommand) as exc:
        submit(g, {"type": "declare_defense", "player": dp, "page": 3})
    assert exc.value.code == "spell.restricted"


def test_m007_stack_and_page_flip():
    g = game(book0=book(p2="M-007"))
    give(g, 0, "M-006")
    tp = 0
    dp = 1
    pos_before = g.state.players[dp].pos
    submit(g, {"type": "flip_pages", "player": tp, "count": 0})
    submit(g, {"type": "play_card", "player": tp, "page": 2})
    s = g.state.players[0].slots[-1]
    assert s.top == "M-007" and s.stack == ["M-006", "M-007"]
    assert g.state.players[dp].pos == pos_before + 2  # 翻對手 1 張


def test_m007_requires_base():
    g = game(book0=book(p2="M-007"))
    submit(g, {"type": "flip_pages", "player": 0, "count": 0})
    with pytest.raises(IllegalCommand) as exc:
        submit(g, {"type": "play_card", "player": 0, "page": 2})
    assert exc.value.code == "play.no_base"


def test_m008_spell_discount_and_power_cut():
    g = game(book0=book(first="M-008", p3="S-014"))
    tp = 0
    submit(g, {"type": "flip_pages", "player": tp, "count": 0})
    submit(g, {"type": "use_field_ability", "player": tp, "zone": "mamodo",
               "slot_uid": slot0(g, tp).uid})
    card = g.db["S-014"]
    assert spell_cost(g, tp, 3, card) == 1  # 2-1
    submit(g, {"type": "pass", "player": 1})
    submit(g, {"type": "declare_attack", "player": tp, "page": 3})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    assert g.state.players[tp].mp == 1  # 2-1
    submit(g, {"type": "no_defense", "player": 1})
    events = both_pass(g)
    assert showdown_of(events)["attacker_total"] == 3500 + 2000 - 1000


def test_m009_mp_on_discard():
    g = game()
    dp = 1 - g.state.turn_player
    kolulu = give(g, dp, "M-009", injured=True)
    tp, _ = start_attack(g, 3)
    submit(g, {"type": "no_defense", "player": dp})
    submit(g, {"type": "pass", "player": tp})
    submit(g, {"type": "pass", "player": dp})
    mp_before = g.state.players[dp].mp
    submit(g, {"type": "choose", "player": dp, "value": kolulu.uid})  # 保護 → 負傷再受傷 → 棄掉
    assert g.state.players[dp].mp == mp_before + 4


def test_m010_defense_boost_and_s016():
    g = game(book1=book(p2="S-016"))
    dp = 1
    base = give(g, dp, "M-009")
    base.stack.append("M-010")
    tp, _ = start_attack(g, 3)
    g.state.players[dp].mp = 5
    submit(g, {"type": "declare_defense", "player": dp, "page": 2})
    submit(g, {"type": "pass", "player": tp})
    submit(g, {"type": "use_field_ability", "player": dp, "zone": "mamodo",
               "slot_uid": base.uid})
    submit(g, {"type": "pass", "player": tp})
    events = submit(g, {"type": "pass", "player": dp})
    sd = showdown_of(events)
    # M-010 4000 + S-016(+2000) + 防禦時+1000 + [1MP]+1000 = 8000 > 6000
    assert sd["defender_total"] == 8000
    assert sd["winner"] == "defender"


def test_m011_discard_mamodo_from_book_once_per_game():
    g = game()
    fein = give(g, 0, "M-011")
    submit(g, {"type": "flip_pages", "player": 0, "count": 0})
    submit(g, {"type": "use_field_ability", "player": 0, "zone": "mamodo",
               "slot_uid": fein.uid})
    assert g.state.pending is not None and g.state.pending.kind == "m011_pick"
    submit(g, {"type": "choose", "player": 0, "value": 6})  # 對手第 6 頁 M-014
    assert "M-014" in g.state.players[1].discard
    assert 6 in g.state.players[1].consumed_pages
    # 一場遊戲限一次(跨回合仍不可)
    end_turn(g)
    end_turn(g)
    submit(g, {"type": "flip_pages", "player": 0, "count": 0})
    with pytest.raises(IllegalCommand) as exc:
        submit(g, {"type": "use_field_ability", "player": 0, "zone": "mamodo",
                   "slot_uid": fein.uid})
    assert exc.value.code == "ability.per_game"


def test_m012_reflip_coin():
    g = game(coins=(TAILS, HEADS))  # 首擲反面,重擲正面
    dp = 1 - g.state.turn_player
    give(g, dp, "M-012")
    tp, _ = start_attack(g, 3)
    # S-025 為指示術,防方有 2 隻魔物須指定使用者
    submit(g, {"type": "declare_defense", "player": dp, "page": 2,
               "slot_uid": slot0(g, dp).uid})
    assert g.state.pending.kind == "coin_confirm"
    submit(g, {"type": "choose", "player": dp, "value": 0})  # 用 M-012 重擲
    assert g.state.battle.attack_negated is True  # 重擲為正面 → 攻擊無效
    assert "mamodo:M-012" in g.state.players[dp].used_abilities


def test_s025_j_version_single_coin():
    g = game(coins=(HEADS,))
    dp = 1 - g.state.turn_player
    tp, _ = start_attack(g, 3)
    events = submit(g, {"type": "declare_defense", "player": dp, "page": 2})
    coin_events = [e for e in events if e["type"] == "coin_flipped"]
    assert len(coin_events) == 1  # 日版:只擲 1 次
    assert g.state.battle.attack_negated is True


def test_m013_no_damage_when_injured():
    g = game()
    dp = 1 - g.state.turn_player
    kan = give(g, dp, "M-013", injured=True)
    g.state.players[dp].mp = 5
    tp, _ = start_attack(g, 3)
    submit(g, {"type": "no_defense", "player": dp})
    submit(g, {"type": "pass", "player": tp})
    submit(g, {"type": "use_field_ability", "player": dp, "zone": "mamodo",
               "slot_uid": kan.uid})
    submit(g, {"type": "pass", "player": tp})
    submit(g, {"type": "pass", "player": dp})
    pos_before = g.state.players[dp].pos
    events = submit(g, {"type": "choose", "player": dp, "value": kan.uid})  # 以 M-013 保護
    assert any(e["type"] == "damage_prevented" for e in events)
    assert kan in g.state.players[dp].slots and kan.injured  # 沒被棄掉
    assert g.state.players[dp].pos == pos_before  # 魔本也沒受傷


def test_m013_condition_requires_injured():
    g = game()
    dp = 1 - g.state.turn_player
    kan = give(g, dp, "M-013", injured=False)
    g.state.players[dp].mp = 5
    tp, _ = start_attack(g, 3)
    submit(g, {"type": "no_defense", "player": dp})
    submit(g, {"type": "pass", "player": tp})
    with pytest.raises(IllegalCommand) as exc:
        submit(g, {"type": "use_field_ability", "player": dp, "zone": "mamodo",
                   "slot_uid": kan.uid})
    assert exc.value.code == "ability.condition"


def test_m014_j_version_two_or_more():
    g = game(book0=book(first="M-014"))
    tia = slot0(g, 0)
    assert slot_power(g, 0, tia) == 2000  # 只有 1 隻:不加成(j 版=2隻以上)
    other = give(g, 0, "M-012")
    assert slot_power(g, 0, tia) == 3000
    assert slot_power(g, 0, other) == 2000  # 全體 +1000(凱喬美 1000+1000)


def test_m015_no_damage():
    g = game()
    dp = 1 - g.state.turn_player
    tia = give(g, dp, "M-015")
    g.state.players[dp].mp = 6
    tp, _ = start_attack(g, 3)
    submit(g, {"type": "no_defense", "player": dp})
    submit(g, {"type": "pass", "player": tp})
    submit(g, {"type": "use_field_ability", "player": dp, "zone": "mamodo",
               "slot_uid": tia.uid})
    submit(g, {"type": "pass", "player": tp})
    submit(g, {"type": "pass", "player": dp})
    events = submit(g, {"type": "choose", "player": dp, "value": tia.uid})
    assert any(e["type"] == "damage_prevented" for e in events)
    assert not tia.injured


# ================================================================ 夥伴

def test_p001_attack_undefendable():
    g = game()
    tp = g.state.turn_player
    dp = 1 - tp
    slot0(g, tp).partner = "P-001"
    submit(g, {"type": "flip_pages", "player": tp, "count": 0})
    submit(g, {"type": "use_field_ability", "player": tp, "zone": "partner",
               "slot_uid": slot0(g, tp).uid})
    assert "P-001" in g.state.players[tp].discard
    submit(g, {"type": "pass", "player": dp})
    submit(g, {"type": "declare_attack", "player": tp, "page": 3})
    submit(g, {"type": "battle_in_response", "player": dp, "allow": True})
    assert g.state.battle.attack_undefendable is True
    with pytest.raises(IllegalCommand) as exc:
        submit(g, {"type": "declare_defense", "player": dp, "page": 3})
    assert exc.value.code == "defense.undefendable"


def test_p002_mp_drain():
    g = game()
    tp = g.state.turn_player
    slot0(g, tp).stack = ["M-004"]  # Reycom
    slot0(g, tp).partner = "P-002"
    g.state.players[1 - tp].mp = 2
    submit(g, {"type": "flip_pages", "player": tp, "count": 0})
    mp_before = g.state.players[tp].mp
    submit(g, {"type": "use_field_ability", "player": tp, "zone": "partner",
               "slot_uid": slot0(g, tp).uid})
    assert g.state.players[1 - tp].mp == 0
    assert g.state.players[tp].mp == mp_before + 2  # 只吸到實際減少量


def test_p003_brago_damage_plus2():
    g = game(book0=book(first="M-005", p3="S-008"))
    slot0(g, 0).partner = "P-003"
    tp, dp = start_attack(g, 3)  # S-008 dam2
    submit(g, {"type": "no_defense", "player": dp})
    submit(g, {"type": "use_field_ability", "player": tp, "zone": "partner",
               "slot_uid": slot0(g, tp).uid})
    submit(g, {"type": "pass", "player": dp})
    submit(g, {"type": "pass", "player": tp})
    submit(g, {"type": "choose", "player": dp, "value": None})
    assert g.state.players[dp].pos == 2 + 2 * 4  # 2+2=4
    assert "P-003" in g.state.players[tp].discard


def test_p004_gofure_damage_double():
    g = game(book0=book(first="M-006", p3="S-013"))
    slot0(g, 0).partner = "P-004"
    tp, dp = start_attack(g, 3)  # S-013 dam2
    submit(g, {"type": "no_defense", "player": dp})
    submit(g, {"type": "use_field_ability", "player": tp, "zone": "partner",
               "slot_uid": slot0(g, tp).uid})
    submit(g, {"type": "pass", "player": dp})
    submit(g, {"type": "pass", "player": tp})
    submit(g, {"type": "choose", "player": dp, "value": None})
    assert g.state.players[dp].pos == 2 + 2 * 4  # 2*2=4


def test_p005_sugino_spells_free():
    g = game(book0=book(first="M-008", p3="S-014"))
    slot0(g, 0).partner = "P-005"
    submit(g, {"type": "flip_pages", "player": 0, "count": 0})
    submit(g, {"type": "use_field_ability", "player": 0, "zone": "partner",
               "slot_uid": slot0(g, 0).uid})
    assert spell_cost(g, 0, 3, g.db["S-014"]) == 0


def test_p006_negate_damage_then_discard_transformed():
    g = game()
    dp = 1 - g.state.turn_player
    kolulu = give(g, dp, "M-009")
    kolulu.stack.append("M-010")
    kolulu.partner = "P-006"
    tp, _ = start_attack(g, 3)
    submit(g, {"type": "no_defense", "player": dp})
    submit(g, {"type": "pass", "player": tp})
    submit(g, {"type": "use_field_ability", "player": dp, "zone": "partner",
               "slot_uid": kolulu.uid})
    submit(g, {"type": "pass", "player": tp})
    submit(g, {"type": "pass", "player": dp})
    events = submit(g, {"type": "choose", "player": dp, "value": kolulu.uid})  # 保護
    assert any(e["type"] == "damage_negated" for e in events)
    assert kolulu.top == "M-009"           # 變身後被棄掉
    assert "M-010" in g.state.players[dp].discard
    assert not kolulu.injured               # 傷害被無效


def test_p007_fein_spell_bonus():
    g = game(book0=book(first="M-011", p3="S-018"))
    slot0(g, 0).partner = "P-007"
    g.state.players[0].mp = 5
    submit(g, {"type": "flip_pages", "player": 0, "count": 0})
    submit(g, {"type": "use_field_ability", "player": 0, "zone": "partner",
               "slot_uid": slot0(g, 0).uid})
    submit(g, {"type": "pass", "player": 1})
    submit(g, {"type": "declare_attack", "player": 0, "page": 3})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    submit(g, {"type": "no_defense", "player": 1})
    events = both_pass(g)
    assert showdown_of(events)["attacker_total"] == 3000 + 2000 + 4000


def test_p008_discard_opponent_partner():
    g = game()
    tp = g.state.turn_player
    dp = 1 - tp
    kan = give(g, tp, "M-012")
    kan.partner = "P-008"
    slot0(g, dp).partner = "P-001"
    submit(g, {"type": "flip_pages", "player": tp, "count": 0})
    submit(g, {"type": "use_field_ability", "player": tp, "zone": "partner",
               "slot_uid": kan.uid})
    assert slot0(g, dp).partner is None
    assert "P-001" in g.state.players[dp].discard


def test_p009_negate_attack_spell():
    g = game()
    dp = 1 - g.state.turn_player
    tia = give(g, dp, "M-014")
    tia.partner = "P-009"
    tp, _ = start_attack(g, 3)
    submit(g, {"type": "no_defense", "player": dp})
    submit(g, {"type": "pass", "player": tp})
    submit(g, {"type": "use_field_ability", "player": dp, "zone": "partner",
               "slot_uid": tia.uid})
    submit(g, {"type": "pass", "player": tp})
    events = submit(g, {"type": "pass", "player": dp})
    sd = showdown_of(events)
    assert sd["attack_negated"] is True
    assert sd["winner"] == "defender"
    assert g.state.players[dp].pos == 2  # 無傷害


# ================================================================ 事件

def test_e001_next_turn_power():
    g = game(book0=book(p2="E-001"))
    tp = 0
    submit(g, {"type": "flip_pages", "player": tp, "count": 0})
    submit(g, {"type": "use_book_card", "player": tp, "page": 2})  # 單一魔物自動指定
    s = slot0(g, tp)
    assert slot_power(g, tp, s) == 4000  # 本回合尚未生效
    end_turn(g)
    # 下回合(對手回合)開始階段生效
    submit(g, {"type": "flip_pages", "player": 1, "count": 0})
    assert slot_power(g, tp, s) == 7000
    end_turn(g)
    assert slot_power(g, tp, s) == 4000  # 下回合結束後失效


def test_e002_both_players_no_spells():
    g = game(book0=book(p2="E-002"))
    tp, dp = 0, 1
    g.state.players[tp].mp = 5
    submit(g, {"type": "flip_pages", "player": tp, "count": 0})
    submit(g, {"type": "use_book_card", "player": tp, "page": 2})
    submit(g, {"type": "pass", "player": dp})  # 行動後優先權在對手
    with pytest.raises(IllegalCommand) as exc:
        submit(g, {"type": "declare_attack", "player": tp, "page": 3})
    assert exc.value.code == "spell.restricted"
    submit(g, {"type": "pass", "player": tp})  # 與前一 pass 合計雙 pass → 回合結束
    # 對手回合(下回合)也不能用術
    submit(g, {"type": "flip_pages", "player": dp, "count": 0})
    with pytest.raises(IllegalCommand) as exc:
        submit(g, {"type": "declare_attack", "player": dp, "page": 3})
    assert exc.value.code == "spell.restricted"
    submit(g, {"type": "pass", "player": dp})
    submit(g, {"type": "pass", "player": tp})
    # 再下一回合恢復(tp 魔本已被結束階段強制翻至 pos=4,用翻開中的第 4 頁)
    submit(g, {"type": "flip_pages", "player": tp, "count": 0})
    submit(g, {"type": "declare_attack", "player": tp, "page": 4})
    assert g.state.battle_in is not None


def test_e003_gain_2mp():
    g = game(book0=book(p2="E-003"))
    submit(g, {"type": "flip_pages", "player": 0, "count": 0})
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    assert g.state.players[0].mp == 4


def test_e004_both_mp_to_zero():
    g = game(book0=book(p2="E-004"))
    g.state.players[0].mp = 8
    g.state.players[1].mp = 6
    submit(g, {"type": "flip_pages", "player": 0, "count": 0})
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    assert g.state.players[0].mp == 0  # 費 5 → 3,歸 0
    assert g.state.players[1].mp == 0


def test_e005_two_tails_turn_forward():
    g = game(book0=book(p2="E-005"), coins=(TAILS, TAILS))
    submit(g, {"type": "flip_pages", "player": 0, "count": 0})
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    assert g.state.players[0].pos == 6  # 反反 → 翻 2 張


def test_e005_two_heads_turn_back():
    g = game(book0=book(p2="E-005"), coins=(HEADS, HEADS))
    g.state.players[0].pos = 10
    submit(g, {"type": "flip_pages", "player": 0, "count": 0})
    # pos 10 → 開 10,11 頁;E-005 不在該頁 → 改放頁面
    g.state.players[0].pos = 2
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    assert g.state.players[0].pos == 2  # 已在最前,回翻不低於 2


def test_e006_heads_heals():
    g = game(book0=book(p2="E-006"), coins=(HEADS,))
    slot0(g, 0).injured = True
    submit(g, {"type": "flip_pages", "player": 0, "count": 0})
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    assert slot0(g, 0).injured is False


def test_e006_tails_power():
    g = game(book0=book(p2="E-006"), coins=(TAILS,))
    submit(g, {"type": "flip_pages", "player": 0, "count": 0})
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    assert slot_power(g, 0, slot0(g, 0)) == 5000


def test_e007_j_version_heal_injured_only():
    g = game(book0=book(p2="E-007"))
    submit(g, {"type": "flip_pages", "player": 0, "count": 0})
    # 無負傷魔物 → 不能使用(j 版限定負傷)
    with pytest.raises(IllegalCommand) as exc:
        submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    assert exc.value.code == "event.condition"
    slot0(g, 0).injured = True
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    assert slot0(g, 0).injured is False


def test_e008_partner_effects_disabled():
    g = game(book0=book(p2="E-008"))
    tp, dp = 0, 1
    slot0(g, dp).partner = "P-001"
    submit(g, {"type": "flip_pages", "player": tp, "count": 0})
    submit(g, {"type": "use_book_card", "player": tp, "page": 2})
    with pytest.raises(IllegalCommand) as exc:
        submit(g, {"type": "use_field_ability", "player": dp, "zone": "partner",
                   "slot_uid": slot0(g, dp).uid})
    assert exc.value.code == "ability.partner_restricted"


def test_e009_power_this_turn():
    g = game(book0=book(p2="E-009"))
    g.state.players[0].mp = 5
    submit(g, {"type": "flip_pages", "player": 0, "count": 0})
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    assert slot_power(g, 0, slot0(g, 0)) == 7000
    end_turn(g)
    assert slot_power(g, 0, slot0(g, 0)) == 4000


def test_e010_borrow_opponent_partner():
    g = game(book0=book(p2="E-010"))
    tp, dp = 0, 1
    reycom = give(g, dp, "M-004")
    reycom.partner = "P-002"
    g.state.players[tp].mp = 5
    g.state.players[dp].mp = 4
    submit(g, {"type": "flip_pages", "player": tp, "count": 0})
    submit(g, {"type": "use_book_card", "player": tp, "page": 2})  # 借 P-002(唯一→自動)
    submit(g, {"type": "pass", "player": dp})
    mp_before = g.state.players[tp].mp
    submit(g, {"type": "use_field_ability", "player": tp, "zone": "partner",
               "slot_uid": reycom.uid})
    assert g.state.players[dp].mp == 1          # 4-3
    assert g.state.players[tp].mp == mp_before + 3
    assert reycom.partner == "P-002"            # 借用不棄掉
    # 本回合只能用一次
    submit(g, {"type": "pass", "player": dp})
    with pytest.raises(IllegalCommand):
        submit(g, {"type": "use_field_ability", "player": tp, "zone": "partner",
                   "slot_uid": reycom.uid})


def test_e011_reflip_by_paying():
    g = game(book0=book(p2="E-011"), coins=(TAILS, HEADS))
    g.state.players[0].discard.append("P-001")
    g.state.players[0].mp = 5
    submit(g, {"type": "flip_pages", "player": 0, "count": 0})
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    assert g.state.pending.kind == "e011_retry"  # 反面 → 可付費重擲
    submit(g, {"type": "choose", "player": 0, "value": True})
    # 重擲正面 → 唯一目標自動放出
    assert slot0(g, 0).partner == "P-001"
    assert "P-001" not in g.state.players[0].discard
    assert g.state.players[0].mp == 5 - 3 - 2  # 事件費 3 + 重擲費 2


def test_e012_deploy_mamodo_from_any_page():
    g = game()
    tp = g.state.turn_player
    # E-012 不在 level1 牌組;手工放入頁 2
    ps = g.state.players[tp]
    bookpages = list(ps.book)
    bookpages[1] = "E-012"
    ps.book = tuple(bookpages)
    ps.mp = 5
    submit(g, {"type": "flip_pages", "player": tp, "count": 0})
    submit(g, {"type": "use_book_card", "player": tp, "page": 2})
    assert g.state.pending.kind == "e012_pick"  # 第 6 頁 M-014、第 14 頁 M-012
    submit(g, {"type": "choose", "player": tp, "value": 14})
    assert any(s.top == "M-012" for s in ps.slots)
    assert 14 in ps.consumed_pages


def test_e013_no_protect_next_battle():
    g = game(book0=book(p2="E-013", p3="S-001"))
    tp, dp = 0, 1
    submit(g, {"type": "flip_pages", "player": tp, "count": 0})
    submit(g, {"type": "use_book_card", "player": tp, "page": 2})
    submit(g, {"type": "pass", "player": dp})
    submit(g, {"type": "declare_attack", "player": tp, "page": 3})
    submit(g, {"type": "battle_in_response", "player": dp, "allow": True})
    submit(g, {"type": "no_defense", "player": dp})
    submit(g, {"type": "pass", "player": tp})
    events = submit(g, {"type": "pass", "player": dp})
    # 不能保護 → 不會出現保護選擇,直接傷害
    assert g.state.pending is None
    assert any(e["type"] == "damage_dealt" for e in events)
    assert g.state.players[dp].pos == 4


def test_e014_flip_opponent_and_peek():
    g = game(book0=book(p2="E-014"))
    submit(g, {"type": "flip_pages", "player": 0, "count": 0})
    events = submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    assert g.state.players[1].pos == 4
    peek = next(e for e in events if e["type"] == "pages_peeked")
    assert {c["page"] for c in peek["cards"]} == {4, 5}


def test_e015_power_until_end_next_turn():
    g = game(book0=book(p2="E-015"))
    s = slot0(g, 0)
    submit(g, {"type": "flip_pages", "player": 0, "count": 0})
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    assert slot_power(g, 0, s) == 6000
    end_turn(g)
    assert slot_power(g, 0, s) == 6000  # 下回合仍生效
    submit(g, {"type": "flip_pages", "player": 1, "count": 0})
    submit(g, {"type": "pass", "player": 1})
    submit(g, {"type": "pass", "player": 0})
    assert slot_power(g, 0, s) == 4000  # 下回合結束階段後失效


# ================================================================ 術

def test_s003_rashield_counter():
    g = game(book1=book(p2="S-003"))
    tp, dp = 0, 1
    start_attack(g, 3)
    submit(g, {"type": "declare_defense", "player": dp, "page": 2})
    submit(g, {"type": "pass", "player": tp})
    events = submit(g, {"type": "pass", "player": dp})
    sd = showdown_of(events)
    assert sd["defender_total"] == 8000 and sd["winner"] == "defender"
    # 反擊:攻方魔本受 1 點傷害(攻方可保護)
    assert g.state.pending.kind == "protect" and g.state.pending.player == tp
    submit(g, {"type": "choose", "player": tp, "value": None})
    assert g.state.players[tp].pos == 4


@pytest.mark.parametrize("spell,mamodo,coin", [
    ("S-004", "M-001", True),   # ジケルド:擲硬幣正面才鎖
    ("S-014", "M-008", True),   # ジュロン:同上
    ("S-009", "M-005", False),  # グラビレイ:必定鎖
    ("S-011", "M-005", False),  # アイアン・グラビレイ:必定鎖
])
def test_spell_lock_after_damage(spell, mamodo, coin):
    g = game(book0=book(first=mamodo, p3=spell), coins=(HEADS,))
    g.state.players[0].mp = 10
    tp, dp = start_attack(g, 3)
    submit(g, {"type": "no_defense", "player": dp})
    submit(g, {"type": "pass", "player": tp})
    submit(g, {"type": "pass", "player": dp})
    submit(g, {"type": "choose", "player": dp, "value": None})  # 不保護
    # 對手下回合不能使用術卡(重置 pos 使第 3 頁 S-001 翻開,以隔離傷害翻頁的影響)
    end_turn(g)
    g.state.players[dp].pos = 2
    submit(g, {"type": "flip_pages", "player": dp, "count": 0})
    with pytest.raises(IllegalCommand) as exc:
        submit(g, {"type": "declare_attack", "player": dp, "page": 3})
    assert exc.value.code == "spell.restricted"


def test_s007_partner_lock_after_damage():
    g = game(book0=book(first="M-004", p3="S-007"))
    g.state.players[0].mp = 10
    tp, dp = start_attack(g, 3)
    slot0(g, dp).partner = "P-001"
    submit(g, {"type": "no_defense", "player": dp})
    submit(g, {"type": "pass", "player": tp})
    submit(g, {"type": "pass", "player": dp})
    submit(g, {"type": "choose", "player": dp, "value": None})
    end_turn(g)
    submit(g, {"type": "flip_pages", "player": dp, "count": 0})
    with pytest.raises(IllegalCommand) as exc:
        submit(g, {"type": "use_field_ability", "player": dp, "zone": "partner",
                   "slot_uid": slot0(g, dp).uid})
    assert exc.value.code == "ability.partner_restricted"


def test_s017_attack_bonus():
    g = game(book0=book(first="M-009", p2="S-017"))
    g.state.players[0].mp = 5
    tp, dp = start_attack(g, 2)
    submit(g, {"type": "no_defense", "player": dp})
    events = both_pass(g)
    sd = showdown_of(events)
    assert sd["attacker_total"] == 1000 + 3000 + 2000  # 可露露+術+攻擊加值 = 6000
    assert sd["winner"] == "attacker"


def test_s017_no_bonus_on_defense():
    g = game(book1=book(p2="S-017"))
    dp = 1
    give(g, dp, "M-009")
    g.state.players[dp].mp = 5
    tp, _ = start_attack(g, 3)
    submit(g, {"type": "declare_defense", "player": dp, "page": 2})
    submit(g, {"type": "pass", "player": tp})
    events = submit(g, {"type": "pass", "player": dp})
    sd = showdown_of(events)
    assert sd["defender_total"] == 1000 + 3000  # 可露露+術,防禦時不再加值 = 4000


def test_s019_next_attack_undefendable():
    g = game(book0=book(first="M-011", p2="S-019", p3="S-018"))
    g.state.players[0].mp = 10
    tp, dp = start_attack(g, 2)  # S-019 dam0
    submit(g, {"type": "no_defense", "player": dp})
    pos_before = g.state.players[dp].pos
    both_pass(g)
    assert g.state.players[dp].pos == pos_before  # 無魔本傷害
    # 本回合下一次攻擊不可被防禦(j 版:下一次「攻擊」)
    submit(g, {"type": "declare_attack", "player": tp, "page": 3})
    submit(g, {"type": "battle_in_response", "player": dp, "allow": True})
    assert g.state.battle.attack_undefendable is True


def test_s020_mp_drain_on_win():
    g = game(book0=book(first="M-012", p3="S-020"))
    tp, dp = start_attack(g, 3)
    g.state.players[dp].mp = 5
    submit(g, {"type": "no_defense", "player": dp})
    events = both_pass(g)
    assert showdown_of(events)["winner"] == "attacker"
    assert g.state.players[dp].mp == 2  # -3
    assert g.state.players[dp].pos == 2  # 無魔本傷害
    assert g.state.battle is None


def test_s021_coin_negate_two_flips():
    g = game(book1=book(first="M-012", p2="S-021"), coins=(TAILS, HEADS))
    tp, dp = start_attack(g, 3)
    g.state.players[dp].mp = 5
    events = submit(g, {"type": "declare_defense", "player": dp, "page": 2})
    assert len([e for e in events if e["type"] == "coin_flipped"]) == 2
    # 防方場上有 M-012 → 詢問是否重擲;保留原結果
    assert g.state.pending.kind == "coin_confirm"
    submit(g, {"type": "choose", "player": dp, "value": None})
    assert g.state.battle.attack_negated is True  # 至少一次正面
    submit(g, {"type": "pass", "player": tp})
    events = submit(g, {"type": "pass", "player": dp})
    assert showdown_of(events)["winner"] == "defender"


def test_s026_set_then_undefendable():
    g = game(book0=book(p2="S-026", p3="S-001"), coins=(HEADS,))
    tp = g.state.turn_player
    dp = 1 - tp
    submit(g, {"type": "flip_pages", "player": tp, "count": 0})
    submit(g, {"type": "use_book_card", "player": tp, "page": 2})  # S-026(非戰鬥術)
    submit(g, {"type": "pass", "player": dp})
    submit(g, {"type": "declare_attack", "player": tp, "page": 3})
    submit(g, {"type": "battle_in_response", "player": dp, "allow": True})
    assert g.state.battle.attack_undefendable is True


def test_s026_cannot_declare_attack():
    g = game(book0=book(p2="S-026"))
    tp = g.state.turn_player
    submit(g, {"type": "flip_pages", "player": tp, "count": 0})
    with pytest.raises(IllegalCommand) as e:
        submit(g, {"type": "declare_attack", "player": tp, "page": 2})
    assert e.value.code == "spell.no_attack_icon"


def test_s027_damage_reduction():
    g = game(book0=book(p3="S-002"), book1=book(p2="S-027"), coins=(TAILS, HEADS))
    tp, dp = start_attack(g, 3)  # S-002 dam2, cost2 → mp 0
    submit(g, {"type": "declare_defense", "player": dp, "page": 2})  # S-027 費 0
    submit(g, {"type": "pass", "player": tp})
    submit(g, {"type": "pass", "player": dp})
    submit(g, {"type": "choose", "player": dp, "value": None})
    assert g.state.players[dp].pos == 2 + 2 * 1  # 2-1=1


def test_last_page_bao_zakeruga_free():
    g = game()
    tp = g.state.turn_player
    g.state.players[tp].pos = 32
    submit(g, {"type": "flip_pages", "player": tp, "count": 0})
    assert spell_cost(g, tp, 32, g.db["S-005"]) == 0
    submit(g, {"type": "declare_attack", "player": tp, "page": 32})
    submit(g, {"type": "battle_in_response", "player": 1 - tp, "allow": True})
    assert g.state.players[tp].mp == 2  # 沒扣
