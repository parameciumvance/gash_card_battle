"""第 4 賽季事件卡第 b 批(card-effects「第 4 賽季事件卡第 b 批」「取除提升魔力的效果」、game-engine
「戰鬥中使用魔書的事件卡」「效果編號」,season4-events-b)。依日文效果文。
"""
import pytest

from gash.engine.cards import pending_cards
from gash.engine.effects import registry as reg
from gash.engine.engine import power_breakdown, submit
from tests.test_level2 import DB, HEADS, Rng, book, mk, to_battle
from tests.test_level3 import add_slot, choose, code, pass_effects

BATCH = ("E-053", "Ex-070")


def test_batch_open():
    assert not set(BATCH) & pending_cards()


# ---------------------------------------------------------------- E-053

def _e053(p1=("M-001", "E-053"), p0=("M-001", "S-001"), mp=10):
    """玩家 0 以 S-001 攻擊,玩家 1 不防禦;停在「効果の使用」攻方先(玩家 0)。"""
    g, _ = mk(book(*p0), book(*p1))
    st = g.state
    st.players[0].mp = st.players[1].mp = mp
    to_battle(g, 0)
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    submit(g, {"type": "no_defense", "player": 1})
    submit(g, {"type": "pass", "player": 0})
    assert st.battle.data["effect_turn"] == 1
    return g


def use_e053(g, page=2):
    return submit(g, {"type": "use_book_card", "player": 1, "page": page})


def test_e053_damages_own_mamodo_and_negates_attack():
    # 自分の場の魔物1体を選び、ダメージをあたえる。…このバトルの、相手の攻撃1つを無効にする
    g = _e053()
    st = g.state
    a = st.players[1].slots[0]
    pos = st.players[1].pos
    use_e053(g)                                                           # 只有 1 隻:自動選
    assert a.injured
    assert st.battle.attack_negated
    assert st.pending is None and st.battle.data["effect_turn"] == 0       # 換對方使用效果
    pass_effects(g)
    assert st.battle is None and st.players[1].pos == pos                  # 魔書沒有受到攻擊的傷害


def test_e053_damage_can_be_protected():
    # 一般的傷害流程:自己其他魔物可以保護;攻擊照樣無效
    g = _e053()
    st = g.state
    a = st.players[1].slots[0]
    b = add_slot(g, 1, "M-017")
    use_e053(g)
    assert st.pending.kind == "pick_own_mamodo" and st.pending.player == 1
    choose(g, a.uid)
    assert st.pending.kind == "protect" and st.pending.player == 1
    assert b.uid in [o["value"] for o in st.pending.options]
    choose(g, b.uid)
    assert b.injured and not a.injured
    assert st.battle.attack_negated


def test_e053_negates_even_without_damage():
    # ダメージがあたえられたかどうかにかかわらず
    g = _e053()
    st = g.state
    a = st.players[1].slots[0]
    a.stack = ["M-051"]                                                   # 不受傷害
    use_e053(g)
    assert not a.injured
    assert st.battle.attack_negated


def test_e053_rejected_outside_battle():
    # バトル:非バトル中には使えない
    g, _ = mk(book("M-001", "S-001"), book("M-001", "E-053"))
    st = g.state
    to_battle(g, 0)
    submit(g, {"type": "pass", "player": 0})
    assert st.action_player == 1 and st.battle is None
    assert code(g, {"type": "use_book_card", "player": 1, "page": 2}) == "event.timing"


def test_e053_rejected_as_battle_in_insert():
    g, _ = mk(book("M-001", "S-001"), book("M-001", "E-053"))
    st = g.state
    st.players[0].mp = 10
    to_battle(g, 0)
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    assert code(g, {"type": "use_book_card", "player": 1, "page": 2}) == "event.timing"
    assert st.battle_in is not None                                       # 進入戰鬥確認仍在等待


def test_e053_attacker_cannot_use():
    # D 欄:只有非回合玩家能用
    g, _ = mk(book("M-001", "S-001", "E-053"), book("M-001"))
    st = g.state
    st.players[0].mp = 10
    to_battle(g, 0)
    st.players[0].pos = 2                                                 # 翻開 2、3 頁
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    submit(g, {"type": "no_defense", "player": 1})
    assert code(g, {"type": "use_book_card", "player": 0, "page": 3}) == "event.timing"


def test_e053_no_own_mamodo_unusable():
    g = _e053()
    g.state.players[1].slots.clear()
    assert code(g, {"type": "use_book_card", "player": 1, "page": 2}) == "event.condition"


