"""第 3 賽季效果第 3 批:從魔書放出、翻對手魔書、從魔書棄掉(card-effects「第 3 賽季卡片的開放」)。
依日文效果文逐卡驗證可觀察的結果。

放出 E-044、Ex-032、Ex-046、M-062、P-036;翻對手魔書 Ex-022、Ex-045、M-060、M-063;
從魔書棄掉 E-045、Ex-003;回翻 PR-007。
"""

import pytest

from gash.engine.cards import pending_cards
from gash.engine.engine import submit
from tests.test_level2 import book, mk, to_battle
from tests.test_level3 import ability, add_slot, choose, code, use_event

BATCH = ("E-044", "E-045", "Ex-003", "Ex-022", "Ex-032", "Ex-045", "Ex-046", "M-060", "M-062", "M-063",
         "P-036", "PR-007")


def values(g):
    return [o["value"] for o in g.state.pending.options]


def opp_turn_battle(g):
    """玩家 0 的回合結束,進入玩家 1 的戰鬥階段。"""
    submit(g, {"type": "pass", "player": 0})
    submit(g, {"type": "pass", "player": 1})
    to_battle(g, 1)


# ---------------------------------------------------------------- 開放

def test_batch_size():
    assert len(set(BATCH)) == 12


def test_batch_cards_are_open():
    assert not set(BATCH) & pending_cards()


# ---------------------------------------------------------------- E-044

def _e044(*pages):
    """E-044 是對手回合的事件卡:玩家 0 結束回合(結束階段翻到第 4 頁),在玩家 1 的戰鬥階段使用。"""
    g, _ = mk(book("M-001", "S-029", "S-029", "E-044", *pages), book("M-001"))
    st = g.state
    to_battle(g, 0)
    opp_turn_battle(g)
    submit(g, {"type": "pass", "player": 1})
    assert st.players[0].pos == 4
    st.players[0].mp = 1
    return g


def test_e044_deploys_mamodo_from_current_page():
    # 自分の魔本の今のページの、魔物カードかパートナーカード1枚を選び、場に出す。
    g = _e044("M-004", "M-008")
    st = g.state
    use_event(g, 4)
    assert [s.top for s in st.players[0].slots] == ["M-001", "M-004"]          # 第 6 頁不是目前的頁
    assert st.players[0].mp == 0


def test_e044_partner_chooses_mamodo():
    g = _e044("P-001")
    st = g.state
    other = add_slot(g, 0, "M-002")
    use_event(g, 4)
    assert st.pending.player == 0 and set(values(g)) == {st.players[0].slots[0].uid, other.uid}
    choose(g, other.uid)
    assert other.partner == "P-001" and st.players[0].slots[0].partner is None


def test_e044_needs_card_on_current_page():
    g = _e044("S-029", "M-008")
    assert code(g, {"type": "use_book_card", "player": 0, "page": 4}) == "event.condition"


def test_e044_not_in_own_turn():
    g, _ = mk(book("M-001", "E-044", "M-004"), book("M-001"))
    g.state.players[0].mp = 1
    to_battle(g, 0)
    assert code(g, {"type": "use_book_card", "player": 0, "page": 2}) == "event.timing"


# ---------------------------------------------------------------- E-045

def test_e045_discards_card_with_restriction_effect():
    # 相手の魔本を見て、好きなページから、「術を使えない」「かばうことができない」「魔物の効果を使えない」
    # のどれかの効果を持つカード1枚を選び、捨て札にする。
    opp = ["M-001", "E-003", "S-029", "E-002", "P-026", "M-004"] + ["S-029"] * 25 + ["S-004"]
    g, _ = mk(book("M-001", "E-045"), opp)
    st = g.state
    st.players[0].mp = 2
    to_battle(g, 0)
    events = use_event(g)
    assert any(e["type"] == "book_revealed" and e["viewer"] == 0 for e in events)
    assert st.pending.player == 0 and values(g) == [4, 5]                      # 最後一頁的 S-004 除外
    choose(g, 5)
    assert "P-026" in st.players[1].discard and 5 in st.players[1].consumed_pages


