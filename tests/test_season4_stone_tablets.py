"""第 4 賽季石版相關卡(card-effects「第 4 賽季石版相關卡」、game-engine「石版魔物」「不能放回棄牌區的卡」,
season4-stone-tablets)。依日文效果文。
"""
import pytest

from gash.engine.cards import pending_cards
from gash.engine.effects import registry as reg
from gash.engine.effects.primitives import add_restriction
from gash.engine.engine import _spell_usable_by, mamodo_effect_block, power_breakdown, submit
from gash.engine.state import DUR_TURN, NO_MAMODO_EFFECTS
from tests.test_level2 import HEADS, Rng, book, mk, to_battle
from tests.test_level3 import ability, add_slot, choose, code

BATCH = ("Ex-000", "Ex-049", "Ex-069", "M-085", "Ex-056", "Ex-057", "Ex-058")


def test_batch_open():
    assert not set(BATCH) & pending_cards()


def setup(b0=("M-001",), b1=("M-001",), mp=10):
    g, _ = mk(book(*b0), book(*b1))
    st = g.state
    st.players[0].mp = st.players[1].mp = mp
    to_battle(g, 0)
    return g


def use(g, page=2, player=0):
    return submit(g, {"type": "use_book_card", "player": player, "page": page})


def spell(g, number):
    return g.db[number]


# ---------------------------------------------------------------- Ex-000

def test_ex000_no_own_stone_tablet_damages_opponent_stone_tablet():
    # ●自分の場に石版魔物がいないとき、相手の石版魔物1体を選び、ダメージをあたえる
    g = setup(("M-001", "Ex-000"))
    st = g.state
    stone = st.players[1].slots[0]
    stone.stack = ["Ex-056"]
    add_slot(g, 1, "M-017")
    use(g)
    assert st.pending.kind == "protect" and st.pending.player == 1          # 只有一個 ●、一個對象:自動選
    choose(g, None)
    assert stone.injured and not st.players[1].slots[1].injured


def test_ex000_only_stone_tablets_damages_opponent_other_mamodo():
    # ●自分の場に石版魔物以外の魔物がいないとき、相手の石版魔物以外の魔物1体を選び、ダメージをあたえる
    g = setup(("M-001", "Ex-000"))
    st = g.state
    st.players[0].slots[0].stack = ["Ex-057"]
    st.players[1].slots[0].stack = ["Ex-056"]
    other = add_slot(g, 1, "M-017")
    use(g)
    assert st.pending.kind == "protect"
    choose(g, None)
    assert other.injured and not st.players[1].slots[0].injured


def test_ex000_both_conditions_fail_unusable():
    g = setup(("M-001", "Ex-000"))
    st = g.state
    add_slot(g, 0, "Ex-057")                                               # 自己兩種都有
    st.players[1].slots[0].stack = ["Ex-056"]
    add_slot(g, 1, "M-017")
    assert code(g, {"type": "use_book_card", "player": 0, "page": 2}) == "event.condition"


def test_ex000_condition_true_but_no_target_unusable():
    g = setup(("M-001", "Ex-000"))                                         # 對手沒有石版魔物
    assert code(g, {"type": "use_book_card", "player": 0, "page": 2}) == "event.condition"


def test_ex000_player_chooses_when_both_available():
    # 自己場上沒有魔物不可能;以「自己場上的魔物全被移走」以外的方式:兩個 ● 都成立需要自己場上沒有魔物,
    # 所以改測對象由使用者選:對手有兩隻石版魔物
    g = setup(("M-001", "Ex-000"))
    st = g.state
    a = st.players[1].slots[0]
    a.stack = ["Ex-056"]
    b = add_slot(g, 1, "Ex-057")
    use(g)
    assert st.pending.kind == "pick_opponent_mamodo" and st.pending.player == 0
    assert {o["value"] for o in st.pending.options} == {a.uid, b.uid}
    choose(g, b.uid)
    choose(g, None) if st.pending is not None and st.pending.kind == "protect" else None
    assert b.injured


# ---------------------------------------------------------------- Ex-049

