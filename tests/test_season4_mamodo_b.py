"""第 4 賽季魔物與搭檔第 2 批(card-effects「第 4 賽季魔物與搭檔第 2 批」;game-engine「雙方都不能選擇的魔物」
「不能棄掉自己的魔物」「戰鬥階段的翻頁限制」「不能被看的魔書」,season4-mamodo-b)。依日文效果文。
"""
import pytest

from gash.engine.cards import pending_cards
from gash.engine.effects.primitives import add_restriction
from gash.engine.engine import submit
from gash.engine.state import DUR_TURN, NO_MAMODO_EFFECTS, NO_PARTNER_EFFECTS
from tests.test_level2 import HEADS, Rng, book, mk, to_battle
from tests.test_level3 import ability, add_slot, battle_in, choose, code, finish_damage, pass_effects

BATCH = ("Ex-051", "Ex-053", "Ex-054", "Ex-059", "Ex-099", "M-070", "M-075", "M-079", "P-047", "P-048",
         "P-049", "PR-012")


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


def block_effects(g, owner_of_card, flag=NO_MAMODO_EFFECTS):
    """owner_of_card 的魔物效果(或搭檔效果)被「使えない」擋下。"""
    add_restriction(g, [], source="E-025", owner=1 - owner_of_card, target_player=owner_of_card, flag=flag,
                    duration=DUR_TURN)


def end_turn(g):
    st = g.state
    tp = st.turn_player
    while st.turn_player == tp:
        if st.pending is not None:
            choose(g, st.pending.options[0]["value"])
            continue
        submit(g, {"type": "pass", "player": st.action_player})
    if st.phase == "start":
        to_battle(g, st.turn_player)


# ---------------------------------------------------------------- Ex-099 / M-075:雙方都不能選

def test_ex099_alone_cannot_be_chosen_by_either_player():
    # この効果は、自分の場にこの魔物以外の魔物がいないとき使える。自分も相手も、カードを選ぶとき、この魔物を選ぶことができない
    g = setup(("M-001", "E-009"), ("M-001", "E-024"))
    st = g.state
    st.players[0].slots[0].stack = ["Ex-099"]
    assert code(g, {"type": "use_book_card", "player": 0, "page": 2}) == "event.condition"   # 自分の効果も
    submit(g, {"type": "pass", "player": 0})
    assert code(g, {"type": "use_book_card", "player": 1, "page": 2}) == "event.condition"   # FAQ A1


def test_ex099_with_other_mamodo_is_selectable():
    from gash.engine.effects.primitives import selectable_opponent_slots
    g = setup()
    st = g.state
    st.players[0].slots[0].stack = ["Ex-099"]
    add_slot(g, 0, "M-017")
    assert len(selectable_opponent_slots(g, 1)) == 2


def test_m075_unselectable_and_blocked_by_restriction():
    from gash.engine.effects.primitives import selectable_opponent_slots, selectable_own_slots
    g = setup()
    st = g.state
    es = st.players[0].slots[0]
    es.stack = ["M-075"]
    other = add_slot(g, 0, "M-017")
    assert [s.uid for s in selectable_opponent_slots(g, 1)] == [other.uid]
    assert [s.uid for s in selectable_own_slots(g, 0)] == [other.uid]
    block_effects(g, 0)
    assert es.uid in [s.uid for s in selectable_opponent_slots(g, 1)]


def test_m075_using_its_spell_locks_its_effect_next_turn():
    # 自分がこの魔物の術を使ったとき、次のターン中、この魔物の「魔物の効果」を使えない
    from gash.engine.effects.primitives import selectable_opponent_slots
    from gash.engine.engine import mamodo_effect_block
    g = setup(("M-075", "S-065"))
    st = g.state
    es = st.players[0].slots[0]
    battle_in(g, 2)
    submit(g, {"type": "no_defense", "player": 1})
    pass_effects(g)
    finish_damage(g)
    assert mamodo_effect_block(g, 0, es) is None                           # このターンはまだ
    end_turn(g)
    assert mamodo_effect_block(g, 0, es) == "mamodo_locked"
    assert es.uid in [s.uid for s in selectable_opponent_slots(g, 1)]
    end_turn(g)
    assert mamodo_effect_block(g, 0, es) is None


