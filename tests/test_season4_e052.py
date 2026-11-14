"""E-052 ウ・ソ 與被無效的效果(card-effects「第 4 賽季事件卡 E-052」、game-engine「被無效的效果」,season4-e052)。

効果文:このターン中に、相手のジャマー効果や「無効にする」効果などで無効にされた自分のカードの効果1つを選ぶ。
その効果を使っていないことにする(コストとしてはらったMPや、コストとして捨て札にしたカードはもどってくる)。
"""
import pytest

from gash.engine.cards import pending_cards
from gash.engine.effects.primitives import add_modifier
from gash.engine.engine import submit
from gash.engine.state import DUR_TURN
from tests.test_level2 import HEADS, TAILS, Rng, book, mk, to_battle
from tests.test_level3 import ability, add_slot, battle_in, choose, code, finish_damage, pass_effects


def test_e052_open():
    assert "E-052" not in pending_cards()


def negated(g, player):
    return [(r["card"], r["kind"]) for r in g.state.players[player].negated_this_turn]


def raise_event_limit(g, player):
    add_modifier(g, [], kind="event_limit", source="E-029", owner=player, duration=DUR_TURN,
                 target_player=player, amount=3)


def use_e052(g, player, page=None):
    """把 E-052 放在 player 翻開的頁(預設最後一個翻開頁)並使用。"""
    ps = g.state.players[player]
    page = page or ps.open_pages()[-1]
    ps.book[page - 1] = "E-052"
    return submit(g, {"type": "use_book_card", "player": player, "page": page})


# ---------------------------------------------------------------- 事件卡被 M-032 無效

def _event_negated():
    g, _ = mk(book("M-001", "E-009"), book("M-001"))
    st = g.state
    st.players[0].mp, st.players[1].mp = 10, 5
    add_slot(g, 1, "M-032")
    to_battle(g, 0)
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    assert st.pending.kind == "jammer_negate" and st.pending.player == 1
    choose(g, "M-032")
    assert st.action_player == 0
    return g


def test_event_negated_by_jammer_recorded():
    g = _event_negated()
    assert negated(g, 0) == [("E-009", "event")]
    assert g.state.players[0].negated_this_turn[0]["mp"] == 3
    assert negated(g, 1) == []


def test_e052_undoes_negated_event():
    g = _event_negated()
    st = g.state
    ps = st.players[0]
    raise_event_limit(g, 0)
    ps.pos = 2                                                           # 翻開 2、3 頁
    mp = ps.mp
    use_e052(g, 0, page=3)
    assert ps.mp == mp + 3                                               # E-052 費用 0,退回 E-009 的 3
    assert ps.events_used_this_turn == 1                                 # E-009 當作沒用過,只剩 E-052
    assert negated(g, 0) == []
    submit(g, {"type": "pass", "player": 1})
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})         # 同回合可再用(FAQ A1)
    assert any(m.source == "E-009" for m in st.modifiers)


# ---------------------------------------------------------------- 魔物效果被 M-026 無效

def _ability_negated(p0_extra=()):
    g, _ = mk(book("PR-002", "S-009"), book("M-001"))
    st = g.state
    st.players[0].mp, st.players[1].mp = 10, 5
    add_slot(g, 1, "M-026")
    for number in p0_extra:
        add_slot(g, 0, number)
    to_battle(g, 0)
    submit(g, ability(0, st.players[0].slots[0]))
    choose(g, "M-026")
    return g


def test_e052_undoes_negated_mamodo_effect():
    g = _ability_negated()
    st = g.state
    ps = st.players[0]
    assert negated(g, 0) == [("PR-002", "ability")]
    mp = ps.mp
    use_e052(g, 0)
    assert ps.mp == mp + 3 and "mamodo:PR-002" not in ps.used_abilities
    submit(g, {"type": "pass", "player": 1})
    submit(g, ability(0, ps.slots[0]))                                   # 同回合可再用
    assert any(m.source == "PR-002" for m in st.modifiers)


def test_e052_refund_ignores_mp_gain_lock():
    # 「もどってくる」不是「ふやす」:P-020(戰鬥階段中自己的效果不能使 MP 增加)不擋
    g = _ability_negated()
    ps = g.state.players[0]
    ps.slots[0].partner = "P-020"
    mp = ps.mp
    use_e052(g, 0)
    assert ps.mp == mp + 3


def test_e052_needs_negated_effect():
    g, _ = mk(book("M-001", "E-052"), book("M-001"))
    to_battle(g, 0)
    assert code(g, {"type": "use_book_card", "player": 0, "page": 2}) == "event.condition"


def test_negated_effects_cleared_at_turn_end():
    g = _ability_negated()
    st = g.state
    while st.turn_player == 0:
        submit(g, {"type": "pass", "player": st.action_player})
    assert negated(g, 0) == []


