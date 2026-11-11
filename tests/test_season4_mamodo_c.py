"""第 4 賽季魔物與搭檔第 3 批(card-effects「第 4 賽季魔物與搭檔第 3 批」;game-engine「以效果結束戰鬥階段」
「被對手的效果翻頁的紀錄」,season4-mamodo-c)。依日文效果文。
"""
import pytest

from gash.engine.cards import pending_cards
from gash.engine.engine import submit
from gash.engine.state import BATTLE
from tests.test_level2 import book, mk, to_battle
from tests.test_level3 import ability, add_slot, choose, code, finish_damage, pass_effects
from tests.test_season4_mamodo_b import end_turn

BATCH = ("M-073", "M-074", "S-135", "M-077", "M-084")


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


# ---------------------------------------------------------------- M-073

def m073_game():
    """玩家 1 的 M-073;第 9 頁マ・セシルド(S-024)、第 3 頁セウシル(S-022)。玩家 0 pass 後玩家 1 使用 M-073。"""
    g = setup(("M-001", "S-001"),
              ("M-073", "S-029", "S-022", "S-029", "S-029", "S-029", "S-029", "S-029", "S-024"))
    submit(g, {"type": "pass", "player": 0})
    submit(g, ability(1, g.state.players[1].slots[0]))
    return g


def test_m073_defend_from_other_page_then_discard():
    # 【スタンバイ】このターン中に1回、自分の魔本の最後のページ以外の「ティオ」の術1つを、防御で使うことができる。
    # そうしたなら、そのバトル後に、使った術カードを捨て札にする
    g = m073_game()
    st = g.state
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    submit(g, {"type": "declare_defense", "player": 1, "page": 9})
    assert st.battle.defense_spell == "S-024"
    pass_effects(g)
    finish_damage(g)
    assert st.battle is None
    assert 9 in st.players[1].consumed_pages and "S-024" in st.players[1].discard


def test_m073_open_page_defense_keeps_standby():
    # 翻開頁的戰術照一般規則(使用者決定):不消耗待命、不棄掉
    g = m073_game()
    st = g.state
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    submit(g, {"type": "declare_defense", "player": 1, "page": 3})
    pass_effects(g)
    finish_damage(g)
    assert 3 not in st.players[1].consumed_pages and "S-022" not in st.players[1].discard
    assert any(sb.kind == "spell_any_page" and sb.source == "M-073" for sb in st.standby)


def test_m073_not_for_attack():
    from gash.engine.engine import _spell_any_page_standby
    g = m073_game()
    assert _spell_any_page_standby(g, 1, 9, use="attack") is None
    assert _spell_any_page_standby(g, 1, 9, use="defense") is not None


def test_m073_not_last_page():
    from gash.engine.engine import _spell_any_page_standby
    g = m073_game()
    st = g.state
    st.players[1].book[31] = "S-024"
    assert _spell_any_page_standby(g, 1, 32, use="defense") is None


# ---------------------------------------------------------------- M-074 / S-135

def test_s135_stacks_m074_and_guards_partner():
    # 自分の魔本の好きなページから「ウマゴン(ゴウ・シュドルク形態)」1枚を選び、自分の場の「ウマゴン」の上に重ねる
    from gash.engine.effects.primitives import partner_discard_guarded
    g = setup(("M-045", "S-135", "S-029", "S-029", "S-029", "S-029", "S-029", "M-074"))
    st = g.state
    uma = st.players[0].slots[0]
    use(g)
    if st.pending is not None:
        choose(g, 8)
    assert uma.stack == ["M-045", "M-074"]
    uma.partner = "P-001"
    assert partner_discard_guarded(g, 0, uma)


def test_m074_cannot_be_played_directly():
    from gash.engine.engine import play_block
    g = setup(("M-045", "M-074"))
    assert play_block(g, 0, "M-074") is not None


def test_s135_needs_m074_in_book():
    g = setup(("M-045", "S-135"))
    assert code(g, {"type": "use_book_card", "player": 0, "page": 2}) == "spell.condition"


# ---------------------------------------------------------------- M-077

def test_m077_ends_battle_phase_and_skips_flip():
    # このバトルフェイズを終了する。このターンのエンドフェイズは、効果の処理はおこなうが、
    # 「ページをめくってMPを2ふやす」処理はおこなわない
    g = setup(("M-077",))
    st = g.state
    pos, mp = st.players[0].pos, st.players[0].mp
    submit(g, ability(0, st.players[0].slots[0]))
    assert st.turn_player == 1                                            # 戰鬥階段結束、回合交替
    assert st.players[0].pos == pos and st.players[0].mp == mp