# ---------------------------------------------------------------- Ex-051

def test_ex051_at_last_page_blocks_opponent_events_and_partners():
    # 自分の魔本が最後のページのとき、相手は、イベントカードやパートナーカードの効果を使えない
    from gash.engine.engine import partner_effects_blocked
    g = setup(("Ex-051",), ("M-001", "E-024"))
    st = g.state
    opp = st.players[1].slots[0]
    opp.partner = "P-001"
    submit(g, {"type": "pass", "player": 0})
    assert not partner_effects_blocked(g, 1, opp)
    st.players[0].pos = 32
    assert partner_effects_blocked(g, 1, opp)
    assert code(g, {"type": "use_book_card", "player": 1, "page": 2}) == "event.restricted"


def test_ex051_blocked_by_restriction():
    from gash.engine.engine import partner_effects_blocked
    g = setup(("Ex-051",), ("M-001",))
    st = g.state
    st.players[1].slots[0].partner = "P-001"
    st.players[0].pos = 32
    block_effects(g, 0)
    assert not partner_effects_blocked(g, 1, st.players[1].slots[0])


# ---------------------------------------------------------------- Ex-053

def test_ex053_blocks_same_name_as_discarded_this_turn():
    # 相手は、このターン中に捨て札にしたカードとカード名が同じカードを、場に出すことができない
    from gash.engine.engine import play_block
    g = setup(("M-001",), ("M-004", "P-002"))
    st = g.state
    add_slot(g, 0, "Ex-053")
    assert play_block(g, 1, "P-002") is None
    st.players[1].discard.append("P-002")
    st.players[1].discarded_this_turn.append("P-002")
    assert play_block(g, 1, "P-002") == "discarded_name"
    assert play_block(g, 0, "P-002") != "discarded_name"                   # 持有者本身不受限


def test_ex053_also_blocks_effect_deploy():
    from gash.engine.effects.tree import AttachablePartnerPagesInOwnBook
    g = setup(("M-001",), ("M-004", "P-002"))
    st = g.state
    add_slot(g, 0, "Ex-053")
    st.players[1].discarded_this_turn.append("P-002")
    assert AttachablePartnerPagesInOwnBook().options(g, {"player": 1}) == []


# ---------------------------------------------------------------- Ex-054

def test_ex054_on_play_locks_opponent_cards_during_battle_phase():
    # このカードが場に出たとき、相手の場のカードすべてを選ぶ。【ステイ】このターンのバトルフェイズ中、相手はそのカードの効果を使えない
    from gash.engine.engine import mamodo_effect_block, partner_effects_blocked
    g = setup(("M-001", "Ex-054"), ("M-001",))
    st = g.state
    opp = st.players[1].slots[0]
    opp.partner = "P-001"
    later = add_slot(g, 1, "M-004")
    submit(g, {"type": "play_card", "player": 0, "page": 2})
    assert mamodo_effect_block(g, 1, opp) == "mamodo_locked" and partner_effects_blocked(g, 1, opp)
    later.partner = "P-002"                                                # 選んだ後につけたパートナー
    assert mamodo_effect_block(g, 1, later) == "mamodo_locked"
    assert not partner_effects_blocked(g, 1, later)


def test_ex054_not_in_end_phase():
    from gash.engine.engine import restriction_live
    g = setup(("M-001", "Ex-054"), ("M-001",))
    st = g.state
    submit(g, {"type": "play_card", "player": 0, "page": 2})
    locks = [m for m in st.modifiers if m.source == "Ex-054"]
    assert locks
    st.phase = "end"
    assert not any(restriction_live(g, m) for m in locks)