# ---------------------------------------------------------------- 費用棄掉的卡(干擾連鎖)

def _m032_chain():
    """玩家 1 使用 Ex-023;玩家 0 以 M-032 無效(M-032 棄掉);玩家 1 以 M-026 使 M-032 的無效化失效。"""
    g, _ = mk(book("M-017", "S-009"), book("M-001", "Ex-023"))      # 玩家 0 沒有其他ガッシュ・ベル(同名上限)
    st = g.state
    st.players[0].mp, st.players[1].mp = 10, 10
    m032 = add_slot(g, 0, "M-032")
    m032.injured = True
    add_slot(g, 1, "M-026")
    to_battle(g, 0)
    submit(g, {"type": "pass", "player": 0})
    submit(g, {"type": "use_book_card", "player": 1, "page": 2})
    choose(g, st.players[1].slots[0].uid) if st.pending.kind != "jammer_negate" else None
    assert st.pending.kind == "jammer_negate" and st.pending.player == 0
    choose(g, "M-032")
    assert st.pending.kind == "jammer_negate" and st.pending.player == 1
    choose(g, "M-026")
    assert "M-032" in st.players[0].discard
    return g, m032.uid


def test_chained_jammer_negation_recorded():
    g, _ = _m032_chain()
    assert negated(g, 0) == [("M-032", "jammer")]


def test_e052_returns_discarded_mamodo_not_as_played():
    g, uid = _m032_chain()
    st = g.state
    ps = st.players[0]
    assert st.action_player == 0
    events = use_e052(g, 0)
    back = st.slot_by_uid(0, uid)
    assert back is not None and back.stack == ["M-032"] and back.injured   # 原 uid、負傷狀態一併回來
    assert "M-032" not in ps.discard and "mamodo:M-032" not in ps.used_abilities
    assert not [e for e in events if e["type"] == "card_played"]           # 不算「場に出た」


def test_e052_discarded_mamodo_stays_when_field_full():
    g, uid = _m032_chain()
    st = g.state
    ps = st.players[0]
    while len(ps.slots) < 3:                                            # 場上 3 隻
        add_slot(g, 0, "M-004" if len(ps.slots) == 1 else "M-005")
    mp = ps.mp
    use_e052(g, 0)
    assert st.slot_by_uid(0, uid) is None and "M-032" in ps.discard        # 回不到原位:留在棄牌區
    assert ps.mp == mp and "mamodo:M-032" not in ps.used_abilities         # 其餘照常還原(M-032 費用 0)


# ---------------------------------------------------------------- 搭檔效果被 M-065 無效

def _partner_negated():
    g, _ = mk(book("M-004"), book("M-001"))
    st = g.state
    st.players[0].mp, st.players[1].mp = 10, 10
    st.players[0].slots[0].partner = "P-002"
    add_slot(g, 1, "M-065")
    to_battle(g, 0)
    g.rng = Rng(HEADS)
    submit(g, ability(0, st.players[0].slots[0], zone="partner"))      # 相手のＭＰを3へらす
    choose(g, "M-065")
    while st.pending is not None:                                      # 擲硬幣子階段
        choose(g, st.pending.options[0]["value"])
    assert st.players[1].mp == 10 and "P-002" in st.players[0].discard
    return g


def test_e052_returns_discarded_partner():
    g = _partner_negated()
    st = g.state
    ps = st.players[0]
    assert negated(g, 0) == [("P-002", "ability")]
    ps.pos = 1
    use_e052(g, 0, page=2)
    assert ps.slots[0].partner == "P-002" and "P-002" not in ps.discard
    assert "partner:P-002" not in ps.used_abilities


def test_e052_partner_stays_when_mamodo_gone():
    g = _partner_negated()
    st = g.state
    ps = st.players[0]
    rei = ps.slots[0]
    ps.slots.remove(rei)
    add_slot(g, 0, "M-001")
    use_e052(g, 0, page=2)
    assert "P-002" in ps.discard


# ---------------------------------------------------------------- 戰鬥中被無效的攻擊與防禦

def _attack_negated(coin=HEADS):
    """玩家 0 以 S-001 攻擊;玩家 1 以 S-025(擲幣正面:攻擊無效)防禦。"""
    g, _ = mk(book("M-001", "S-001"), book("M-001", "S-025"))
    st = g.state
    st.players[0].mp, st.players[1].mp = 10, 10
    to_battle(g, 0)
    g.rng = Rng(coin)
    battle_in(g, 2)
    submit(g, {"type": "declare_defense", "player": 1, "page": 2})
    while st.pending is not None and st.pending.kind != "protect":
        choose(g, st.pending.options[0]["value"])
    pass_effects(g)
    finish_damage(g)
    assert st.battle is None
    return g


