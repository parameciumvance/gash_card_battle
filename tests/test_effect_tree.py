"""效果樹直譯器單元測試(effect-tree spec):節點不可變、續體純資料、上溯續行、
Coin 同步 / 非同步只執行一次、Standby 脫離式、註冊檢查。"""

import json
from dataclasses import FrozenInstanceError, dataclass

import pytest

from gash.engine.effects import registry as reg
from gash.engine.effects import tree
from gash.engine.effects.tree import (
    CHOICE_KEY, CONT_KEY, Choose, Coin, HeadsAtLeast, Nothing, NextStartPhase, OwnMamodo,
    Sequence, Standby, When, run_effect,
)
from gash.engine.engine import IllegalCommand, submit

from .test_cards import HEADS, TAILS, end_turn, game, give, slot0
from .test_effect_characterization import StrictRng, pending

LOG: list = []


@dataclass(frozen=True)
class Record(tree.Effect):
    """測試用葉節點:把自己的標籤(與指定 ctx 值)寫進 LOG,用來驗證副作用次數與順序。"""
    label: str = ""
    key: str = ""

    def run(self, rt, ctx, path):
        LOG.append((self.label, ctx.get(self.key)) if self.key else self.label)
        return True


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    LOG.clear()
    monkeypatch.setattr(tree, "EFFECTS", dict(tree.EFFECTS))
    monkeypatch.setattr(tree, "TREE_HOOKS", set(tree.TREE_HOOKS))
    monkeypatch.setattr(reg, "EVENT", dict(reg.EVENT))
    monkeypatch.setattr(reg, "EVENT_CONDITION", dict(reg.EVENT_CONDITION))


def run(g, root, **ctx):
    tree.EFFECTS["T-000:test"] = root
    base = {"player": 0, "source": "T-000"}
    base.update(ctx)
    batch = []
    run_effect(g, batch, "T-000:test", base)
    return batch


def two_slot_game(**kw):
    g = game(**kw)
    b = give(g, 0, "M-002")
    return g, slot0(g, 0), b


def roundtrip_pending(g, key):
    """把 pending 續體經 json.dumps → json.loads 往返,驗證續體是純資料。"""
    g.state.pending.data[key] = json.loads(json.dumps(g.state.pending.data[key]))


# ================================================================ 節點

def test_nodes_are_immutable():
    seq = Sequence(steps=(Record("A"),))
    with pytest.raises(FrozenInstanceError):
        seq.steps = ()
    with pytest.raises(FrozenInstanceError):
        Choose(target=OwnMamodo(), bind="x", prompt="p").bind = "y"


def test_may_suspend_is_derived():
    assert not Sequence(steps=(Record("A"), Record("B"))).may_suspend
    assert Sequence(steps=(Record("A"), Choose(target=OwnMamodo(), prompt="p"))).may_suspend
    assert Coin().may_suspend
    assert not Standby(then=Record("A")).may_suspend   # 排程本身不會停下
    assert not When(cond=HeadsAtLeast(), then=Record("A")).may_suspend


def test_node_at_invalid_path():
    root = Sequence(steps=(Record("A"),))
    assert tree.node_at(root, (0,)) == Record("A")
    with pytest.raises(LookupError):
        tree.node_at(root, (3,))


# ================================================================ Choose / 上溯續行

def test_choose_single_option_auto_resolves():
    g = game()
    root = Sequence(steps=(Record("A"),
                           Choose(target=OwnMamodo(), bind="slot", prompt="t_pick",
                                  then=Record("B", "slot")),
                           Record("C")))
    run(g, root)
    assert g.state.pending is None
    assert LOG == ["A", ("B", slot0(g, 0).uid), "C"]


def test_choose_sibling_nodes_run_after_response_once_each():
    g, a, b = two_slot_game()
    root = Sequence(steps=(Record("A"),
                           Choose(target=OwnMamodo(), bind="slot", prompt="t_pick",
                                  then=Record("B", "slot")),
                           Record("C")))
    run(g, root)
    assert LOG == ["A"]
    assert pending(g) == ("t_pick", 0, [a.uid, b.uid])
    assert list(g.state.pending.data) == [CHOICE_KEY]
    roundtrip_pending(g, CHOICE_KEY)
    submit(g, {"type": "choose", "player": 0, "value": b.uid})
    assert LOG == ["A", ("B", b.uid), "C"]
    assert g.state.pending is None


def test_choose_invalid_value_keeps_pending_and_state():
    g, a, b = two_slot_game()
    run(g, Choose(target=OwnMamodo(), bind="slot", prompt="t_pick", then=Record("B")))
    with pytest.raises(IllegalCommand) as exc:
        submit(g, {"type": "choose", "player": 0, "value": 9999})
    assert exc.value.code == "choose.invalid"
    assert pending(g) == ("t_pick", 0, [a.uid, b.uid])
    assert LOG == []
    submit(g, {"type": "choose", "player": 0, "value": a.uid})
    assert LOG == ["B"]


