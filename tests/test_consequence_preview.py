"""後果預告(battle-api「保護的後果預告快照」「翻頁後落敗的快照」「戰術的預估合計魔力快照」)。"""
import pytest

from gash.api.views import snapshot
from gash.engine import engine as eng
from gash.engine.engine import submit
from gash.engine.state import MamodoSlot
from tests.test_level2 import _run_attack_to_damage, _use_partner, book, mk, slot_uid, to_battle


# ---------------------------------------------------------------- 保護的後果預告

def protect_decision(*, sherry=True, attacker_top="M-005", page=2, protector_injured=False):
    """玩家 0 的布拉葛(或賈修)攻擊,玩家 1 等待保護決策;sherry 時玩家 0 先用 P-012。
    回傳 (game, 玩家 1 可保護的 M-004 slot)。"""
    g, _ = mk(book("M-005", "S-008", "S-001"), book("M-001"))
    st = g.state
    st.players[0].mp = 10
    brago = st.players[0].slots[0]
    brago.partner = "P-012"
    st.players[0].slots.append(MamodoSlot(uid=st.next_uid(), stack=["M-001"]))
    protector = MamodoSlot(uid=st.next_uid(), stack=["M-004"], injured=protector_injured)
    st.players[1].slots.append(protector)
    to_battle(g, 0)
    if sherry:
        _use_partner(g, 0, brago)
        submit(g, {"type": "pass", "player": 1})
    submit(g, {"type": "declare_attack", "player": 0, "page": page, "slot_uid": slot_uid(g, 0, attacker_top)})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    _run_attack_to_damage(g, 0, 1)
    assert st.pending.kind == "protect" and st.pending.player == 1
    return g, protector


def option(g, uid, viewer=1):
    pending = snapshot(g, viewer)["pending"]
    return next((o for o in pending.get("options", []) if o.get("value") == uid), None)


def test_sherry_protector_marked_as_leaving():
    # P-012:このターン中、自分の「ブラゴ」によるダメージを「かばって」、ダメージを受けた魔物は捨て札になる
    g, protector = protect_decision()
    opt = option(g, protector.uid)
    assert opt["leaves"] is True and opt["leave_reason"] == "P-012"
    submit(g, {"type": "choose", "player": 1, "value": protector.uid})
    assert protector not in g.state.players[1].slots                    # 預告與實際結算一致


def test_injured_protector_marked_as_leaving():
    g, protector = protect_decision(sherry=False, protector_injured=True)
    opt = option(g, protector.uid)
    assert opt["leaves"] is True and opt["leave_reason"] == "injured"
    submit(g, {"type": "choose", "player": 1, "value": protector.uid})
    assert protector not in g.state.players[1].slots


def test_healthy_protector_not_marked():
    g, protector = protect_decision(sherry=False)
    opt = option(g, protector.uid)
    assert not opt.get("leaves") and "leave_reason" not in opt
    submit(g, {"type": "choose", "player": 1, "value": protector.uid})
    assert protector in g.state.players[1].slots and protector.injured   # 只負傷


def test_sherry_only_for_brago_damage():
    g, protector = protect_decision(attacker_top="M-001", page=3)          # ガッシュ的攻擊:雪莉不適用
    assert not option(g, protector.uid).get("leaves")


def test_preview_does_not_touch_real_game():
    g, protector = protect_decision()
    before = (g.state.players[1].discard[:], [s.uid for s in g.state.players[1].slots], g.rng.getstate())
    snapshot(g, 1)
    assert (g.state.players[1].discard, [s.uid for s in g.state.players[1].slots], g.rng.getstate()) == before


@pytest.mark.parametrize("viewer", [0, "spectator"])
def test_others_cannot_see_outcomes(viewer):
    g, protector = protect_decision()
    pending = snapshot(g, viewer)["pending"]
    assert "options" not in pending                                       # 選項只給決策者
    assert "leaves" not in str(pending["info"])


@pytest.mark.parametrize("heads_leaves", [True, False])
def test_random_outcome_not_marked(monkeypatch, heads_leaves):
    """保護的魔物離不離場取決於亂數時(這裡以 monkeypatch 模擬),不標示。兩個方向都測:
    若預告偷用實際的 RNG(兩次結果必然相同),其中一個方向一定會被標示。"""
    import random
    draws = [random.Random(seed).random() < .5 for seed in eng.PREVIEW_SEEDS]
    assert len(set(draws)) == 2                                           # 前提:兩個種子的結果不同
    original = eng._maybe_discard_protector

    def coin_discard(game, batch, player, slot, ctx):
        if (game.rng.random() < .5) == heads_leaves and slot in game.state.players[player].slots:
            eng._discard_slot(game, batch, player, slot, reason="protect_discard")
            return
        return original(game, batch, player, slot, ctx)
    monkeypatch.setattr(eng, "_maybe_discard_protector", coin_discard)
    g, protector = protect_decision(sherry=False)
    assert not option(g, protector.uid).get("leaves")


