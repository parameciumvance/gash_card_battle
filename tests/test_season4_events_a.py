"""第 4 賽季事件卡第 a 批(card-effects「第 4 賽季事件卡第 a 批」、game-engine「魔物層級的搭檔效果限制」,
season4-events-a)。依日文效果文。
"""
import pytest

from gash.api.views import snapshot
from gash.engine.cards import pending_cards
from gash.engine.engine import IllegalCommand, submit
from tests.test_level2 import DB, HEADS, TAILS, Rng, book, mk, to_battle
from tests.test_level3 import ability, add_slot, battle_in, choose, code, pass_effects
from tests.test_opponent_book_search import end_review

BATCH = ("Ex-071", "Ex-072", "E-050", "Ex-073", "Ex-100", "E-051", "E-054", "PR-013", "Ex-101")


def setup(b0, b1=("M-001",), coins=(), mp=10):
    g, _ = mk(book(*b0), book(*b1))
    st = g.state
    g.rng = Rng(*coins)
    st.players[0].mp, st.players[1].mp = mp, mp
    to_battle(g, 0)
    return g


def use(g, page=2, player=0):
    return submit(g, {"type": "use_book_card", "player": player, "page": page})


def respond_pass(g):
    if g.state.pending is None and g.state.action_player == 1:
        submit(g, {"type": "pass", "player": 1})


def options(g):
    return [o["value"] for o in g.state.pending.options]


def test_batch_open():
    assert not set(BATCH) & pending_cards()


# ---------------------------------------------------------------- Ex-071

def _ex071():
    g = setup(("M-001", "Ex-071", "S-001"), ("M-001",))
    st = g.state
    a = st.players[1].slots[0]
    b = add_slot(g, 1, "M-017", partner="P-009")
    a.partner = "P-016"
    use(g)
    assert st.pending.kind == "pick_opponent_mamodo" and st.pending.player == 0
    choose(g, a.uid)
    respond_pass(g)
    return g, a, b


def test_ex071_blocks_chosen_mamodo_partner_only():
    # このターン中、相手はその魔物の「魔物の効果」や、その魔物につけられたパートナーの効果を使えない
    g, a, b = _ex071()
    st = g.state
    battle_in(g, 3)
    submit(g, {"type": "no_defense", "player": 1})
    submit(g, {"type": "pass", "player": 0})
    assert code(g, ability(1, a, zone="partner")) == "ability.partner_restricted"
    submit(g, ability(1, b, zone="partner"))                                 # 其他魔物的搭檔照常
    assert st.battle.attack_negated


def test_ex071_partner_attached_later_also_blocked():
    # 效果使用後才裝上的搭檔也被擋(常駐效果:P-020)
    g, a, _ = _ex071()
    a.partner = "P-020"
    view = next(s for s in snapshot(g, 0)["players"][1]["slots"] if s["uid"] == a.uid)
    assert {"card": "P-020", "by": ["Ex-071"]} in view["blocked_effects"]


def test_ex071_blocks_mamodo_effect_not_spells():
    g, a, _ = _ex071()
    from gash.engine.engine import mamodo_effect_block, spell_block
    assert mamodo_effect_block(g, 1, a) == "mamodo_locked"
    assert spell_block(g, 1, a) is None                                      # 「術」は封じない(E-024 との違い)


def test_ex071_no_opponent_mamodo_unusable():
    g = setup(("M-001", "Ex-071"))
    g.state.players[1].slots.clear()
    assert code(g, {"type": "use_book_card", "player": 0, "page": 2}) == "event.condition"


# ---------------------------------------------------------------- Ex-072

def _ex072(*opp):
    pages = ["S-029"] * 31
    for p, n in opp:
        pages[p - 2] = n
    return setup(("M-001", "Ex-072"), ("M-001", *pages))


def test_ex072_discards_up_to_two_dartagnan():
    # 相手の魔本を見て、好きなページから「プロフェッサー・ダルタニアン」2枚までを選び、捨て札にする
    g = _ex072((5, "E-024"), (9, "E-024"), (12, "E-024"))
    st = g.state
    use(g)
    assert st.pending.kind == "pick_opponent_book_card" and st.pending.player == 0
    assert options(g) == [5, 9, 12, None]
    choose(g, 5)
    assert options(g) == [9, 12, None]
    choose(g, 12)
    assert st.pending is None and st.players[1].discard.count("E-024") == 2 and st.players[1].book[8] == "E-024"