def test_two_consecutive_chooses():
    g, a, b = two_slot_game()
    root = Sequence(steps=(
        Choose(target=OwnMamodo(), bind="x", prompt="t_first", then=Record("X", "x")),
        Choose(target=OwnMamodo(), bind="y", prompt="t_second", then=Record("Y", "y")),
        Record("END"),
    ))
    run(g, root)
    assert pending(g)[0] == "t_first"
    submit(g, {"type": "choose", "player": 0, "value": a.uid})
    assert pending(g)[0] == "t_second"
    assert LOG == [("X", a.uid)]
    roundtrip_pending(g, CHOICE_KEY)
    submit(g, {"type": "choose", "player": 0, "value": b.uid})
    assert LOG == [("X", a.uid), ("Y", b.uid), "END"]
    assert g.state.pending is None


def test_nested_sequence_resumes_inner_then_outer():
    g, a, b = two_slot_game()
    root = Sequence(steps=(
        Record("A"),
        Sequence(steps=(Record("B"),
                        Choose(target=OwnMamodo(), bind="s", prompt="t_pick", then=Record("C")),
                        Record("D"))),
        Record("E"),
    ))
    run(g, root)
    assert LOG == ["A", "B"]
    submit(g, {"type": "choose", "player": 0, "value": a.uid})
    assert LOG == ["A", "B", "C", "D", "E"]


# ================================================================ Coin

def coin_root():
    return Sequence(steps=(Record("A"),
                           Coin(count=1, on=HeadsAtLeast(1),
                                then=Record("HEADS"), otherwise=Record("TAILS")),
                           Record("B")))


@pytest.mark.parametrize("coin,branch", [(HEADS, "HEADS"), (TAILS, "TAILS")])
def test_coin_sync_runs_each_node_once(coin, branch):
    g = game()
    g.rng = StrictRng(coin)
    run(g, coin_root())
    assert LOG == ["A", branch, "B"]
    assert g.state.pending is None
    assert g.rng.calls == 1


def test_coin_with_m012_confirm_runs_each_node_once():
    g = game()
    give(g, 0, "M-012")
    g.rng = StrictRng(HEADS)
    run(g, coin_root())
    assert LOG == ["A"]                       # 停在確認鏈,B 尚未執行
    assert pending(g)[0] == "coin_confirm"
    assert CONT_KEY in g.state.pending.data and CHOICE_KEY not in g.state.pending.data
    roundtrip_pending(g, CONT_KEY)
    submit(g, {"type": "choose", "player": 0, "value": None})   # 保留
    assert LOG == ["A", "HEADS", "B"]
    assert g.rng.calls == 1


def test_coin_reflip_via_m012_changes_branch_and_consumes_rng():
    g = game()
    give(g, 0, "M-012")
    g.rng = StrictRng(TAILS, HEADS)
    run(g, coin_root())
    submit(g, {"type": "choose", "player": 0, "value": 0})      # 重擲第 0 枚
    assert LOG == ["A", "HEADS", "B"]
    assert g.rng.calls == 2


# ================================================================ Standby(脫離式)

def test_standby_is_detached_and_fires_once():
    g = game()
    root = Sequence(steps=(Standby(at=NextStartPhase(), expires="next_start",
                                   then=Record("S")),
                           Record("B")))
    run(g, root)
    assert LOG == ["B"]                        # 排程後外層立即續行,不等觸發
    assert len(g.state.standby) == 1
    sb = g.state.standby[0]
    assert sb.kind == "start_phase" and sb.data["expires"] == "next_start"
    assert list(sb.data) == ["callback", "expires", CONT_KEY]
    sb.data[CONT_KEY] = json.loads(json.dumps(sb.data[CONT_KEY]))
    end_turn(g)
    submit(g, {"type": "flip_pages", "player": 1, "count": 0})
    assert LOG == ["B", "S"]                   # 觸發時只解決 then,不重跑 B
    assert g.state.standby == []


def test_standby_expires_turn_is_removed_at_end_of_creating_turn():
    g = game()
    run(g, Standby(at=NextStartPhase(), expires="turn", then=Record("S")))
    assert len(g.state.standby) == 1
    end_turn(g)
    assert g.state.standby == []
    submit(g, {"type": "flip_pages", "player": 1, "count": 0})
    assert LOG == []


# ================================================================ 註冊檢查

def test_register_rejects_suspending_standby_then():
    with pytest.raises(ValueError, match="Standby.then"):
        tree.validate_tree(Standby(then=Choose(target=OwnMamodo(), prompt="t_pick")))
    with pytest.raises(ValueError, match="Standby.then"):
        tree.validate_tree(Standby(then=Sequence(steps=(Record("A"), Coin()))))