def test_e045_usable_without_target():
    g, _ = mk(book("M-001", "E-045"), ["M-001"] + ["S-029"] * 30 + ["S-004"])
    st = g.state
    st.players[0].mp = 2
    to_battle(g, 0)
    use_event(g)
    assert st.pending.kind == "end_book_review" and st.pending.player == 0
    choose(g, None)
    assert st.players[1].discard == [] and st.players[0].events_used_this_turn == 1


# ---------------------------------------------------------------- Ex-003

def test_ex003_discards_any_card_on_opponent_current_page_once_per_game():
    # 《工作》使用を宣言する→相手の魔本の今のページを見て、好きなカード1枚を選び、捨て札にする。ゲーム中に1回だけ使える。
    g, _ = mk(book("Ex-003"), book("M-001", "E-003", "M-004"))
    st = g.state
    me = st.players[0].slots[0]
    to_battle(g, 0)
    events = submit(g, ability(0, me))
    assert any(e["type"] == "pages_peeked" and e["viewer"] == 0 for e in events)
    assert st.pending.player == 0 and values(g) == [2, 3]
    choose(g, 3)
    assert "M-004" in st.players[1].discard
    submit(g, {"type": "pass", "player": 1})
    assert code(g, ability(0, me)) == "ability.used"
    st.players[0].used_abilities.clear()
    assert code(g, ability(0, me)) == "ability.per_game"


def test_ex003_usable_in_opponent_turn():
    g, _ = mk(book("M-001"), book("Ex-003"))
    st = g.state
    to_battle(g, 0)
    submit(g, {"type": "pass", "player": 0})
    submit(g, ability(1, st.players[1].slots[0]))
    assert st.pending.player == 1


# ---------------------------------------------------------------- Ex-022

def test_ex022_turns_opponent_then_own_book():
    # 相手の魔本を1枚めくる。そうしたなら、自分の魔本を1枚めくる。
    # このターン中、自分は「自分の魔本をめくる」効果を合計1回しか使えない。
    g, _ = mk(book("M-001", "Ex-022"), book("M-001"))
    st = g.state
    st.players[0].mp = 3
    st.players[0].slots[0].partner = "P-010"
    to_battle(g, 0)
    use_event(g)
    assert st.players[1].pos == 4 and st.players[0].pos == 4
    submit(g, {"type": "pass", "player": 1})
    assert code(g, ability(0, st.players[0].slots[0], zone="partner")) == "ability.condition"   # P-010:合計 1 回已用掉


def test_ex022_only_opponent_when_already_limited():
    g, _ = mk(book("M-001", "S-029", "S-029", "Ex-022"), book("M-001"))
    st = g.state
    st.players[0].mp = 3
    st.players[0].slots[0].partner = "P-010"
    to_battle(g, 0)
    submit(g, ability(0, st.players[0].slots[0], zone="partner"))                # P-010:翻到第 4 頁
    submit(g, {"type": "pass", "player": 1})
    events = use_event(g, 4)
    assert st.players[1].pos == 4 and st.players[0].pos == 4
    assert [e["source"] for e in events if e["type"] == "page_turn_restricted"] == ["Ex-022"]


# ---------------------------------------------------------------- Ex-032

def test_ex032_attaches_nazonazo_from_book():
    # 《本当?》MPを2へらす→自分の魔本の好きなページから、パートナーカード「ナゾナゾ博士」1枚を選び、場に出す。
    g, _ = mk(book("Ex-032", "S-029", "S-029", "S-029", "S-029", "S-029", "Ex-037"), book("M-001"))
    st = g.state
    kid = st.players[0].slots[0]
    st.players[0].mp = 2
    to_battle(g, 0)
    submit(g, ability(0, kid))
    assert kid.partner == "Ex-037" and 7 in st.players[0].consumed_pages and st.players[0].mp == 0