def test_e053_event_limit():
    g = _e053()
    g.state.players[1].events_used_this_turn = 1
    assert code(g, {"type": "use_book_card", "player": 1, "page": 2}) == "event.limit"


def test_event_without_battle_icon_rejected_in_battle():
    g = _e053(p1=("M-001", "Ex-023"))
    assert code(g, {"type": "use_book_card", "player": 1, "page": 2}) == "battle.invalid"


@pytest.mark.parametrize("jammer", ["M-032", "Ex-034"])
def test_e053_not_jammable_in_battle(jammer):
    # バトル中には「バトル効果」「バトル防御」「バトル」アイコンが付いた効果しか使えません:干擾不能在戰鬥中用
    g = _e053()
    st = g.state
    if jammer == "M-032":
        add_slot(g, 0, "M-032")
    else:
        add_slot(g, 0, "Ex-027", partner="Ex-034")
    use_e053(g)
    assert st.pending is None and st.battle.attack_negated
    assert st.battle.data["effect_turn"] == 0


def test_jammers_not_available_in_battle():
    # M-026 / M-065 也一樣(game-engine「ジャマー效果」);非戰鬥中照常
    from gash.engine.engine import _jammer_holder
    g = _e053()
    for number in ("M-026", "M-065"):
        add_slot(g, 0, number)
    assert _jammer_holder(g, 0, "mamodo_effect") is None and _jammer_holder(g, 0, "mp_reduced") is None
    g.state.battle = None
    assert _jammer_holder(g, 0, "mamodo_effect") is not None and _jammer_holder(g, 0, "mp_reduced") is not None


# ---------------------------------------------------------------- 效果編號

def _choices(g, choices):
    """依序回答選擇;單一選項時 Choose 自動解決,不會停下。"""
    for c in choices:
        if g.state.pending is not None:
            choose(g, c)


def _apply_event(g, number, player, *choices):
    reg.EVENT[number](g, [], player, None)
    _choices(g, choices)


def _apply_ability(g, number, player, slot, *choices):
    reg.ACTIVATED[number].handler(g, [], player, slot)
    _choices(g, choices)


def _setup(p0_extra=("Ex-070",), mp=10):
    g, _ = mk(book("M-001", *p0_extra), book("M-001"))
    st = g.state
    st.players[0].mp = st.players[1].mp = mp
    to_battle(g, 0)
    return g


def _use_ex070(g):
    st = g.state
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    if st.pending is None and st.action_player == 1:
        submit(g, {"type": "pass", "player": 1})


def test_use_id_shared_within_composite_effect():
    g = _setup()
    st = g.state
    a = st.players[0].slots[0]
    a.stack = ["M-052"]
    _apply_ability(g, "M-052", 0, a)
    ids = {m.use_id for m in st.modifiers if m.source == "M-052"}
    assert len([m for m in st.modifiers if m.source == "M-052"]) == 2 and len(ids) == 1 and None not in ids


def test_use_id_separate_for_bullets():
    g = _setup()
    st = g.state
    a = st.players[0].slots[0]
    _apply_event(g, "Ex-021", 0, a.uid)
    power = next(m for m in st.modifiers if m.source == "Ex-021")
    discard = next(sb for sb in st.standby if sb.source == "Ex-021")
    assert power.use_id is not None and discard.use_id is not None
    assert power.use_id != discard.use_id


# ---------------------------------------------------------------- Ex-070

def power(g, player, slot):
    return power_breakdown(g, player, slot)[0]


def test_ex070_removes_power_ups_of_both_players():
    g = _setup()
    st = g.state
    a, b = st.players[0].slots[0], st.players[1].slots[0]
    base_a, base_b = power(g, 0, a), power(g, 1, b)
    _apply_event(g, "E-009", 0, a.uid)
    _apply_event(g, "Ex-023", 1, b.uid)
    _apply_event(g, "E-023", 0)
    a.partner = "P-001"
    _apply_event(g, "E-048", 1)
    assert power(g, 0, a) > base_a and power(g, 1, b) > base_b
    _use_ex070(g)
    assert power(g, 0, a) == base_a and power(g, 1, b) == base_b
    assert not [m for m in st.modifiers if m.source in ("E-009", "Ex-023", "E-023", "E-048")]


