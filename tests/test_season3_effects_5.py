"""第 3 賽季效果第 5 批:Ex-025(對手增加 MP 的效果之後)、M-065(對手使自己 MP 減少時的ジャマー)、
Ex-034(事件卡重新解決的ジャマー)。"""

import pytest

from gash.engine.engine import submit
from gash.engine.state import DUR_TURN, NO_PARTNER_EFFECTS
from tests.test_level2 import HEADS, TAILS, Rng, book, mk, to_battle
from tests.test_level3 import ability, add_slot, choose, code, events_of, restrict, use_event

BATCH = ["Ex-025", "Ex-034", "M-065"]


# ---------------------------------------------------------------- Ex-025

def _ex025():
    """玩家 0 第 2 頁 E-032(自分のMPを5ふやす)、第 3 頁 M-004;玩家 1 場上 Ex-025。"""
    g, _ = mk(book("M-001", "E-032", "M-004"), book("Ex-025"))
    st = g.state
    st.players[0].mp, st.players[1].mp = 5, 2
    to_battle(g, 0)
    return g


def test_ex025_right_after_opponent_mp_gain():
    # 《ブリ大好き》使用を宣言する→この効果は、相手が相手のMPをふやす効果を使った直後に使う。その効果でふえたMPと同じ数だけ、自分のMPをふやす
    g = _ex025()
    st = g.state
    use_event(g, 2)
    submit(g, ability(1, st.players[1].slots[0]))
    assert st.players[1].mp == 2 + 5


def test_ex025_not_after_another_action():
    g = _ex025()
    st = g.state
    use_event(g, 2)
    submit(g, {"type": "pass", "player": 1})
    submit(g, {"type": "play_card", "player": 0, "page": 3})      # 玩家 0 再行動(放出魔物)
    assert code(g, ability(1, st.players[1].slots[0])) == "ability.condition"


def test_ex025_not_without_opponent_gain():
    g = _ex025()
    st = g.state
    st.players[0].book[1] = "E-038"
    use_event(g, 2)                                                # E-038:結束階段才增加
    assert code(g, ability(1, st.players[1].slots[0])) == "ability.condition"


# ---------------------------------------------------------------- M-065

def _m065(*coins, extra_book=()):
    """玩家 0 第 2 頁 E-018(相手のMPを4へらす);玩家 1 場上 M-065。"""
    g, _ = mk(book("M-001", "E-018", *extra_book), book("M-065"))
    st = g.state
    st.players[0].mp, st.players[1].mp = 10, 6
    g.rng = Rng(*coins)
    to_battle(g, 0)
    return g


def test_m065_heads_negates():
    # 《あげないよ》…コインを投げてオモテなら、相手が直前に使った、自分のMPがへる効果1つを無効にする
    g = _m065(HEADS)
    st = g.state
    use_event(g, 2)
    assert st.players[1].mp == 2
    assert st.pending.kind == "jammer_negate" and st.pending.player == 1 and st.pending.source == "M-065"
    choose(g, True)
    assert st.players[1].mp == 6 and st.players[0].mp == 10 - 2          # 對手的費用照算
    assert st.players[1].slots[0].top == "M-065"


def test_m065_tails_keeps():
    g = _m065(TAILS)
    st = g.state
    use_event(g, 2)
    choose(g, True)
    assert st.players[1].mp == 2


def test_m065_every_time_in_a_turn():
    # 相手が自分のMPがへる効果を使うごとに1回、1ターンに何回でも使える
    g = _m065(HEADS, HEADS)
    st = g.state
    st.players[0].slots[0].partner = "P-002"
    use_event(g, 2)
    choose(g, True)                                                    # ジャマー是玩家 1 的行動,接著輪到玩家 0
    submit(g, ability(0, st.players[0].slots[0], zone="partner"))     # 第二個使 MP 減少的行動
    assert st.pending.kind == "jammer_negate" and st.pending.source == "M-065"
    choose(g, True)
    assert st.players[1].mp == 6


def test_m065_not_when_reduction_blocked():
    # P-021:相手の効果によって自分のMPがへることはない → 沒有減少,不詢問
    g = _m065(HEADS)
    st = g.state
    st.players[1].slots[0].partner = "P-021"
    submit(g, {"type": "pass", "player": 0})
    submit(g, ability(1, st.players[1].slots[0], zone="partner"))
    use_event(g, 2)
    assert st.players[1].mp == 6 and st.pending is None


def test_m065_not_for_passive_effect():
    # 常駐效果(P-019)不是對手剛完成的行動,不詢問
    g, _ = mk(book("M-001"), book("M-065"))
    st = g.state
    st.players[0].slots[0].partner = "P-019"
    holder = st.players[1].slots[0]
    holder.partner = "P-018"
    st.players[1].mp = 6
    to_battle(g, 0)
    st.players[1].pos = 6
    submit(g, {"type": "pass", "player": 0})
    submit(g, ability(1, holder, zone="partner"))                     # 玩家 1 自己回翻 → 玩家 0 的 P-019 減 MP
    assert st.players[1].mp == 4 and st.pending is None


def test_m065_negates_partner_effect():
    # 搭檔效果也是對手的行動:P-002(相手のMPを3へらす。そうしたなら…自分のMPをふやす)整個無效
    g, _ = mk(book("M-001"), book("M-065"))
    st = g.state
    st.players[0].slots[0].partner = "P-002"
    st.players[0].mp, st.players[1].mp = 2, 6
    g.rng = Rng(HEADS)
    to_battle(g, 0)
    submit(g, ability(0, st.players[0].slots[0], zone="partner"))
    assert st.players[1].mp == 3 and st.players[0].mp == 5
    choose(g, True)
    assert st.players[1].mp == 6 and st.players[0].mp == 2