def test_ex032_needs_nazonazo_in_book():
    g, _ = mk(book("Ex-032"), book("M-001"))
    g.state.players[0].mp = 2
    to_battle(g, 0)
    assert code(g, ability(0, g.state.players[0].slots[0])) == "ability.condition"


# ---------------------------------------------------------------- Ex-045

@pytest.mark.parametrize("opp_page2, turned", [("E-003", True), ("S-029", False)])
def test_ex045_turns_opponent_book_if_event_on_current_page(opp_page2, turned):
    # 相手の魔本の今のページを見る。その見開きにイベントカードがあれば、相手の魔本を1枚めくる。
    g, _ = mk(book("M-001", "Ex-045"), book("M-001", opp_page2))
    st = g.state
    st.players[0].mp = 2
    to_battle(g, 0)
    events = use_event(g)
    assert any(e["type"] == "pages_peeked" and e["viewer"] == 0 for e in events)
    assert st.players[1].pos == (4 if turned else 2)


# ---------------------------------------------------------------- Ex-046

def test_ex046_deploys_two_mamodo_in_order():
    # 自分の魔本の好きなページから、魔物カード2枚を選び、場に出す(2枚出さなければならない)。
    g, _ = mk(book("M-001", "Ex-046", "S-029", "S-029", "M-004", "M-002", "M-008"), book("M-001"))
    st = g.state
    st.players[0].mp = 4
    to_battle(g, 0)
    use_event(g)
    assert st.pending.player == 0 and values(g) == [5, 7]                      # M-002 與場上同名
    choose(g, 5)
    assert [s.top for s in st.players[0].slots] == ["M-001", "M-004", "M-008"]


def test_ex046_needs_two_free_slots():
    g, _ = mk(book("M-001", "Ex-046", "S-029", "S-029", "M-004", "M-008"), book("M-001"))
    st = g.state
    st.players[0].mp = 4
    to_battle(g, 0)
    add_slot(g, 0, "M-050")
    assert code(g, {"type": "use_book_card", "player": 0, "page": 2}) == "event.condition"


def test_ex046_excludes_stacking_mamodo():
    g, _ = mk(book("M-006", "Ex-046", "S-029", "S-029", "M-004", "M-007"), book("M-001"))
    g.state.players[0].mp = 4
    to_battle(g, 0)
    assert code(g, {"type": "use_book_card", "player": 0, "page": 2}) == "event.condition"


def test_ex046_needs_two_different_names():
    g, _ = mk(book("M-001", "Ex-046", "S-029", "S-029", "M-002", "M-003"), book("M-001"))
    g.state.players[0].mp = 4
    to_battle(g, 0)
    assert code(g, {"type": "use_book_card", "player": 0, "page": 2}) == "event.condition"


def test_ex046_first_choice_must_leave_a_second():
    # M-004 兩張同名:選了其中一張就沒有第 2 張,只有 M-008 能當第 1 張以外的組合
    g, _ = mk(book("M-001", "Ex-046", "S-029", "S-029", "M-004", "M-004"), book("M-001"))
    g.state.players[0].mp = 4
    to_battle(g, 0)
    assert code(g, {"type": "use_book_card", "player": 0, "page": 2}) == "event.condition"


# ---------------------------------------------------------------- M-060

def test_m060_turns_opponent_book_in_own_battle_phase():
    # 《メルメルメ～》このカードを捨て札にする→自分のバトルフェイズに、相手の魔本を1枚めくる。
    g, _ = mk(book("M-001"), book("M-001"))
    st = g.state
    to_battle(g, 0)
    uma = add_slot(g, 0, "M-060")
    submit(g, ability(0, uma))
    assert st.players[1].pos == 4 and "M-060" in st.players[0].discard


