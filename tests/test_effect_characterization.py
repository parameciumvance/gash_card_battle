"""遷移前特徵測試:固定擲幣確認鏈(M-012 / M-019)、三種擲幣入口與 E-001 的現行行為。

效果樹遷移(effect-tree-interpreter)前後這些測試都必須通過。全部經 submit() 走引擎入口,
逐步斷言 pending 的 kind / 決策者、能力消耗、事件序列與 RNG 呼叫次數。
"""

import pytest

from gash.engine.engine import IllegalCommand, slot_power, submit

from .test_cards import HEADS, TAILS, book, end_turn, game, give, slot0, start_attack

TRACED = {"coin_flipped", "choice_required", "ability_used", "attack_negated",
          "modifier_added", "standby_set", "standby_resolved"}


class StrictRng:
    """腳本化 RNG:序列用完再呼叫即拋錯(抓額外的 RNG 消耗),並記錄呼叫次數。"""

    def __init__(self, *seq):
        self.seq = list(seq)
        self.calls = 0

    def random(self):
        self.calls += 1
        if not self.seq:
            raise AssertionError("RNG 被超額呼叫")
        return self.seq.pop(0)

    def randint(self, a, b):
        return a


def strict_game(*coins, **kw):
    g = game(**kw)
    g.rng = StrictRng(*coins)
    return g


def kinds(events):
    return [(e["type"], e.get("result", e.get("kind"))) for e in events if e["type"] in TRACED]


def pending(g):
    p = g.state.pending
    return None if p is None else (p.kind, p.player, [o["value"] for o in p.options])


# ================================================================ M-019 / M-012 確認鏈

def defend_with_s025(g):
    """攻方 tp 攻擊,防方 dp 以 S-025 防禦(擲 1 枚硬幣)。回傳 (tp, dp, events)。"""
    tp, dp = start_attack(g, 3)
    events = submit(g, {"type": "declare_defense", "player": dp, "page": 2,
                        "slot_uid": slot0(g, dp).uid})
    return tp, dp, events


def test_m019_keep_result():
    g = strict_game(TAILS, book0=None, book1=book(p2="S-025"))
    give(g, 0, "M-019")
    tp, dp, events = defend_with_s025(g)
    assert kinds(events) == [("coin_flipped", "tails"), ("choice_required", "opp_coin_redo")]
    assert pending(g) == ("opp_coin_redo", tp, [None, True])  # 決策者是對手(攻方)
    events = submit(g, {"type": "choose", "player": tp, "value": None})
    assert g.state.battle.attack_negated is False  # 保留反面
    assert "mamodo:M-019" not in g.state.players[tp].used_abilities
    assert g.rng.calls == 1
    assert kinds(events) == []


def test_m019_pay_reflip():
    g = strict_game(TAILS, HEADS, book1=book(p2="S-025"))
    give(g, 0, "M-019")
    tp, dp, _ = defend_with_s025(g)
    events = submit(g, {"type": "choose", "player": tp, "value": True})
    assert kinds(events) == [("ability_used", None), ("coin_flipped", "heads"),
                             ("attack_negated", None)]
    assert g.state.battle.attack_negated is True
    assert "mamodo:M-019" in g.state.players[tp].used_abilities
    assert g.state.pending is None
    assert g.rng.calls == 2


def test_m019_then_m012_chain():
    g = strict_game(TAILS, HEADS, TAILS, book1=book(p2="S-025"))
    give(g, 0, "M-019")
    give(g, 1, "M-012")
    tp, dp, events = defend_with_s025(g)
    assert pending(g) == ("opp_coin_redo", tp, [None, True])
    # 對手令整組重擲(反面 → 正面),接著輪到防方的 M-012 確認
    events = submit(g, {"type": "choose", "player": tp, "value": True})
    assert kinds(events) == [("ability_used", None), ("coin_flipped", "heads"),
                             ("choice_required", "coin_confirm")]
    assert pending(g) == ("coin_confirm", dp, [None, 0])
    assert g.state.battle.attack_negated is False  # 尚未確定
    # 防方以 M-012 重擲(正面 → 反面)
    events = submit(g, {"type": "choose", "player": dp, "value": 0})
    assert kinds(events) == [("ability_used", None), ("coin_flipped", "tails")]
    assert g.state.battle.attack_negated is False
    assert {"mamodo:M-019"} <= g.state.players[tp].used_abilities
    assert {"mamodo:M-012"} <= g.state.players[dp].used_abilities
    assert g.state.pending is None
    assert g.rng.calls == 3