def test_m065_coin_subphase_costs_kept():
    # 擲幣子階段的消耗(Ex-026 付 MP 重擲)在無效還原後照算
    g = _m065(TAILS, HEADS)
    st = g.state
    add_slot(g, 1, "Ex-026")
    use_event(g, 2)
    choose(g, True)
    assert st.pending.kind == "coin_confirm"
    choose(g, "reflip:Ex-026:0")
    choose(g, None)                                                    # 不再重擲,結束擲硬幣子階段
    assert st.pending is None
    assert st.players[1].mp == 6 - 1                                   # 還原到 6,再付重擲的 1


# ---------------------------------------------------------------- Ex-034

def _ex034(opp_mp):
    """玩家 0 第 2 頁 E-032(MP+5,費用 2);玩家 1 的魔物裝 Ex-034。"""
    g, _ = mk(book("M-001", "E-032"), book("M-001"))
    st = g.state
    st.players[1].slots[0].partner = "Ex-034"
    st.players[0].mp = opp_mp + 2
    to_battle(g, 0)
    return g


def test_ex034_redo_with_three_more():
    # 《マッド・サイエンティスト》…そのイベントカードのコストを3ふやして、効果を解決しなおす
    g = _ex034(5)
    st = g.state
    use_event(g, 2)
    assert st.players[0].mp == 10
    assert st.pending.kind == "jammer_negate" and st.pending.source == "Ex-034"
    events = choose(g, True)
    assert st.players[1].slots[0].partner is None and "Ex-034" in st.players[1].discard
    assert st.players[0].mp == 5 - 3 + 5
    assert st.players[0].events_used_this_turn == 1
    assert len([e for e in events if e["type"] == "mp_changed" and e["player"] == 0 and e["delta"] == 5]) == 1


def test_ex034_negated_when_cannot_pay():
    # 相手がコストをはらえなければ、その効果は無効になる(相手のMPは0になる)
    g = _ex034(2)
    st = g.state
    use_event(g, 2)
    events = choose(g, True)
    assert st.players[0].mp == 0
    assert events_of(events, "effect_negated")[0]["negated"] == "E-032"


def test_ex034_blocked_by_partner_restriction():
    g = _ex034(5)
    restrict(g, 1, NO_PARTNER_EFFECTS, owner=0, duration=DUR_TURN)
    use_event(g, 2)
    assert g.state.pending is None


# ---------------------------------------------------------------- NPC 自我對戰

SELFPLAY_BOOKS = (
    ("M-001", "E-032", "E-018", "P-002", "S-001", "E-032", "S-002", "E-018", "M-002", "S-029", "E-004",
     "S-001", "E-032", "P-001", "S-002", "E-018", "S-029", "E-032", "S-001", "E-038", "S-002", "E-018",
     "S-029", "E-032", "S-001", "S-002", "E-018", "S-029", "E-032", "S-001", "S-002", "S-005"),
    ("M-065", "S-094", "Ex-025", "M-012", "S-093", "E-032", "M-001", "S-001", "Ex-034", "E-018", "S-094",
     "S-002", "E-032", "S-093", "S-001", "E-038", "S-029", "S-094", "E-032", "S-002", "S-093", "E-018",
     "S-001", "S-029", "E-032", "S-094", "S-002", "S-093", "E-038", "S-001", "S-029", "S-005"),
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


# ---------------------------------------------------------------- ジャマー是自己的行動(官方規則書第 39 頁)

def test_jammer_use_passes_action_to_opponent():
    # 相手がアクションをしたとき、その直後の自分のアクションでジャマー効果を使い…:用完後行動權換給對手
    from tests.test_level3 import _m032
    g = _m032()
    st = g.state
    use_event(g)
    assert st.action_player == 1
    choose(g, True)
    assert st.action_player == 0 and st.consecutive_passes == 0


def test_jammer_skip_keeps_action():
    from tests.test_level3 import _m032
    g = _m032()
    st = g.state
    use_event(g)
    choose(g, None)
    assert st.action_player == 1


def test_jammer_chain_returns_action():
    # 對手以 M-026 使 M-032 的無效化失效:那也是對手的行動,行動權回到玩家 1
    from tests.test_level3 import _m032
    g = _m032(p0_extra="M-026")
    st = g.state
    use_event(g)
    choose(g, True)
    choose(g, True)
    assert st.action_player == 1


@pytest.mark.parametrize("which", ["M-065", "Ex-034"])
def test_new_jammers_pass_action(which):
    g = _m065(HEADS) if which == "M-065" else _ex034(5)
    st = g.state
    use_event(g, 2)
    choose(g, True)
    assert st.pending is None and st.action_player == 0


def test_multiple_jammers_offered_together():
    # 多張ジャマー可用時同時提供:E-018 減少 MP,M-032(事件卡)與 M-065(MP 減少)都能回應
    g = _m065(HEADS)
    st = g.state
    add_slot(g, 1, "M-032")
    use_event(g, 2)
    assert st.pending.kind == "jammer_negate"
    assert {o.get("jammer") for o in st.pending.options if o["value"] is not None} == {"M-032", "M-065"}
    choose(g, "M-065")
    assert st.players[1].mp == 6 and any(s.top == "M-032" for s in st.players[1].slots)   # 用 M-065,M-032 留著
