"""第 4 賽季 Ex-060 アポロ《自由人》(card-effects「第 4 賽季 Ex-060」;game-engine「今のページ以外的卡的限制」,
season4-ex060)。依日文效果文:
このカードが場にある→相手は、相手自身の魔本の今のページ以外のページのカードを使う効果を使えず、
相手自身の魔本の今のページ以外のページのカードを場に出したり、捨て札にしたり、ページを移動させることができない。
"""
import pytest

from gash.engine.cards import pending_cards
from gash.engine.engine import submit
from gash.engine.state import NO_PARTNER_EFFECTS
from tests.test_level2 import HEADS, Rng, book, mk, to_battle
from tests.test_level3 import ability, choose, code
from tests.test_season4_mamodo_b import block_effects


def test_ex060_open():
    assert "Ex-060" not in pending_cards()


def setup(b0=("M-001",), b1=("M-001",), mp=10, holder=1):
    """holder 的魔物裝上 Ex-060;玩家 0 的戰鬥階段,翻開 2、3 頁。"""
    g, _ = mk(book(*b0), book(*b1))
    st = g.state
    st.players[0].mp = st.players[1].mp = mp
    to_battle(g, 0)
    st.players[holder].slots[0].partner = "Ex-060"
    return g


def use(g, page=2, player=0):
    return submit(g, {"type": "use_book_card", "player": player, "page": page})


# ---------------------------------------------------------------- 使用其他頁卡片的效果:發動(使用者決定)

def test_p015_cannot_be_used():
    g = setup(("M-024", "S-029", "S-029", "S-042"))
    slot = g.state.players[0].slots[0]
    slot.partner = "P-015"
    assert code(g, ability(0, slot, zone="partner")) == "ability.other_pages"


def test_ex037_cannot_be_used():
    g = setup(("M-001", "S-029", "S-029", "S-029", "E-003"))
    slot = g.state.players[0].slots[0]
    slot.partner = "Ex-037"
    assert code(g, ability(0, slot, zone="partner")) == "ability.other_pages"


@pytest.mark.parametrize("number", ["S-145", "PR-006"])
def test_nonbattle_spell_cannot_be_used(number):
    g = setup(("M-001", number))
    assert code(g, {"type": "use_book_card", "player": 0, "page": 2}) == "spell.other_pages"


# ---------------------------------------------------------------- 使用其他頁卡片的效果:既有待命

def test_existing_standby_cannot_use_other_page():
    # P-015 在 Ex-060 上場前建立待命;之後不能從翻開頁以外使用「ビライツ」
    g = setup(("M-024", "S-029", "S-029", "S-029", "S-042"), holder=0)
    st = g.state
    st.players[0].slots[0].partner = None
    slot = st.players[0].slots[0]
    slot.partner = "P-015"
    submit(g, ability(0, slot, zone="partner"))
    submit(g, {"type": "pass", "player": 1})
    st.players[1].slots[0].partner = "Ex-060"
    assert code(g, {"type": "declare_attack", "player": 0, "page": 5, "slot_uid": slot.uid}) == "page.not_open"


def test_s145_standby_cannot_use_other_page():
    g = setup(("M-001", "S-145", "S-029", "S-029", "S-001"), holder=0)
    st = g.state
    st.players[0].slots[0].partner = None
    g.rng = Rng(HEADS)
    use(g)
    if st.pending is not None:
        choose(g, st.pending.options[0]["value"])
    submit(g, {"type": "pass", "player": 1})
    st.players[1].slots[0].partner = "Ex-060"
    slot = st.players[0].slots[0]
    assert code(g, {"type": "declare_attack", "player": 0, "page": 5, "slot_uid": slot.uid}) == "page.not_open"


# ---------------------------------------------------------------- 放出、重疊、移動頁

def test_e012_only_open_pages():
    # 自分の魔本の好きなページから魔物カードを1枚選び、場に出す → 今のページ(翻開的 2、3 頁)だけ
    g = setup(("M-001", "E-012", "M-012", "S-029", "S-029", "S-029", "S-029", "M-014"))
    use(g)
    st = g.state
    if st.pending is not None:
        assert [o["value"] for o in st.pending.options] == [3]
    else:
        assert any(s.top == "M-012" for s in st.players[0].slots)
    assert 8 not in st.players[0].consumed_pages