def test_ex070_removes_standby_power_up():
    # E-001:次のターンのスタートフェイズまで【スタンバイ】
    g = _setup()
    st = g.state
    a = st.players[0].slots[0]
    _apply_event(g, "E-001", 0, a.uid)
    assert any(sb.source == "E-001" for sb in st.standby)
    _use_ex070(g)
    assert not any(sb.source == "E-001" for sb in st.standby)


@pytest.mark.parametrize("number, kind", [("PR-006", "spell"), ("S-089", "spell"), ("P-007", "partner")])
def test_ex070_removes_spell_and_total_standbys(number, kind):
    g = _setup()
    st = g.state
    g.rng = Rng(HEADS)
    a = st.players[0].slots[0]
    if kind == "spell":
        reg.SPELL_NONBATTLE[number](g, [], 0, None)
    else:
        a.stack, a.partner = ["M-011"], "P-007"
        _apply_ability(g, "P-007", 0, a)
    assert any(sb.source == number for sb in st.standby)
    _use_ex070(g)
    assert not any(sb.source == number for sb in st.standby)               # PR-006:任意頁待命一起取除


@pytest.mark.parametrize("number", ["M-052", "PR-010", "MJ-002"])
def test_ex070_removes_whole_composite_modifiers(number):
    g = _setup()
    st = g.state
    a = st.players[0].slots[0]
    if number == "M-052":
        a.stack = ["M-052"]
        _apply_ability(g, "M-052", 0, a)                                    # 魔力 +1000 與傷害 +1
    elif number == "PR-010":
        _apply_event(g, "PR-010", 0)                                        # 減費與魔力 +2000
    else:
        _apply_ability(g, "MJ-002", 0, None)
    assert any(m.source == number for m in st.modifiers)
    _use_ex070(g)
    assert not any(m.source == number for m in st.modifiers)


def test_ex070_keeps_reductions_set_values_and_other_effects():
    g = _setup()
    st = g.state
    a, b = st.players[0].slots[0], st.players[1].slots[0]
    c = add_slot(g, 1, "M-017")
    b.stack = ["Ex-002"]
    _apply_ability(g, "Ex-002", 1, b, a.uid)                                # 相手の魔物の魔力を-2000
    _apply_ability(g, "P-011", 0, None, c.uid)                              # 魔力を0にする
    _apply_event(g, "Ex-021", 0, a.uid)                                     # ●+5000 ●エンドフェイズに捨て札
    _apply_event(g, "E-002", 1)                                             # 限制(不是加魔力)
    before = {m.source for m in st.modifiers} - {"Ex-021"}
    _use_ex070(g)
    assert {m.source for m in st.modifiers} == before
    assert any(sb.source == "Ex-021" for sb in st.standby)
    assert power(g, 1, c) == 0


# ---------------------------------------------------------------- 自我對戰

SELFPLAY_BOOKS = (
    ("M-001", "E-053", "Ex-070", "E-009", "S-001", "E-053", "M-017", "E-001", "S-002", "E-053", "Ex-023",
     "S-003", "M-052", "E-015", "S-001", "PR-010", "S-002", "E-048", "S-003", "M-002", "Ex-070", "S-001",
     "S-004", "S-001", "S-002", "S-003", "M-005", "S-010", "S-001", "S-002", "S-003", "E-030"),
    ("M-001", "S-001", "E-053", "M-017", "E-009", "S-002", "E-053", "Ex-070", "S-003", "M-052", "E-023",
     "S-022", "M-002", "S-003", "M-003", "S-004", "E-053", "M-005", "S-010", "S-001", "S-002", "S-003",
     "E-030", "S-002", "S-003", "S-001", "S-002", "S-003", "Ex-023", "S-002", "S-003", "S-008"),
)


@pytest.mark.slow
@pytest.mark.parametrize("levels", [("normal", "normal"), ("normal", "dummy"), ("dummy", "normal")])
@pytest.mark.parametrize("seed", [1, 2, 3])
def test_npc_selfplay_with_batch_cards(levels, seed):
    import random

    from gash import npc
    from gash.engine.awaiting import awaited_player
    from gash.engine.engine import new_game
    from gash.engine.state import GAME_OVER
    books = [list(b) for b in SELFPLAY_BOOKS]
    g = new_game(books[0], seed=seed, decks=(books[0], books[1]))
    rngs = [random.Random(f"{seed}:{p}") for p in (0, 1)]
    for _ in range(3000):
        if g.state.phase == GAME_OVER:
            break
        p = awaited_player(g)
        assert npc.submit_ranked(g, p, npc.decide(g, p, levels[p], rngs[p])) is not None
    assert g.state.phase == GAME_OVER