def test_negated_attack_recorded_and_undone():
    g = _attack_negated()
    st = g.state
    ps = st.players[0]
    assert negated(g, 0) == [("S-001", "attack")]
    assert "ザケル" in ps.spell_names_by_turn.get(st.turn_no, [])
    assert code(g, {"type": "declare_attack", "player": 0, "page": 2}) == "spell.used"
    mp = ps.mp
    ps.pos = 2
    use_e052(g, 0, page=3)
    assert ps.mp == mp + 1                                               # S-001 的費用 1
    assert "ザケル" not in ps.spell_names_by_turn.get(st.turn_no, [])
    submit(g, {"type": "pass", "player": 1})
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})        # 同回合可再以那一頁攻擊
    assert st.battle_in is not None


def test_attack_not_negated_not_recorded():
    g = _attack_negated(coin=TAILS)
    assert negated(g, 0) == []


def test_own_effect_negation_not_recorded():
    # M-055 反面「その術は無効になる」是自己的效果
    g, _ = mk(book("M-055", "S-008"), book("M-001"))
    st = g.state
    st.players[0].mp = 10
    to_battle(g, 0)
    submit(g, ability(0, st.players[0].slots[0]))
    submit(g, {"type": "pass", "player": 1})
    g.rng = Rng(TAILS)
    battle_in(g, 2)
    choose(g, "use")
    assert st.battle.attack_negated
    submit(g, {"type": "no_defense", "player": 1})
    pass_effects(g)
    finish_damage(g)
    assert negated(g, 0) == []


def test_negated_defense_with_extra_cost_undone():
    # 攻方以 P-017(術による防御1つを無効)使 S-097 的防禦無效;防方退回含追加費用的 5 MP
    g, _ = mk(book("M-027", "S-049"), book("M-050", "S-097"))
    st = g.state
    st.players[0].mp, st.players[1].mp = 10, 10
    st.players[0].slots[0].partner = "P-017"
    to_battle(g, 0)
    battle_in(g, 2)
    submit(g, {"type": "declare_defense", "player": 1, "page": 2})
    choose(g, 2)                                                         # 追加費用 2
    assert st.players[1].mp == 10 - 5
    submit(g, ability(0, st.players[0].slots[0], zone="partner"))
    assert st.battle.defense_negated
    pass_effects(g)
    finish_damage(g)
    assert negated(g, 1) == [("S-097", "defense")]
    ps = st.players[1]
    ps.pos = 2
    raise_event_limit(g, 1)
    while st.action_player != 1:
        submit(g, {"type": "pass", "player": st.action_player})
    mp = ps.mp
    use_e052(g, 1, page=3)
    assert ps.mp == mp + 5


# ---------------------------------------------------------------- 多筆時由使用者選

def test_e052_user_chooses_among_negated_effects():
    g = _ability_negated()
    st = g.state
    ps = st.players[0]
    ps.negated_this_turn.append({"id": 500, "card": "E-009", "kind": "event", "mp": 3, "returns": [], "undo": {}})
    use_e052(g, 0)
    assert st.pending.kind == "pick_negated_effect" and st.pending.player == 0
    assert code(g, {"type": "choose", "player": 0, "value": 99}) == "choose.invalid"
    assert st.pending.kind == "pick_negated_effect"
    first = st.pending.options[0]["value"]
    mp = ps.mp
    choose(g, first)
    assert ps.mp == mp + 3 and len(ps.negated_this_turn) == 1


# ---------------------------------------------------------------- 自我對戰

SELFPLAY_BOOKS = (
    ("M-017", "E-052", "PR-002", "E-009", "S-009", "E-052", "M-055", "S-008", "E-052", "M-004", "P-002",
     "S-001", "E-029", "S-022", "S-009", "M-002", "S-003", "E-052", "S-005", "S-010", "S-009", "M-003",
     "S-004", "S-009", "S-002", "S-003", "M-005", "S-010", "S-009", "S-002", "S-003", "E-030"),
    ("M-001", "S-001", "M-026", "M-032", "S-025", "S-002", "M-065", "E-052", "S-003", "S-022", "S-025",
     "S-022", "M-002", "S-003", "M-003", "S-004", "E-052", "M-005", "S-010", "S-001", "S-002", "S-003",
     "E-030", "S-002", "S-003", "S-001", "S-002", "S-003", "S-025", "S-002", "S-003", "S-008"),
)


@pytest.mark.slow
@pytest.mark.parametrize("levels", [("normal", "normal"), ("normal", "dummy"), ("dummy", "normal")])
@pytest.mark.parametrize("seed", [1, 2, 3])
def test_npc_selfplay_with_e052(levels, seed):
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