# ---------------------------------------------------------------- 翻頁後落敗

def start_phase_at(pos):
    g, _ = mk(book("M-001"), book("M-001"))
    g.state.players[0].pos = pos
    assert g.state.phase == "start" and g.state.turn_player == 0
    return g


def test_flip_end_loses_per_count():
    g = start_phase_at(28)                                                # 第 28–29 頁,最多翻 2 張
    for viewer in (0, 1, "all"):                                          # 只依公開資訊,所有視角相同
        assert snapshot(g, viewer)["players"][0]["flip_end_loses"] == [False, False, True]


def test_flip_end_loses_matches_actual_end():
    g = start_phase_at(28)
    submit(g, {"type": "flip_pages", "player": 0, "count": 2})
    assert eng.end_flip_loses(g, 0)                                       # 預告會落敗的張數,翻了之後確實會落敗


def test_flip_end_loses_with_skip_standby():
    from gash.engine.state import Standby
    g = start_phase_at(28)
    g.state.standby.append(Standby(kind="skip_end_flip", source="M-030", owner=0, created_turn=g.state.turn_no))
    assert snapshot(g, 0)["players"][0]["flip_end_loses"] == [False, False, False]


def test_flip_end_loses_only_in_start_phase_for_turn_player():
    g = start_phase_at(28)
    assert snapshot(g, 0)["players"][1].get("flip_end_loses") is None     # 非回合玩家
    submit(g, {"type": "flip_pages", "player": 0, "count": 0})
    assert snapshot(g, 0)["players"][0].get("flip_end_loses") is None     # 戰鬥階段


# ---------------------------------------------------------------- 預估魔力的確定宣告加成

def declare_bonus(items, number):
    """明細中來自戰術自身宣告時效果(number)的加成。"""
    return [i["amount"] for i in items if i.get("source") == number and i["kind"] != "spell"]


def preview(number, side, mamodo="M-001", setup=None):
    g, _ = mk(book(mamodo, number), book("M-001"))
    if setup:
        setup(g)
    slot = g.state.players[0].slots[0]
    return g, eng.spell_power_preview(g, 0, slot, number, side)


def test_s092_attack_preview_includes_declare_bonus_and_matches_actual():
    # S-092:この術を攻撃で使ったとき、この術の魔力を+2000する
    g, (power, items) = preview("S-092", "attack")
    assert declare_bonus(items, "S-092") == [2000]
    g.state.players[0].mp = 10
    to_battle(g, 0)
    submit(g, {"type": "declare_attack", "player": 0, "page": 2, "slot_uid": g.state.players[0].slots[0].uid})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    actual, _ = eng.side_breakdown(g, g.state.battle, "attack")
    assert actual == power                                               # 與宣告後實際的合計魔力相同


def test_s092_defense_preview_has_no_attack_bonus():
    g, (power, items) = preview("S-092", "defense")
    assert declare_bonus(items, "S-092") == []


@pytest.mark.parametrize("number,side,expected", [
    ("S-016", "defense", [1000]),           # この術を防御で使ったとき +1000
    ("S-016", "attack", []),
    ("S-017", "attack", [2000]),            # この術を攻撃で使ったとき +2000
    ("S-017", "defense", []),
])
def test_side_dependent_bonus(number, side, expected):
    g, (power, items) = preview(number, side, mamodo="M-009")
    assert declare_bonus(items, number) == expected


@pytest.mark.parametrize("used_thunder,expected", [(True, [4000]), (False, [])])
def test_ex043_condition_on_public_state(used_thunder, expected):
    # Ex-043:直前のターンに、相手が「雷」属性の術を使っていれば、この術の魔力を+4000、ダメージを+2する
    def setup(g):
        if used_thunder:
            g.state.players[1].spell_attrs_by_turn[g.state.turn_no - 1] = {"雷"}
    g, (power, items) = preview("Ex-043", "attack", setup=setup)
    assert declare_bonus(items, "Ex-043") == expected


@pytest.mark.parametrize("number", ["S-040", "S-108"])
def test_coin_bonus_not_included(number):
    for side in ("attack", "defense"):
        g, (power, items) = preview(number, side)
        assert declare_bonus(items, number) == []