def test_m012_confirm_rejects_invalid_and_keeps_pending():
    g = strict_game(TAILS, book1=book(p2="S-025"))
    give(g, 1, "M-012")
    tp, dp, _ = defend_with_s025(g)
    with pytest.raises(IllegalCommand) as exc:
        submit(g, {"type": "choose", "player": dp, "value": 5})
    assert exc.value.code == "choose.invalid"
    assert pending(g) == ("coin_confirm", dp, [None, 0])
    submit(g, {"type": "choose", "player": dp, "value": None})
    assert g.state.pending is None
    assert g.rng.calls == 1


# ================================================================ 入口 1:傷害後擲幣(S-004 / S-014)

def _s004_until_damage(g):
    g.state.players[0].mp = 10
    tp, dp = start_attack(g, 3, slot_uid=slot0(g, 0).uid)
    submit(g, {"type": "no_defense", "player": dp})
    submit(g, {"type": "pass", "player": tp})
    submit(g, {"type": "pass", "player": dp})
    return tp, dp


def _assert_spells_locked(g, tp, dp):
    end_turn(g)
    g.state.players[dp].pos = 2
    submit(g, {"type": "flip_pages", "player": dp, "count": 0})
    with pytest.raises(IllegalCommand) as exc:
        submit(g, {"type": "declare_attack", "player": dp, "page": 3})
    assert exc.value.code == "spell.restricted"


@pytest.mark.parametrize("spell,mamodo", [("S-004", "M-001"), ("S-014", "M-008")])
def test_damage_coin_no_confirm_heads_locks(spell, mamodo):
    g = strict_game(HEADS, book0=book(first=mamodo, p3=spell))
    tp, dp = _s004_until_damage(g)
    events = submit(g, {"type": "choose", "player": dp, "value": None})  # 不保護
    assert kinds(events) == [("coin_flipped", "heads"), ("modifier_added", "restriction")]
    assert pending(g) is None
    assert g.rng.calls == 1
    _assert_spells_locked(g, tp, dp)


def test_damage_coin_no_confirm_tails_does_not_lock():
    g = strict_game(TAILS, book0=book(first="M-001", p3="S-004"))
    tp, dp = _s004_until_damage(g)
    events = submit(g, {"type": "choose", "player": dp, "value": None})
    assert kinds(events) == [("coin_flipped", "tails")]
    assert g.rng.calls == 1
    end_turn(g)
    g.state.players[dp].pos = 2
    submit(g, {"type": "flip_pages", "player": dp, "count": 0})
    submit(g, {"type": "declare_attack", "player": dp, "page": 3})  # 未被鎖,可宣告


def test_damage_coin_with_m012_confirm_keep():
    g = strict_game(HEADS, book0=book(first="M-001", p3="S-004"))
    give(g, 0, "M-012")
    tp, dp = _s004_until_damage(g)
    events = submit(g, {"type": "choose", "player": dp, "value": None})
    assert kinds(events) == [("coin_flipped", "heads"), ("choice_required", "coin_confirm")]
    assert pending(g) == ("coin_confirm", tp, [None, 0])
    submit(g, {"type": "choose", "player": tp, "value": None})
    assert pending(g) is None
    assert g.rng.calls == 1
    _assert_spells_locked(g, tp, dp)


def test_damage_coin_with_m012_confirm_reflip_to_tails():
    g = strict_game(HEADS, TAILS, book0=book(first="M-001", p3="S-004"))
    give(g, 0, "M-012")
    tp, dp = _s004_until_damage(g)
    submit(g, {"type": "choose", "player": dp, "value": None})
    events = submit(g, {"type": "choose", "player": tp, "value": 0})
    assert kinds(events) == [("ability_used", None), ("coin_flipped", "tails")]
    assert pending(g) is None
    assert g.rng.calls == 2
    end_turn(g)
    g.state.players[dp].pos = 2
    submit(g, {"type": "flip_pages", "player": dp, "count": 0})
    submit(g, {"type": "declare_attack", "player": dp, "page": 3})  # 重擲成反面 → 未鎖