def test_ex072_may_choose_none():
    g = _ex072((5, "E-024"))
    use(g)
    choose(g, None)
    assert g.state.pending is None and g.state.players[1].discard == []


def test_ex072_none_in_book_review_only():
    g = _ex072((5, "E-003"))
    use(g)
    end_review(g, 0)


# ---------------------------------------------------------------- E-050

def test_e050_same_name_as_opponent_discard():
    # 相手の捨て札にあるカードと同じカード名のカード1枚を選び、捨て札にする;( )内が異なっても同名
    pages = ["S-029"] * 31
    pages[5 - 2], pages[7 - 2], pages[8 - 2] = "E-030", "M-045", "E-003"
    g = setup(("M-001", "E-050"), ("M-001", *pages))
    st = g.state
    st.players[1].discard += ["E-030", "M-046"]                             # ００Ｆ～鉄のフォルゴレ～、ウマゴン（シュドルク形態）
    use(g)
    assert st.pending.kind == "pick_opponent_book_card" and options(g) == [5, 7]
    with pytest.raises(IllegalCommand) as exc:
        choose(g, 8)
    assert exc.value.code == "choose.invalid" and st.pending is not None
    choose(g, 7)
    assert "M-045" in st.players[1].discard and st.pending is None


def test_e050_no_match_review_only():
    g = setup(("M-001", "E-050"))
    use(g)
    end_review(g, 0)


def test_card_name_key():
    from gash.engine.effects.primitives import card_name_key
    assert card_name_key("ウマゴン（シュドルク形態）") == card_name_key("ウマゴン") == card_name_key("ウマゴン(X)")
    assert card_name_key("キャンチョメ＆ティオ") != card_name_key("キャンチョメ")


# ---------------------------------------------------------------- Ex-073 / Ex-100

def test_ex073_mp_per_discarded_mamodo():
    # 自分の捨て札の魔物カードの枚数×1、自分のMPをふやす
    g = setup(("M-001", "Ex-073"))
    st = g.state
    st.players[0].discard += ["M-001", "M-002", "S-001", "M-045", "P-001"]
    use(g)
    assert st.players[0].mp == 10 + 3


@pytest.mark.parametrize("coins, gain", [((HEADS, HEADS), 5), ((HEADS, TAILS), 0), ((TAILS, TAILS), 0)])
def test_ex100_two_heads_five_mp(coins, gain):
    # コインを2回投げる。オモテが2回出れば、自分のMPを5ふやす
    g = setup(("M-001", "Ex-100"), coins=coins)
    use(g)
    assert g.state.players[0].mp == 10 + gain


# ---------------------------------------------------------------- E-051

def _e051():
    pages = ["S-029"] * 31
    pages[5 - 2], pages[6 - 2] = "P-001", "P-012"
    g = setup(("M-001", "E-051", *pages[1:]))
    add_slot(g, 0, "M-017")
    return g


def test_e051_any_number_of_partners():
    # 自分の魔本の好きなページから、パートナーカードを何枚でも選び、場に出す
    g = _e051()
    st = g.state
    use(g)
    assert st.pending.kind == "pick_partner_in_own_book" and options(g) == [5, 6, None]
    choose(g, 5)
    assert st.pending.kind == "pick_partner_in_own_book" and options(g) == [6, None]
    choose(g, 6)
    assert st.pending is None
    assert [s.partner for s in st.players[0].slots] == ["P-001", "P-012"]


def test_e051_stop_after_one():
    g = _e051()
    st = g.state
    use(g)
    choose(g, 6)
    choose(g, None)
    assert st.pending is None and [s.partner for s in st.players[0].slots] == [None, "P-012"]
    assert st.players[0].book[4] == "P-001"


def test_e051_no_partner_unusable():
    g = setup(("M-001", "E-051"))
    assert code(g, {"type": "use_book_card", "player": 0, "page": 2}) == "event.condition"


# ---------------------------------------------------------------- E-054