def test_m077_on_opponent_turn_skips_opponent_flip():
    g = setup(("M-001",), ("M-077",))
    st = g.state
    pos, mp = st.players[0].pos, st.players[0].mp
    submit(g, {"type": "pass", "player": 0})
    submit(g, ability(1, st.players[1].slots[0]))
    assert st.turn_player == 1
    assert st.players[0].pos == pos and st.players[0].mp == mp


def test_m077_jammer_negates_and_battle_phase_continues():
    # この効果に対してジャマー効果を使うことはできる
    g = setup(("M-077",), ("M-026",))
    st = g.state
    submit(g, ability(0, st.players[0].slots[0]))
    assert st.pending.kind == "jammer_negate" and st.pending.player == 1
    choose(g, "M-026")
    assert st.phase == BATTLE and st.turn_player == 0
    assert not any(sb.kind in ("end_battle_phase", "skip_end_flip") for sb in st.standby)


def test_m077_jammer_declined_ends_battle_phase():
    g = setup(("M-077",), ("M-026",))
    st = g.state
    submit(g, ability(0, st.players[0].slots[0]))
    choose(g, None)
    assert st.turn_player == 1


def test_m077_once_per_game():
    g = setup(("M-077",))
    st = g.state
    submit(g, ability(0, st.players[0].slots[0]))
    to_battle(g, 1)                                                       # 玩家 1 的回合
    end_turn(g)
    assert st.turn_player == 0 and st.phase == BATTLE
    assert code(g, ability(0, st.players[0].slots[0])) == "ability.per_game"


def test_m030_still_only_own_turn():
    # M-030 維持只在自己回合有效(使用者決定)
    from gash.engine.state import Standby
    g = setup()
    st = g.state
    st.standby.append(Standby(kind="skip_end_flip", source="M-030", owner=1, created_turn=st.turn_no))
    pos = st.players[0].pos
    end_turn(g)
    assert st.players[0].pos == pos + 2


# ---------------------------------------------------------------- M-084

def test_m084_turns_opponent_pages_by_count():
    # このターン中に、ダメージ以外の相手の効果で自分の魔本がめくられていれば使える。めくられた枚数の合計、相手の魔本をめくる
    g = setup(("M-001", "E-014"), ("M-084",))
    st = g.state
    use(g)                                                                # 玩家 1 的魔書翻 1 張
    if st.pending is not None:
        choose(g, st.pending.options[0]["value"])
    assert st.players[1].pages_turned_by_opponent == 1
    pos0 = st.players[0].pos
    submit(g, ability(1, st.players[1].slots[0]))
    assert st.players[0].pos == pos0 + 2


def test_m084_needs_opponent_effect_flip():
    g = setup(("M-001",), ("M-084",))
    st = g.state
    submit(g, {"type": "pass", "player": 0})
    assert code(g, ability(1, st.players[1].slots[0])) == "ability.condition"


def test_m084_own_effect_and_damage_not_counted():
    g = setup(("M-084", "E-005", "S-001"))
    st = g.state
    st.players[0].pages_turned_by_opponent = 0
    from gash.engine.effects.primitives import own_book_turn_effect, turn_pages
    own_book_turn_effect(g, [], 0, 1, "E-005")
    assert st.players[0].pages_turned_by_opponent == 0
    turn_pages(g, [], 0, 1, "S-001")                                      # 使用者不明(例如規則)不算
    assert st.players[0].pages_turned_by_opponent == 0


def test_pages_turned_by_opponent_resets_each_turn():
    g = setup(("M-001", "E-014"), ("M-084",))
    st = g.state
    use(g)
    if st.pending is not None:
        choose(g, st.pending.options[0]["value"])
    end_turn(g)
    assert st.players[1].pages_turned_by_opponent == 0


# ---------------------------------------------------------------- 自我對戰

SELFPLAY_BOOKS = (
    ("M-073", "S-022", "M-084", "S-024", "M-045", "S-135", "S-022", "M-074", "S-061", "S-022", "S-024",
     "M-077", "S-022", "S-024", "S-061", "S-022", "S-024", "S-022", "S-024", "S-022", "S-024", "S-022",
     "S-024", "S-022", "S-024", "S-022", "S-024", "S-022", "S-024", "S-022", "S-024", "S-022"),
    ("M-001", "S-001", "E-014", "S-002", "M-077", "S-003", "E-014", "M-084", "S-001", "E-014", "S-003",
     "E-005", "S-001", "E-014", "S-003", "S-001", "S-002", "S-003", "S-001", "S-002", "S-003", "S-001",
     "S-002", "S-003", "S-001", "S-002", "S-003", "S-001", "S-002", "S-003", "S-001", "S-008"),
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