@pytest.mark.parametrize("prompt", ["coin_confirm", "opp_coin_redo", "protect", "deploy_page"])
def test_register_rejects_reserved_prompt(prompt):
    with pytest.raises(ValueError, match="pending kind"):
        tree.validate_tree(Choose(target=OwnMamodo(), prompt=prompt))


def test_register_rejects_existing_resolver_key_as_prompt():
    with pytest.raises(ValueError, match="pending kind"):
        tree.validate_tree(Choose(target=OwnMamodo(), prompt="m011_pick"))


def test_register_duplicate_tree_hook_rejected():
    reg.event("T-900", effect=Nothing())
    with pytest.raises(ValueError, match="已被註冊"):
        reg.event("T-900", effect=Nothing())


def test_register_tree_after_legacy_rejected():
    @reg.event("T-901")
    def legacy(game, batch, player, page):
        pass
    with pytest.raises(ValueError, match="已被註冊"):
        reg.event("T-901", effect=Nothing())


def test_register_legacy_after_tree_rejected():
    reg.event("T-902", effect=Nothing())
    with pytest.raises(ValueError, match="已以效果樹註冊"):
        @reg.event("T-902")
        def legacy(game, batch, player, page):
            pass


def test_legacy_decorators_unchanged():
    @reg.event("T-903", condition=lambda g, p: True)
    def handler(game, batch, player, page):
        return "ok"
    assert reg.EVENT["T-903"] is handler
    assert reg.EVENT_CONDITION["T-903"](None, 0) is True


# ================================================================ 葉節點(與遷移前 primitives 的事件一致)

def test_when_side_guard_skips_coin_for_attack_side():
    g = game()
    g.rng = StrictRng()                       # 任何擲幣都會拋錯
    root = When(cond=tree.SideIs("defense"), then=Coin(then=Record("HEADS")))
    run(g, root, side="attack")
    assert LOG == [] and g.rng.calls == 0


def test_restrict_opponent_matches_add_restriction():
    from gash.engine.state import DUR_UNTIL_END_NEXT_TURN, NO_SPELLS
    g = game()
    batch = run(g, tree.RestrictOpponent(flag=NO_SPELLS, duration=DUR_UNTIL_END_NEXT_TURN))
    ev = [e for e in batch if e["type"] == "modifier_added"]
    assert len(ev) == 1 and ev[0]["kind"] == "restriction" and ev[0]["source"] == "T-000"
    assert ev[0]["target_player"] == 1 and ev[0]["flag"] == NO_SPELLS
    assert ev[0]["duration"] == DUR_UNTIL_END_NEXT_TURN
    m = g.state.modifiers[-1]
    assert (m.owner, m.target_player, m.flag) == (0, 1, NO_SPELLS)


def test_negate_attack_without_battle_is_noop():
    g = game()
    batch = run(g, tree.NegateAttack())
    assert batch == [] and g.state.battle is None


def test_make_next_attack_undefendable_schedules_standby():
    g = game()
    batch = run(g, tree.MakeNextAttackUndefendable())
    assert [e["type"] for e in batch] == ["standby_set"]
    sb = g.state.standby[0]
    assert (sb.kind, sb.source, sb.owner, sb.data) == ("attack_undefendable", "T-000", 0, {})


def test_add_power_target_gone_is_noop_without_event():
    from gash.engine.state import DUR_TURN
    g = game()
    batch = run(g, tree.AddPower(amount=3000, duration=DUR_TURN), slot=9999)
    assert batch == [] and g.state.modifiers == []


def test_add_power_applies_to_bound_slot():
    from gash.engine.state import DUR_TURN
    g, a, b = two_slot_game()
    batch = run(g, tree.AddPower(amount=3000, duration=DUR_TURN), slot=b.uid)
    assert [e["type"] for e in batch] == ["modifier_added"]
    m = g.state.modifiers[-1]
    assert (m.kind, m.target_slot, m.amount, m.source) == ("power", b.uid, 3000, "T-000")


# ================================================================ 新舊並存

def test_tree_and_decorator_cards_coexist_in_one_game():
    from gash.engine.engine import slot_power
    from .test_cards import book
    assert ("E-001", "event") in tree.TREE_HOOKS       # 效果樹註冊
    assert ("E-002", "event") not in tree.TREE_HOOKS    # 仍是裝飾器註冊
    g = game(book0=book(p2="E-001"), book1=book(p2="E-002"))
    s = slot0(g, 0)
    base = slot_power(g, 0, s)
    submit(g, {"type": "flip_pages", "player": 0, "count": 0})
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})   # E-001(樹)
    end_turn(g)
    submit(g, {"type": "flip_pages", "player": 1, "count": 0})
    assert slot_power(g, 0, s) == base + 3000                      # 待命於下回合開始階段觸發
    submit(g, {"type": "use_book_card", "player": 1, "page": 2})   # E-002(舊寫法)
    assert any(m.source == "E-002" and m.kind == "restriction" for m in g.state.modifiers)