def test_e054_discards_mamodo_with_discard_cost_effect():
    # 相手の「このカードを捨て札にする→」効果を持つ魔物1体を選び、捨て札にする
    g = setup(("M-001", "E-054"), ("M-001",))
    st = g.state
    zeon = add_slot(g, 1, "M-059")                                           # 啟動效果(捨て札)
    gash = add_slot(g, 1, "M-032")                                           # 干擾(捨て札)
    use(g)
    assert st.pending.kind == "pick_opponent_mamodo" and sorted(options(g)) == sorted([zeon.uid, gash.uid])
    with pytest.raises(IllegalCommand) as exc:
        choose(g, st.players[1].slots[0].uid)                                # M-001:沒有捨て札效果
    assert exc.value.code == "choose.invalid"
    choose(g, zeon.uid)
    assert zeon not in st.players[1].slots and "M-059" in st.players[1].discard


def test_e054_no_target_unusable():
    g = setup(("M-001", "E-054"), ("M-001",))
    assert code(g, {"type": "use_book_card", "player": 0, "page": 2}) == "event.condition"


# ---------------------------------------------------------------- PR-013

def test_pr013_opponent_chooses_mine_then_i_choose_theirs():
    # 相手は、自分の魔本を見て、今のページより後ろのイベントカード1枚を選び、捨て札にする。
    # そうしたなら、相手の魔本を見て、今のページより後ろのイベントカード1枚を選び、捨て札にする
    mine = ["S-029"] * 30
    mine[3 - 3], mine[8 - 3], mine[9 - 3] = "E-003", "E-008", "E-030"
    theirs = ["S-029"] * 31
    theirs[3 - 2], theirs[10 - 2] = "E-030", "E-003"
    g = setup(("M-001", "PR-013", *mine), ("M-001", *theirs))
    st = g.state
    use(g)
    assert st.pending.kind == "pick_opponent_book_card" and st.pending.player == 1
    assert options(g) == [8, 9]                                               # 第 3 頁是今のページ
    choose(g, 9)
    assert "E-030" in st.players[0].discard
    assert st.pending.player == 0 and options(g) == [10]
    choose(g, 10)
    assert "E-003" in st.players[1].discard and st.pending is None


def test_pr013_no_event_after_current_page_nothing():
    theirs = ["S-029"] * 31
    theirs[10 - 2] = "E-003"
    g = setup(("M-001", "PR-013"), ("M-001", *theirs))
    st = g.state
    use(g)
    assert st.pending.kind == "end_book_review" and st.pending.player == 1
    submit(g, {"type": "choose", "player": 1, "value": None})
    assert st.pending is None and st.players[1].discard == []


# ---------------------------------------------------------------- Ex-101

def test_ex101_half_of_battle_phase_mp_lost():
    # このターンのエンドフェイズに、このターンのバトルフェイズ中にへった、自分のMPの数の半分(端数切り捨て)だけふやす
    g = setup(("M-001", "Ex-101", "S-005"))
    st = g.state
    use(g)                                                                   # 費用 2
    respond_pass(g)
    battle_in(g, 3)                                                          # S-005 費用 6
    submit(g, {"type": "no_defense", "player": 1})
    pass_effects(g)
    from tests.test_level3 import finish_damage
    finish_damage(g)
    lost = DB["Ex-101"].cost + DB["S-005"].cost
    while st.turn_player == 0:
        submit(g, {"type": "pass", "player": st.action_player})
    gains = [e for e in g.events if e["type"] == "mp_changed" and e.get("reason") == "Ex-101" and e["delta"] > 0]
    assert [e["delta"] for e in gains] == [lost // 2]


# ---------------------------------------------------------------- NPC 自我對戰

SELFPLAY_BOOKS = (
    ("M-001", "Ex-071", "Ex-072", "E-050", "Ex-073", "Ex-100", "E-051", "P-001", "E-054", "PR-013", "Ex-101",
     "S-001", "M-017", "P-012", "S-009", "S-005", "M-002", "S-003", "E-003", "S-022", "S-001", "M-003",
     "S-004", "S-001", "S-002", "S-003", "M-005", "S-010", "S-001", "S-002", "S-003", "E-030"),
    ("M-001", "S-001", "E-024", "M-059", "M-034", "P-016", "S-025", "E-024", "S-005", "P-017", "E-003",
     "S-022", "M-002", "S-003", "M-003", "S-004", "S-002", "M-005", "S-010", "S-001", "S-002", "S-003",
     "E-030", "S-002", "S-003", "S-001", "S-002", "S-003", "E-008", "S-002", "S-003", "S-008"),
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
