"""擲硬幣子階段(game-engine「擲硬幣子階段」、card-effects「令對手重擲 1 枚硬幣」)。

擲幣者先使用影響硬幣結果的效果(M-012 重擲 1 枚 / M-034 改成正面),之後雙方輪替(M-019 令對手重擲 1 枚),
雙方連續不使用時依當下結果解決。以 E-005(擲 2 枚:正正回翻 2 張、一正一反無效、反反翻 2 張)驗證。
"""

import pytest

from gash.engine.engine import IllegalCommand, submit

from .test_cards import HEADS, TAILS, book, game, give
from .test_effect_characterization import StrictRng

POS = 10       # E-005 放在第 10 頁並從這裡翻開:正正 → 6、反反 → 14、一正一反 → 10


def e005(*coins, p0=(), p1=(), mp1=0):
    """玩家 0 使用 E-005,擲幣結果依 coins;p0 / p1 為各自場上另放的魔物。"""
    g = game(book0=book(p10="E-005"))
    g.rng = StrictRng(*coins)
    for p, cards in ((0, p0), (1, p1)):
        for card in cards:
            give(g, p, card)
    g.state.players[1].mp = mp1
    submit(g, {"type": "flip_pages", "player": 0, "count": 0})
    g.state.players[0].pos = POS
    submit(g, {"type": "use_book_card", "player": 0, "page": POS})
    return g


def pending(g):
    p = g.state.pending
    return None if p is None else (p.kind, p.player, [o["value"] for o in p.options])


def choose(g, player, value):
    return submit(g, {"type": "choose", "player": player, "value": value})


def test_m019_rerolls_only_the_chosen_coin():
    # E-005 擲出正、反;對手以 M-019 選第 2 枚重擲為正 → 正正,回翻 2 張;只多消耗 1 次 RNG
    g = e005(HEADS, TAILS, HEADS, p1=("M-019",))
    assert pending(g) == ("opp_coin_redo", 1, [None, 0, 1])
    choose(g, 1, 1)
    assert g.state.pending is None
    assert g.state.players[0].pos == POS - 4
    assert g.rng.calls == 3


def test_flipper_goes_first():
    g = e005(TAILS, TAILS, p0=("M-012",), p1=("M-019",))
    assert pending(g) == ("coin_confirm", 0, [None, 0, 1])               # 擲幣者先
    choose(g, 0, None)
    assert pending(g) == ("opp_coin_redo", 1, [None, 0, 1])              # 不使用後才輪到對手
    choose(g, 1, None)
    assert g.state.pending is None and g.state.players[0].pos == POS + 4


def test_turns_alternate_until_both_pass():
    # 擲幣者用 M-012 → 輪到對手;對手不使用 → 再輪到擲幣者(M-012 已用,只剩 M-034)
    g = e005(TAILS, TAILS, TAILS, p0=("M-012", "M-034"), p1=("M-019",))
    choose(g, 0, 0)                                                      # 重擲第 1 枚,仍為反面
    assert pending(g) == ("opp_coin_redo", 1, [None, 0, 1])
    choose(g, 1, None)
    assert pending(g) == ("coin_confirm", 0, [None, "heads:0", "heads:1"])
    choose(g, 0, None)                                                   # 雙方連續不使用 → 依反反解決
    assert g.state.pending is None and g.state.players[0].pos == POS + 4
    assert g.rng.calls == 3


def test_use_after_opponent_reroll():
    # 對手的 M-019 改變結果後,擲幣者仍可在下一次機會以 M-034 回應
    g = e005(HEADS, HEADS, TAILS, p0=("M-034",), p1=("M-019",))
    assert pending(g)[:2] == ("opp_coin_redo", 1)                        # 擲幣者沒有可用效果:自動不使用
    choose(g, 1, 0)                                                      # 第 1 枚重擲為反面
    assert pending(g) == ("coin_confirm", 0, [None, "heads:0"])
    choose(g, 0, "heads:0")                                              # M-034 改回正面
    assert "M-034" in g.state.players[0].discard
    assert pending(g) is None                                            # 對手的 M-019 已用過:結束
    assert g.state.players[0].pos == POS - 4


def test_illegal_opp_choice_rejected_and_kept():
    g = e005(HEADS, TAILS, p1=("M-019",))
    with pytest.raises(IllegalCommand) as e:
        choose(g, 1, 5)
    assert e.value.code == "choose.invalid"
    assert pending(g) == ("opp_coin_redo", 1, [None, 0, 1])


def test_no_coin_effects_no_prompt():
    g = e005(HEADS, TAILS)
    assert g.state.pending is None and g.state.players[0].pos == POS


@pytest.mark.parametrize("value", [0, "heads:1"])
def test_coin_effects_do_not_offer_jammer(value):
    # M-012 / M-034 不是可被ジャマー無效的效果:對手有可用的 M-026 也不詢問
    g = e005(HEADS, TAILS, HEADS, p0=("M-012", "M-034"), p1=("M-026",), mp1=5)
    choose(g, 0, value)
    assert g.state.pending is None or g.state.pending.kind != "jammer_negate"
    assert g.state.players[1].mp == 5


def test_m019_does_not_offer_jammer():
    g = e005(HEADS, TAILS, HEADS, p0=("M-026",), p1=("M-019",))
    g.state.players[0].mp = 5
    choose(g, 1, 0)
    assert g.state.pending is None
    assert g.state.players[0].mp == 5


def test_coin_effects_keep_action_player():
    # 非戰鬥中使用擲幣事件卡:子階段中雙方各使用一次效果後,行動權與沒有使用時相同
    plain = e005(TAILS, TAILS)
    used = e005(TAILS, TAILS, TAILS, TAILS, p0=("M-012",), p1=("M-019",))
    choose(used, 0, 0)
    choose(used, 1, 1)
    assert used.state.pending is None
    assert (used.state.action_player, used.state.consecutive_passes) == \
        (plain.state.action_player, plain.state.consecutive_passes)