# ================================================================ 入口 2:宣告時擲幣(S-021 / S-025)

@pytest.mark.parametrize("coins,negated", [
    ((HEADS, HEADS), True), ((HEADS, TAILS), True), ((TAILS, HEADS), True),
    ((TAILS, TAILS), False),
])
def test_s021_two_coin_branches(coins, negated):
    g = strict_game(*coins, book1=book(first="M-013", p2="S-021"))
    tp, dp = start_attack(g, 3)
    g.state.players[dp].mp = 5
    events = submit(g, {"type": "declare_defense", "player": dp, "page": 2})
    assert len([e for e in events if e["type"] == "coin_flipped"]) == 2
    assert pending(g) is None
    assert g.state.battle.attack_negated is negated
    assert g.rng.calls == 2


def test_s021_with_m012_reflip_changes_branch():
    g = strict_game(TAILS, TAILS, HEADS, book1=book(first="M-012", p2="S-021"))
    tp, dp = start_attack(g, 3)
    g.state.players[dp].mp = 5
    submit(g, {"type": "declare_defense", "player": dp, "page": 2})
    assert pending(g) == ("coin_confirm", dp, [None, 0, 1])
    events = submit(g, {"type": "choose", "player": dp, "value": 1})
    assert kinds(events)[:2] == [("ability_used", None), ("coin_flipped", "heads")]
    assert g.state.battle.attack_negated is True
    assert g.rng.calls == 3


@pytest.mark.parametrize("coin,negated", [(HEADS, True), (TAILS, False)])
def test_s025_single_coin_branches(coin, negated):
    g = strict_game(coin, book1=book(p2="S-025"))
    tp, dp = start_attack(g, 3)
    events = submit(g, {"type": "declare_defense", "player": dp, "page": 2,
                        "slot_uid": slot0(g, dp).uid})
    assert len([e for e in events if e["type"] == "coin_flipped"]) == 1
    assert g.state.battle.attack_negated is negated
    assert g.rng.calls == 1


# ================================================================ 入口 3:非戰鬥戰術擲幣(S-026)

def _s026_use(g):
    tp = g.state.turn_player
    dp = 1 - tp
    submit(g, {"type": "flip_pages", "player": tp, "count": 0})
    events = submit(g, {"type": "use_book_card", "player": tp, "page": 2})
    return tp, dp, events


def _s026_attack_undefendable(g, tp, dp):
    submit(g, {"type": "pass", "player": dp})
    submit(g, {"type": "declare_attack", "player": tp, "page": 3})
    submit(g, {"type": "battle_in_response", "player": dp, "allow": True})
    return g.state.battle.attack_undefendable


def test_s026_no_confirm_heads_sets_standby():
    g = strict_game(HEADS, book0=book(p2="S-026", p3="S-001"))
    tp, dp, events = _s026_use(g)
    assert kinds(events) == [("coin_flipped", "heads"), ("standby_set", "attack_undefendable")]
    assert g.rng.calls == 1
    assert _s026_attack_undefendable(g, tp, dp) is True


def test_s026_no_confirm_tails_no_standby():
    g = strict_game(TAILS, book0=book(p2="S-026", p3="S-001"))
    tp, dp, events = _s026_use(g)
    assert kinds(events) == [("coin_flipped", "tails")]
    assert g.rng.calls == 1
    assert _s026_attack_undefendable(g, tp, dp) is False


def test_s026_with_m012_confirm_reflip_to_heads():
    g = strict_game(TAILS, HEADS, book0=book(p2="S-026", p3="S-001"))
    give(g, 0, "M-012")
    tp, dp, events = _s026_use(g)
    assert kinds(events) == [("coin_flipped", "tails"), ("choice_required", "coin_confirm")]
    assert pending(g) == ("coin_confirm", tp, [None, 0])
    events = submit(g, {"type": "choose", "player": tp, "value": 0})
    assert kinds(events) == [("ability_used", None), ("coin_flipped", "heads"),
                             ("standby_set", "attack_undefendable")]
    assert g.rng.calls == 2
    assert _s026_attack_undefendable(g, tp, dp) is True