def _ex049():
    g = setup(("Ex-049",), ("M-001",))
    st = g.state
    stone = st.players[1].slots[0]
    stone.stack = ["Ex-056"]
    other = add_slot(g, 1, "M-017")
    assert _spell_usable_by(g, 1, stone, spell(g, "S-044"))
    submit(g, ability(0, st.players[0].slots[0]))                          # MP 1
    assert st.players[0].mp == 9
    return g, stone, other


def test_ex049_blocks_stone_tablet_mamodo_effects():
    # 【ステイ】このターン中、相手は、石版魔物の「魔物の効果」を使えない
    g, stone, other = _ex049()
    assert mamodo_effect_block(g, 1, stone) == "mamodo_restricted"
    assert not _spell_usable_by(g, 1, stone, spell(g, "S-044"))           # 「このカードが場にある→」也擋
    assert mamodo_effect_block(g, 1, other) is None


def test_ex049_also_blocks_stone_tablets_deployed_later():
    g, _, _ = _ex049()
    later = add_slot(g, 1, "Ex-058")
    assert mamodo_effect_block(g, 1, later) == "mamodo_restricted"


def test_ex049_ends_with_turn():
    g, stone, _ = _ex049()
    st = g.state
    while st.turn_player == 0:
        submit(g, {"type": "pass", "player": st.action_player})
    assert mamodo_effect_block(g, 1, stone) is None


# ---------------------------------------------------------------- Ex-069

def power(g, player, slot):
    return power_breakdown(g, player, slot)[0]


def test_ex069_boosts_own_stone_tablets_including_later_ones():
    # 【ステイ】自分の石版魔物すべてを選ぶ。次の自分のターンのエンドフェイズまで、その魔物の魔力を+2000する
    g = setup(("M-001", "Ex-069"))
    st = g.state
    gash = st.players[0].slots[0]
    stone = add_slot(g, 0, "Ex-056")
    opp_stone = st.players[1].slots[0]
    opp_stone.stack = ["Ex-057"]
    before = {id(s): power(g, p, s) for p, s in ((0, gash), (0, stone), (1, opp_stone))}
    use(g)
    assert power(g, 0, stone) == before[id(stone)] + 2000
    assert power(g, 0, gash) == before[id(gash)]
    assert power(g, 1, opp_stone) == before[id(opp_stone)]
    later = add_slot(g, 0, "Ex-058")
    assert power(g, 0, later) == g.db["Ex-058"].power_base + 2000           # 之後放出的也加(比照 E-048)


def test_ex069_removed_by_ex070():
    from gash.engine.engine import remove_power_ups
    g = setup(("M-001", "Ex-069"))
    stone = add_slot(g, 0, "Ex-056")
    use(g)
    remove_power_ups(g, [], 1)
    assert power(g, 0, stone) == g.db["Ex-056"].power_base


# ---------------------------------------------------------------- M-085

def _m085(b0, **kw):
    g = setup(b0, ("M-085",), **kw)
    return g


def test_m085_blocks_e033():
    # 相手は、捨て札のカードを、場や魔本にもどすことができない
    g = _m085(("M-001", "E-033"))
    ps = g.state.players[0]
    ps.discard.append("M-017")
    assert ps.consumed_pages
    assert code(g, {"type": "use_book_card", "player": 0, "page": 2}) == "event.condition"


def test_m085_blocked_by_mamodo_effect_restriction():
    # 「このカードが場にある→」も「魔物の効果を使えない」で止まる
    g = _m085(("M-001", "E-033"))
    st = g.state
    st.players[0].discard.append("M-017")
    add_restriction(g, [], source="E-025", owner=0, target_player=1, flag=NO_MAMODO_EFFECTS, duration=DUR_TURN)
    use(g)
    if st.pending is not None:
        choose(g, st.pending.options[0]["value"])
    assert "M-017" not in st.players[0].discard


def test_m085_blocks_e011_and_s090():
    g = _m085(("M-001", "E-011", "S-090"))
    ps = g.state.players[0]
    ps.discard.append("P-001")
    assert code(g, {"type": "use_book_card", "player": 0, "page": 2}) == "event.condition"
    ps.pos = 2
    assert code(g, {"type": "use_book_card", "player": 0, "page": 3}) == "spell.condition"


