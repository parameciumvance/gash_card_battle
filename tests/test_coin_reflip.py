"""擲幣重擲(M-012 / M-019)的可用判斷:兩者都是「魔物の効果」,受 E-024 / E-025 限制
(card-effects 禁止旗標「禁指定或全體魔物效果」);只在擲幣確認鏈中詢問,不能主動宣告。"""
import pytest

from gash.api.views import snapshot
from gash.engine.effects.primitives import add_modifier
from gash.engine.state import DUR_TURN, MAMODO_LOCKED, NO_MAMODO_EFFECTS

from .test_cards import TAILS, book, give
from .test_effect_characterization import defend_with_s025, pending, strict_game


def restrict(g, p, flag, slot=None):
    add_modifier(g, [], kind="restriction", source="E-024" if slot else "E-025", owner=1 - p,
                 duration=DUR_TURN, target_player=p,
                 target_slot=slot.uid if slot else None, flag=flag)


def m012_game():
    g = strict_game(TAILS, book1=book(p2="S-025"))
    return g, give(g, 1, "M-012")


def test_m012_offered_normally():
    g, _ = m012_game()
    _, dp, _ = defend_with_s025(g)
    assert pending(g)[:2] == ("coin_confirm", dp)


@pytest.mark.parametrize("how", ["locked", "no_mamodo_effects"])
def test_m012_not_offered_when_restricted(how):
    g, m012 = m012_game()
    if how == "locked":
        restrict(g, 1, MAMODO_LOCKED, m012)            # E-024:その魔物の「魔物の効果」を使えない
    else:
        restrict(g, 1, NO_MAMODO_EFFECTS)              # E-025:「魔物の効果」を使えない
    defend_with_s025(g)
    assert pending(g) is None                          # 不詢問重擲,硬幣結果直接確定
    assert "mamodo:M-012" not in g.state.players[1].used_abilities


def test_m012_lock_on_other_mamodo_does_not_matter():
    g, _ = m012_game()
    restrict(g, 1, MAMODO_LOCKED, give(g, 1, "M-004"))   # 封鎖的是另一隻
    _, dp, _ = defend_with_s025(g)
    assert pending(g)[:2] == ("coin_confirm", dp)


def test_reflip_mamodo_have_no_declarable_ability():
    # 只在擲幣確認鏈中詢問:快照不給主動使用的效果(前端不會出現無法使用的「使用」按鈕)
    g = strict_game(TAILS)
    give(g, 0, "M-012")
    give(g, 0, "M-019")
    tops = {s["top"]: s["ability"] for s in snapshot(g, 0)["players"][0]["slots"]}
    assert tops["M-012"] is None and tops["M-019"] is None