def test_s026_with_m019_opponent_redo():
    g = strict_game(HEADS, TAILS, book0=book(p2="S-026", p3="S-001"))
    give(g, 1, "M-019")
    tp, dp, events = _s026_use(g)
    assert pending(g) == ("opp_coin_redo", dp, [None, True])
    events = submit(g, {"type": "choose", "player": dp, "value": True})
    assert [k for k in kinds(events)] == [("ability_used", None), ("coin_flipped", "tails")]
    assert g.rng.calls == 2
    assert _s026_attack_undefendable(g, tp, dp) is False


# ================================================================ E-001

def _e001_use(g, uid=None):
    tp = g.state.turn_player
    submit(g, {"type": "flip_pages", "player": tp, "count": 0})
    return tp, submit(g, {"type": "use_book_card", "player": tp, "page": 2})


def test_e001_multi_slot_choose_and_retry():
    g = strict_game(book0=book(p2="E-001"))
    a = slot0(g, 0)
    b = give(g, 0, "M-002")
    tp, events = _e001_use(g)
    assert pending(g) == ("pick_own_mamodo", 0, [a.uid, b.uid])
    with pytest.raises(IllegalCommand) as exc:
        submit(g, {"type": "choose", "player": 0, "value": 9999})
    assert exc.value.code == "choose.invalid"
    assert pending(g) == ("pick_own_mamodo", 0, [a.uid, b.uid])  # 保留,可重選
    events = submit(g, {"type": "choose", "player": 0, "value": b.uid})
    assert kinds(events) == [("standby_set", "start_phase")]
    assert pending(g) is None
    base_a, base_b = slot_power(g, 0, a), slot_power(g, 0, b)
    end_turn(g)
    events = submit(g, {"type": "flip_pages", "player": 1, "count": 0})
    assert ("modifier_added", "power") in kinds(events)
    assert slot_power(g, 0, b) == base_b + 3000
    assert slot_power(g, 0, a) == base_a  # 只加在選定的魔物


def test_e001_target_gone_no_effect_no_event():
    g = strict_game(book0=book(p2="E-001"))
    a = slot0(g, 0)
    b = give(g, 0, "M-002")
    base_a = slot_power(g, 0, a)
    _e001_use(g)
    submit(g, {"type": "choose", "player": 0, "value": b.uid})
    g.state.players[0].slots.remove(b)  # 目標於待命期間離場
    end_turn(g)
    events = submit(g, {"type": "flip_pages", "player": 1, "count": 0})
    assert not [e for e in events if e["type"] == "modifier_added"]
    assert not [m for m in g.state.modifiers if m.source == "E-001"]
    assert slot_power(g, 0, a) == base_a  # 未改選另一隻


def test_e001_two_uses_target_different_slots():
    """事件卡每回合限 1 張,故兩筆待命於不同回合建立,各自只影響自己選定的魔物。"""
    g = strict_game(book0=book(p2="E-001", p3="E-001"))
    a = slot0(g, 0)
    b = give(g, 0, "M-002")
    base_a, base_b = slot_power(g, 0, a), slot_power(g, 0, b)
    submit(g, {"type": "flip_pages", "player": 0, "count": 0})
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    submit(g, {"type": "choose", "player": 0, "value": a.uid})
    end_turn(g)
    submit(g, {"type": "flip_pages", "player": 1, "count": 0})  # 第一筆觸發
    assert slot_power(g, 0, a) == base_a + 3000
    assert slot_power(g, 0, b) == base_b
    end_turn(g)  # 結束玩家 1 的回合
    submit(g, {"type": "flip_pages", "player": 0, "count": 0})
    g.state.players[0].pos = 2  # 使第 2、3 頁再度翻開(第 2 頁的 E-001 已用過,改用第 3 頁)
    submit(g, {"type": "use_book_card", "player": 0, "page": 3})
    submit(g, {"type": "choose", "player": 0, "value": b.uid})
    assert slot_power(g, 0, a) == base_a and slot_power(g, 0, b) == base_b
    end_turn(g)
    submit(g, {"type": "flip_pages", "player": 1, "count": 0})  # 第二筆觸發
    assert slot_power(g, 0, b) == base_b + 3000
    assert slot_power(g, 0, a) == base_a


# ================================================================ E-011 / E-018 / E-027(遷移前固定行為)