def test_e012_without_open_candidates_cannot_be_used():
    g = setup(("M-001", "E-012", "S-029", "S-029", "S-029", "S-029", "S-029", "M-014"))
    assert code(g, {"type": "use_book_card", "player": 0, "page": 2}) == "event.condition"


def test_e027_opponent_deploy_limited_when_holder_uses_it():
    # 持有者自己用 E-027:「相手は…相手の魔本の好きなページからパートナーカード1枚を選び、場に出す」也只能選翻開的頁
    g = setup(("M-001", "E-027"), ("M-001", "S-029", "P-001", "S-029", "S-029", "S-029", "S-029", "P-001"),
              holder=0)
    use(g)
    st = g.state
    if st.pending is not None:                                            # 只剩一頁時自動選
        assert st.pending.player == 1 and [o["value"] for o in st.pending.options] == [3]
        choose(g, 3)
    assert st.players[1].slots[0].partner == "P-001"
    assert 3 in st.players[1].consumed_pages and 8 not in st.players[1].consumed_pages


def test_stack_from_book_only_open_pages():
    from gash.engine.effects.tree import CanStackFromBook, OwnBookCopiesOf
    g = setup(("M-001", "S-029", "S-029", "S-029", "S-029", "S-029", "S-029", "M-046"))
    st = g.state
    st.players[0].slots[0].stack = ["M-045"]                              # ウマゴン
    assert OwnBookCopiesOf("M-046").options(g, {"player": 0}) == []
    assert not CanStackFromBook("M-046")(g, 0)
    st.players[1].slots[0].partner = None
    assert OwnBookCopiesOf("M-046").options(g, {"player": 0})


def test_m016_cannot_move_earlier_page():
    g = setup(("M-016", "E-003", "S-029", "E-004", "S-001"))
    ps = g.state.players[0]
    ps.pos = 4
    assert code(g, ability(0, ps.slots[0])) == "ability.condition"


# ---------------------------------------------------------------- 不受影響

def test_holder_book_not_protected():
    # 「相手自身の魔本」:對手影響持有者魔書的效果不受限(E-016 可選翻開頁以外的戰術)
    g = setup(("M-001", "E-016"), ("M-001", "S-001", "S-029", "S-029", "S-029", "S-029", "S-002"))
    use(g)
    st = g.state
    pages = [o.get("page", o["value"]) for o in st.pending.options if isinstance(o.get("value"), int)]
    assert any(p > 3 for p in pages)


def test_blocked_by_restriction():
    g = setup(("M-001", "E-012", "S-029", "S-029", "S-029", "S-029", "S-029", "M-014"))
    block_effects(g, 1, flag=NO_PARTNER_EFFECTS)
    use(g)
    st = g.state
    if st.pending is not None:
        choose(g, 8)
    assert any(s.top == "M-014" for s in st.players[0].slots)


# ---------------------------------------------------------------- 自我對戰

SELFPLAY_BOOKS = (
    ("M-038", "Ex-060", "S-069", "S-070", "E-027", "S-069", "S-070", "S-069", "S-070", "E-012", "S-069",
     "S-070", "S-069", "S-070", "S-069", "S-070", "S-069", "S-070", "S-069", "S-070", "S-069", "S-070",
     "S-069", "S-070", "S-069", "S-070", "S-069", "S-070", "S-069", "S-070", "S-069", "S-071"),
    ("M-024", "S-042", "P-015", "S-042", "E-012", "M-016", "S-145", "M-020", "PR-006", "S-042", "E-051",
     "P-036", "MJ-003", "S-042", "S-029", "S-042", "S-029", "S-042", "S-029", "S-042", "S-029", "S-042",
     "S-029", "S-042", "S-029", "S-042", "S-029", "S-042", "S-029", "S-042", "S-029", "S-042"),
)


@pytest.mark.slow
@pytest.mark.parametrize("levels", [("normal", "normal"), ("normal", "dummy"), ("dummy", "normal")])
@pytest.mark.parametrize("seed", [1, 2, 3])
def test_npc_selfplay_with_ex060(levels, seed):
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