def test_m085_e022_flips_but_returns_nothing():
    g = _m085(("M-001", "E-022"))
    st = g.state
    ps = st.players[0]
    ps.discard.append("P-001")
    ps.discarded_this_turn.append("P-001")
    g.rng = Rng(HEADS)
    use(g)
    while st.pending is not None and st.pending.player == 0 and st.pending.kind.startswith("coin"):
        choose(g, st.pending.options[0]["value"])
    assert "P-001" in ps.discard and ps.slots[0].partner is None


def test_m085_blocks_m025_and_m058_options():
    from gash.engine.effects.tree import DiscardedCardsToReturn, OpponentDiscardedPartner
    g = _m085(("M-001",))
    st = g.state
    st.players[0].discard.append("M-024")
    st.players[1].discard.append("P-001")
    assert DiscardedCardsToReturn(numbers=("M-024", "M-025")).options(g, {"player": 0}) == []
    assert OpponentDiscardedPartner().options(g, {"player": 0}) == []
    st.players[1].discard.append("M-024")
    assert DiscardedCardsToReturn(numbers=("M-024", "M-025")).options(g, {"player": 1}) != []   # 持有者本身不受限


def test_m085_keeps_e052_cost_card_in_discard():
    from tests.test_season4_e052 import _m032_chain, use_e052
    g, uid = _m032_chain()
    st = g.state
    add_slot(g, 1, "M-085")
    mp = st.players[0].mp
    use_e052(g, 0)
    assert st.slot_by_uid(0, uid) is None and "M-032" in st.players[0].discard
    assert "mamodo:M-032" not in st.players[0].used_abilities and st.players[0].mp == mp


# ---------------------------------------------------------------- Ex-056 / Ex-057 / Ex-058

@pytest.mark.parametrize("mamodo, spell_no, other", [
    ("Ex-056", "S-044", "S-065"),       # 「マルス」の術
    ("Ex-057", "S-065", "S-044"),       # 「エシュロス」の術
    ("Ex-058", "S-042", "S-043"),       # 術カード「ビライツ」(ロブノスの「レリ・ブルク」は不可)
])
def test_stone_tablet_spell_compat(mamodo, spell_no, other):
    g = setup()
    slot = g.state.players[0].slots[0]
    slot.stack = [mamodo]
    assert _spell_usable_by(g, 0, slot, spell(g, spell_no))
    assert not _spell_usable_by(g, 0, slot, spell(g, other))
    add_restriction(g, [], source="E-025", owner=1, target_player=0, flag=NO_MAMODO_EFFECTS, duration=DUR_TURN)
    assert not _spell_usable_by(g, 0, slot, spell(g, spell_no))


def test_ex056_attacks_with_marus_spell():
    g = setup(("Ex-056", "S-044"))
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    assert g.state.battle_in is not None


def test_stone_tablet_flag():
    assert g_db()["Ex-056"].stone_tablet and not g_db()["M-001"].stone_tablet


def g_db():
    from gash.engine.cards import card_db
    return card_db()


# ---------------------------------------------------------------- 自我對戰

SELFPLAY_BOOKS = (
    ("Ex-056", "Ex-069", "S-044", "Ex-000", "Ex-057", "S-065", "Ex-058", "S-042", "S-044", "S-045", "Ex-069",
     "S-065", "S-066", "S-044", "S-042", "S-045", "S-065", "Ex-000", "S-044", "S-066", "S-042", "S-045",
     "S-065", "S-044", "S-042", "S-066", "S-045", "S-065", "S-044", "S-042", "S-066", "E-030"),
    ("M-001", "S-001", "Ex-049", "Ex-000", "M-085", "S-002", "E-033", "S-003", "E-011", "P-001", "S-022",
     "M-002", "S-003", "M-003", "S-004", "S-090", "M-005", "S-010", "S-001", "S-002", "S-003", "E-022",
     "E-030", "S-002", "S-003", "S-001", "S-002", "S-003", "Ex-000", "S-002", "S-003", "S-008"),
)


@pytest.mark.slow
@pytest.mark.parametrize("levels", [("normal", "normal"), ("normal", "dummy"), ("dummy", "normal")])
@pytest.mark.parametrize("seed", [1, 2, 3])
def test_npc_selfplay_with_stone_tablets(levels, seed):
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