# ---------------------------------------------------------------- Ex-059 / M-070

@pytest.mark.parametrize("number, zone, flags", [
    ("Ex-059", "partner", {"no_partner_effects", "no_events"}),
    ("M-070", "mamodo", {"no_mamodo_effects", "no_partner_effects"}),
])
def test_battle_lock_when_attacking_with_gash(number, zone, flags):
    g = setup(("M-001", "S-001"), ("M-001",))
    st = g.state
    gash = st.players[0].slots[0]
    if zone == "partner":
        gash.partner = number
    else:
        gash.stack = [number]
    submit(g, ability(0, gash, zone=zone))
    submit(g, {"type": "pass", "player": 1})
    battle_in(g, 2)
    got = {m.flag for m in st.modifiers if m.source == number and m.kind == "restriction"}
    assert got == flags and all(m.target_player == 1 for m in st.modifiers if m.source == number)


# ---------------------------------------------------------------- M-079

def test_m079_blocks_book_viewing_cards():
    # 相手は、自分(このカードの持ち主)の魔本を見なければ使えない効果を使えない(FAQ:E-014 はすべて使えなくなる)
    g = setup(("M-001", "E-014"), ("M-079",))
    assert code(g, {"type": "use_book_card", "player": 0, "page": 2}) == "event.book_hidden"


def test_m079_blocks_book_viewing_ability_and_spell():
    g = setup(("M-011", "S-104"), ("M-079",))
    st = g.state
    feyn = st.players[0].slots[0]
    assert code(g, ability(0, feyn)) == "ability.book_hidden"               # 《索敵》
    add_slot(g, 0, "M-052")
    assert code(g, {"type": "declare_attack", "player": 0, "page": 2,
                    "slot_uid": st.players[0].slots[-1].uid}) == "spell.book_hidden"


def test_m079_disables_p024_reveal():
    from gash.engine.engine import reveals_open_pages
    g = setup(("M-001",), ("M-079",))
    st = g.state
    st.players[0].slots[0].stack = ["M-038"]
    st.players[0].slots[0].partner = "P-024"
    assert not reveals_open_pages(g, 0, 1)


def test_m079_blocked_by_restriction():
    g = setup(("M-001", "E-014"), ("M-079",))
    block_effects(g, 1)
    use(g)
    assert g.state.players[1].pos > 1


# ---------------------------------------------------------------- P-047

def test_p047_discards_non_mamodo_passive_card():
    # 自分か相手の場の「このカードが場にある→」の効果を持つ、魔物以外のカード1枚を選び、捨て札にする
    g = setup(("M-001",), ("M-001",))
    st = g.state
    pat = st.players[0].slots[0]
    pat.stack, pat.partner = ["M-079"], "P-047"
    opp = st.players[1].slots[0]
    opp.stack, opp.partner = ["M-038"], "P-024"                             # 「このカードが場にある→」
    add_slot(g, 1, "M-017", partner="P-012")                                # 「このカードを捨て札にする→」:不可
    submit(g, ability(0, pat, zone="partner"))
    assert opp.partner is None and "P-024" in st.players[1].discard


def test_p047_respects_partner_guard():
    g = setup(("M-001",), ("M-001",))
    st = g.state
    pat = st.players[0].slots[0]
    pat.stack, pat.partner = ["M-079"], "P-047"
    opp = st.players[1].slots[0]
    opp.stack, opp.partner = ["M-078"], "P-024"                             # M-078:相手の効果では捨て札にならない
    assert code(g, ability(0, pat, zone="partner")) == "ability.condition"


# ---------------------------------------------------------------- P-048

def test_p048_blocks_own_mamodo_discard():
    # 相手は、相手自身の場の魔物を捨て札にできない(魔物がダメージを受けて捨て札になるのはよい)
    g = setup(("M-001", "E-019"), ("M-022",))
    st = g.state
    st.players[1].slots[0].partner = "P-048"
    add_slot(g, 0, "M-017")
    assert code(g, {"type": "use_book_card", "player": 0, "page": 2}) == "event.condition"