def _e011_game(*coins, mp=10, discard=("P-001",)):
    g = strict_game(*coins, book0=book(p2="E-011"))
    g.state.players[0].mp = mp
    g.state.players[0].discard.extend(discard)
    submit(g, {"type": "flip_pages", "player": 0, "count": 0})
    return g


def test_e011_heads_attaches_partner_from_discard():
    g = _e011_game(HEADS)
    events = submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    assert slot0(g, 0).partner == "P-001" and "P-001" not in g.state.players[0].discard
    assert [e for e in events if e["type"] == "card_played" and e.get("from_discard")]
    assert g.state.players[0].mp == 10 - 3 and g.rng.calls == 1


def test_e011_tails_offer_retry_and_stop():
    g = _e011_game(TAILS)
    events = submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    assert pending(g) == ("paid_reflip", 0, [True, False])
    req = [e for e in events if e["type"] == "choice_required"][-1]
    assert (req["kind"], req["player"]) == ("paid_reflip", 0) and "options" not in req
    submit(g, {"type": "choose", "player": 0, "value": False})
    assert g.state.pending is None and slot0(g, 0).partner is None
    assert g.state.players[0].mp == 10 - 3 and g.rng.calls == 1


def test_e011_tails_without_mp_for_retry_just_ends():
    g = _e011_game(TAILS, mp=4)                 # 付完費用剩 1 MP,不足以重擲
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    assert g.state.pending is None and slot0(g, 0).partner is None
    assert g.state.players[0].mp == 1 and g.rng.calls == 1


def test_e011_retry_twice_then_heads():
    g = _e011_game(TAILS, TAILS, HEADS)
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    submit(g, {"type": "choose", "player": 0, "value": True})
    assert pending(g) == ("paid_reflip", 0, [True, False])
    submit(g, {"type": "choose", "player": 0, "value": True})
    assert slot0(g, 0).partner == "P-001"
    assert g.state.players[0].mp == 10 - 3 - 2 - 2 and g.rng.calls == 3


def test_e011_m012_confirm_comes_before_retry_offer():
    g = _e011_game(TAILS)
    give(g, 0, "M-012")
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    assert pending(g) == ("coin_confirm", 0, [None, 0])
    submit(g, {"type": "choose", "player": 0, "value": None})       # 保留反面
    assert pending(g) == ("paid_reflip", 0, [True, False])
    assert g.rng.calls == 1


def test_e011_multiple_targets_pick():
    g = _e011_game(HEADS, discard=("P-001", "P-002"))
    reycom = give(g, 0, "M-004")
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    assert g.state.pending.kind == "pick_partner_in_discard"
    assert [(o["card"], o["slot_uid"]) for o in g.state.pending.options] == [
        ("P-001", slot0(g, 0).uid), ("P-002", reycom.uid)]
    with pytest.raises(IllegalCommand):
        submit(g, {"type": "choose", "player": 0, "value": 7})
    submit(g, {"type": "choose", "player": 0, "value": 1})
    assert reycom.partner == "P-002" and slot0(g, 0).partner is None


def test_e011_same_name_partner_on_field_is_not_a_target():
    g = strict_game(book0=book(p2="E-011"))
    g.state.players[0].mp = 10
    give(g, 0, "M-016", partner="P-001")         # 場上已有「高嶺清麿」
    g.state.players[0].discard.append("P-010")   # 同名「高嶺清麿」→ 不是目標
    submit(g, {"type": "flip_pages", "player": 0, "count": 0})
    with pytest.raises(IllegalCommand):
        submit(g, {"type": "use_book_card", "player": 0, "page": 2})


def _e018_second_use(turns_later):
    from .test_level2 import book as lbook, mk, to_battle
    g, _ = mk(lbook("M-001", "E-018", "E-018"), lbook("M-001"))
    st = g.state
    st.players[0].mp, st.players[1].mp = 10, 20
    to_battle(g, 0)
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    for _ in range(turns_later):
        submit(g, {"type": "pass", "player": st.action_player})
        submit(g, {"type": "pass", "player": st.action_player})
        submit(g, {"type": "flip_pages", "player": st.turn_player, "count": 0})
    if st.action_player != 0:
        submit(g, {"type": "pass", "player": st.action_player})
    st.players[0].pos = 3                         # 翻開第 3 頁的第二張 E-018
    before = st.players[1].mp
    events = submit(g, {"type": "use_book_card", "player": 0, "page": 3})
    return g, before, events