def test_m060_not_in_opponent_turn():
    g, _ = mk(book("M-001"), book("M-001"))
    st = g.state
    uma = add_slot(g, 0, "M-060")
    to_battle(g, 0)
    opp_turn_battle(g)
    submit(g, {"type": "pass", "player": 1})
    assert code(g, ability(0, uma)) == "ability.timing"


# ---------------------------------------------------------------- M-062

def _m062(*extra_pages, mp=2):
    g, _ = mk(book("M-062", "S-029", "S-029", "S-029", *extra_pages), book("M-001"))
    g.state.players[0].mp = mp
    to_battle(g, 0)
    return g


def test_m062_discard_only():
    # 《出会い》MPを2へらす→自分のバトルフェイズに、次の効果の、片方または両方を、この順で使う。
    # ●自分の場の魔物1体を選び、捨て札にする。●自分の魔本の好きなページから、魔物カード1枚を選び、場に出す。
    g = _m062("M-008")
    st = g.state
    gash = st.players[0].slots[0]
    other = add_slot(g, 0, "M-004")
    submit(g, ability(0, gash))
    assert st.pending.player == 0 and set(values(g)) == {gash.uid, other.uid, None}
    choose(g, other.uid)
    assert st.pending.player == 0 and values(g) == [5, None]
    choose(g, None)
    assert [s.top for s in st.players[0].slots] == ["M-062"] and "M-004" in st.players[0].discard
    assert st.players[0].mp == 0


def test_m062_deploy_only():
    g = _m062("M-008", "M-050")
    st = g.state
    gash = st.players[0].slots[0]
    add_slot(g, 0, "M-004")
    submit(g, ability(0, gash))
    choose(g, None)
    assert st.pending.player == 0 and values(g) == [5, 6]                      # 不棄掉時必須放出
    choose(g, 5)
    assert [s.top for s in st.players[0].slots] == ["M-062", "M-004", "M-008"]


def test_m062_discard_only_mamodo_then_must_deploy():
    g = _m062("M-008", "M-050")
    st = g.state
    gash = st.players[0].slots[0]
    submit(g, ability(0, gash))
    assert values(g) == [gash.uid, None]
    choose(g, gash.uid)
    assert st.pending.player == 0 and values(g) == [5, 6]                      # 場上沒有魔物:必須放出
    choose(g, 5)
    assert [s.top for s in st.players[0].slots] == ["M-008"] and "M-062" in st.players[0].discard


def test_m062_cannot_discard_only_mamodo_without_deploy():
    g = _m062()
    assert code(g, ability(0, g.state.players[0].slots[0])) == "ability.condition"


def test_m062_full_field_must_discard_first():
    g = _m062("M-008")
    st = g.state
    gash = st.players[0].slots[0]
    add_slot(g, 0, "M-004")
    add_slot(g, 0, "M-050")
    submit(g, ability(0, gash))
    assert None not in values(g)                                                # 放不出,必須棄掉
    choose(g, gash.uid)
    assert st.pending.player == 0 and values(g) == [5, None]                   # 棄掉後有空位,可選擇放出
    choose(g, None)
    assert len(st.players[0].slots) == 2


def test_m062_not_in_opponent_turn():
    g = _m062("M-008")
    opp_turn_battle(g)
    submit(g, {"type": "pass", "player": 1})
    assert code(g, ability(0, g.state.players[0].slots[0])) == "ability.timing"


# ---------------------------------------------------------------- M-063

def test_m063_turns_opponent_book_on_last_page():
    # 《非情の勝利》使用を宣言する→この効果は、相手の魔本が最後のページのとき使える。相手の魔本を1枚めくる。
    g, _ = mk(book("M-063"), book("M-001"))
    st = g.state
    to_battle(g, 0)
    st.players[1].pos = 32
    submit(g, ability(0, st.players[0].slots[0]))
    assert st.phase == "game_over" and st.winner == 0


def test_m063_needs_opponent_last_page():
    g, _ = mk(book("M-063"), book("M-001"))
    to_battle(g, 0)
    g.state.players[1].pos = 30
    assert code(g, ability(0, g.state.players[0].slots[0])) == "ability.condition"