def test_p048_blocks_discard_cost_and_jammer():
    from gash.engine.engine import _jammer_holder
    g = setup(("M-001", "Ex-023"), ("M-022",))
    st = g.state
    st.players[1].slots[0].partner = "P-048"
    m033 = add_slot(g, 0, "M-033")
    add_slot(g, 0, "M-032")
    assert code(g, ability(0, m033)) == "ability.own_discard_blocked"
    assert _jammer_holder(g, 0, "event") is None


def test_p048_damage_discard_still_happens():
    g = setup(("M-001", "S-001"), ("M-022",))
    st = g.state
    st.players[1].slots[0].partner = "P-048"
    st.players[1].slots[0].injured = True
    st.players[1].slots[0].stack = ["M-022"]
    from gash.engine.engine import _start_damage
    _start_damage(g, [], [{"kind": "slot", "player": 1, "slot_uid": st.players[1].slots[0].uid, "amount": 1}],
                  {"cause": "effect", "source": "test", "source_player": 0, "amount": 1})
    assert "M-022" in st.players[1].discard


# ---------------------------------------------------------------- P-049 / PR-012

def test_p049_blocks_opponent_turning_back_in_battle_phase():
    # 相手は、バトルフェイズ中、相手自身の魔本をもどすことができない
    g = setup(("M-001", "PR-007"), ("M-001",))
    st = g.state
    st.players[1].slots[0].stack = ["Ex-002"]
    st.players[1].slots[0].partner = "P-049"
    st.players[0].pos = 5
    st.players[0].book[5] = "PR-007"
    use(g, page=6)
    assert st.players[0].pos == 5


def test_p049_action_discard():
    g = setup(("M-001",), ("M-001",))
    st = g.state
    st.players[1].slots[0].stack = ["Ex-002"]
    st.players[1].slots[0].partner = "P-049"
    submit(g, {"type": "pass", "player": 0})
    submit(g, {"type": "use_action_effect", "player": 1, "zone": "partner", "slot_uid": st.players[1].slots[0].uid})
    assert "P-049" in st.players[1].discard


def test_pr012_blocks_effect_page_turn_in_battle_phase():
    # 自分も相手も、バトルフェイズに、ダメージ以外の効果で、魔本をめくることはできない
    g = setup(("M-001", "E-014"), ("PR-012",))
    st = g.state
    pos = st.players[1].pos
    use(g)
    assert st.players[1].pos == pos


def test_pr012_damage_still_turns_pages():
    g = setup(("M-001", "S-001"), ("PR-012",))
    st = g.state
    pos = st.players[1].pos
    battle_in(g, 2)
    submit(g, {"type": "no_defense", "player": 1})
    pass_effects(g)
    finish_damage(g)
    assert st.players[1].pos == pos + 2


# ---------------------------------------------------------------- 自我對戰

SELFPLAY_BOOKS = (
    ("M-075", "S-065", "M-079", "Ex-099", "P-047", "S-066", "Ex-054", "PR-012", "S-067", "E-009", "S-065",
     "S-066", "M-070", "S-065", "S-066", "Ex-051", "S-067", "S-065", "S-066", "S-067", "S-065", "S-066",
     "S-065", "S-066", "S-067", "S-065", "S-066", "S-067", "E-030", "S-065", "S-066", "S-067"),
    ("M-001", "S-001", "M-022", "P-048", "Ex-059", "S-002", "E-014", "S-003", "Ex-053", "E-024", "S-001",
     "M-002", "S-003", "P-049", "S-004", "E-019", "M-005", "S-010", "S-001", "S-002", "S-003", "PR-007",
     "E-030", "S-002", "S-003", "S-001", "S-002", "S-003", "E-005", "S-002", "S-003", "S-008"),
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