def test_e018_zero_when_reduced_opponent_mp_in_previous_turn():
    g, before, events = _e018_second_use(turns_later=1)   # 對手回合 = 直前回合剛減過
    assert g.state.players[1].mp == before
    applied = [e for e in events if e["type"] == "effect_applied"]
    assert len(applied) == 1
    assert (applied[0]["source"], applied[0]["skipped"]) == ("E-018", True)


def test_e018_reduces_again_when_previous_turn_had_no_reduction():
    g, before, _ = _e018_second_use(turns_later=2)        # 直前回合(對手回合)沒減過
    assert g.state.players[1].mp == before - 4


def test_e027_opponent_chooses_partner_to_keep_then_self_fetches():
    # 效果文:相手は…パートナーカードを1枚残してすべて選び、捨て札にする(由對手選擇保留哪張)
    g = strict_game(book0=book(p2="E-027", p9="P-001"))
    g.state.players[0].mp = 10
    opp_a = slot0(g, 1)
    opp_a.partner = "P-001"
    opp_b = give(g, 1, "M-004", partner="P-002")
    submit(g, {"type": "flip_pages", "player": 0, "count": 0})
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    assert pending(g) == ("pick_partner_to_keep", 1, [opp_a.uid, opp_b.uid])   # 決策者是對手
    assert [o["card"] for o in g.state.pending.options] == ["P-001", "P-002"]
    assert slot0(g, 0).partner is None                               # 自己這側尚未處理
    with pytest.raises(IllegalCommand):
        submit(g, {"type": "choose", "player": 1, "value": slot0(g, 0).uid})
    events = submit(g, {"type": "choose", "player": 1, "value": opp_b.uid})   # 保留第 2 張
    assert opp_a.partner is None and opp_b.partner == "P-002"
    assert "P-001" in g.state.players[1].discard
    assert slot0(g, 0).partner == "P-001" and 9 in g.state.players[0].consumed_pages
    order = [(e["type"], e["player"]) for e in events
             if e["type"] in ("card_discarded", "card_played") and e.get("zone") == "partner"]
    assert order == [("card_discarded", 1), ("card_played", 0)]      # 先對手後自己


def test_e027_self_chooses_page_then_mamodo():
    # 自己沒有搭檔:自己選魔書哪一頁的搭檔,可裝的魔物有多隻時再選裝到哪一隻
    g = strict_game(book0=book(p2="E-027", p9="P-001", p10="P-010"), book1=book())
    g.state.players[0].mp = 10
    gash = slot0(g, 0)
    gash2 = give(g, 0, "M-016")
    submit(g, {"type": "flip_pages", "player": 0, "count": 0})
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    assert pending(g) == ("pick_partner_in_own_book", 0, [9, 10])
    submit(g, {"type": "choose", "player": 0, "value": 10})
    assert pending(g) == ("pick_mamodo_for_partner", 0, [gash.uid, gash2.uid])
    submit(g, {"type": "choose", "player": 0, "value": gash2.uid})
    assert gash2.partner == "P-010" and gash.partner is None
    assert 10 in g.state.players[0].consumed_pages and 9 not in g.state.players[0].consumed_pages


def test_e027_single_partner_kept_without_asking():
    g = strict_game(book0=book(p2="E-027"), book1=book())
    g.state.players[0].mp = 10
    slot0(g, 0).partner = "P-001"
    slot0(g, 1).partner = "P-001"
    submit(g, {"type": "flip_pages", "player": 0, "count": 0})
    events = submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    assert g.state.pending is None
    assert slot0(g, 0).partner == "P-001" and slot0(g, 1).partner == "P-001"
    assert not [e for e in events if e["type"] == "card_discarded"]


def test_e027_side_without_partner_and_none_in_book_does_nothing():
    g = strict_game(book0=book(p2="E-027"), book1=book())   # 對手魔書沒有搭檔卡
    g.state.players[0].mp = 10
    slot0(g, 0).partner = "P-001"
    submit(g, {"type": "flip_pages", "player": 0, "count": 0})
    events = submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    assert slot0(g, 1).partner is None and slot0(g, 0).partner == "P-001"
    assert not [e for e in events if e.get("zone") == "partner"]