# ---------------------------------------------------------------- P-036

def test_p036_puts_partner_from_book_judged_after_discard():
    # 《戦う友》このカードを捨て札にする→自分の魔本の好きなページから、パートナーカード1枚を選び、場に出す。
    g, _ = mk(book("M-001", "S-029", "S-029", "S-029", "P-010"), book("M-001"))
    st = g.state
    gash = st.players[0].slots[0]
    gash.partner = "P-036"
    to_battle(g, 0)
    submit(g, ability(0, gash, zone="partner"))
    assert gash.partner == "P-010" and "P-036" in st.players[0].discard and 5 in st.players[0].consumed_pages


def test_p036_needs_partner_in_book():
    g, _ = mk(book("M-001"), book("M-001"))
    gash = g.state.players[0].slots[0]
    gash.partner = "P-036"
    to_battle(g, 0)
    assert code(g, ability(0, gash, zone="partner")) == "ability.condition"


# ---------------------------------------------------------------- PR-007

def test_pr007_discards_itself_then_turns_back_two():
    # このカードを捨て札にする。そうしたなら、自分の魔本を2枚もどす。
    # このターン中、自分は「自分の魔本をもどす」効果を合計1回しか使えない。
    g, _ = mk(book("M-001", "S-029", "S-029", "S-029", "S-029", "PR-007"), book("M-001"))
    st = g.state
    st.players[0].mp = 2
    st.players[0].slots[0].partner = "P-018"
    to_battle(g, 0)
    st.players[0].pos = 6
    use_event(g, 6)
    assert "PR-007" in st.players[0].discard and 6 in st.players[0].consumed_pages
    assert st.players[0].pos == 2
    st.players[0].pos = 6
    submit(g, {"type": "pass", "player": 1})
    assert code(g, ability(0, st.players[0].slots[0], zone="partner")) == "ability.condition"   # P-018:合計 1 回已用掉


# ---------------------------------------------------------------- 每回合 1 次以卡號計(game-engine)

def test_same_number_replayed_cannot_use_again():
    g, _ = mk(book("M-001", "M-067"), book("M-001"))
    st = g.state
    to_battle(g, 0)
    um = add_slot(g, 0, "M-067")
    submit(g, ability(0, um))
    submit(g, {"type": "pass", "player": 1})
    submit(g, {"type": "play_card", "player": 0, "page": 2})
    again = next(s for s in st.players[0].slots if s.top == "M-067")
    submit(g, {"type": "pass", "player": 1})
    assert code(g, ability(0, again)) == "ability.used"


# ---------------------------------------------------------------- NPC 自我對戰

SELFPLAY_BOOKS = (
    ("M-062", "S-001", "E-044", "P-036", "M-060", "Ex-022", "Ex-045", "E-045", "PR-007", "S-002", "M-004",
     "P-010", "M-063", "S-029", "Ex-046", "M-008", "M-050", "S-001", "E-012", "M-005", "P-018", "S-002",
     "P-001", "S-029", "E-044", "Ex-046", "S-001", "M-001", "E-045", "S-002", "PR-007", "S-029"),
    ("M-063", "S-008", "Ex-003", "Ex-015", "Ex-032", "Ex-037", "Ex-044", "E-002", "P-026", "S-009", "M-060",
     "Ex-045", "Ex-022", "E-045", "M-062", "S-010", "E-044", "PR-007", "Ex-046", "M-050", "S-011", "P-036",
     "E-013", "S-004", "M-001", "S-001", "E-025", "S-002", "Ex-022", "S-029", "P-003", "S-034"),
)


def test_selfplay_books_cover_batch():
    assert all(len(b) == 32 for b in SELFPLAY_BOOKS)
    assert set(BATCH) <= set(SELFPLAY_BOOKS[0]) | set(SELFPLAY_BOOKS[1])


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
