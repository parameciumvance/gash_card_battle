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
    monkeypatch.setattr(reg, "SPELL_RIDERS", dict(reg.SPELL_RIDERS))
    monkeypatch.setattr(reg, "SPELL_NONBATTLE", dict(reg.SPELL_NONBATTLE))
    for name in ("ACTIVATED", "ON_PLAY", "ON_DISCARD", "START_PHASE", "STATIC_POWER",
                 "DAMAGE_IMMUNITY", "SPELL_COMPAT"):
        monkeypatch.setattr(reg, name, dict(getattr(reg, name)))
    monkeypatch.setattr(reg, "TRIGGERS", {k: list(v) for k, v in reg.TRIGGERS.items()})


def without_seq(events):
    return [{k: v for k, v in e.items() if k != "seq"} for e in events]


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


def test_register_rejects_existing_resolver_key_as_prompt(monkeypatch):
    monkeypatch.setattr(reg, "CHOICE_RESOLVERS", {**reg.CHOICE_RESOLVERS, "t_legacy_pick": print})
    with pytest.raises(ValueError, match="pending kind"):
        tree.validate_tree(Choose(target=OwnMamodo(), prompt="t_legacy_pick"))


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
    assert (sb.kind, sb.source, sb.owner, sb.data) == (
        "attack_undefendable", "T-000", 0, {"expires": "next_battle"})


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
    """同一局中效果樹註冊的卡(E-001)與以裝飾器註冊的卡都正常運作。
    全部卡片都已遷移,因此用一張測試專用的事件卡 T-990(複製 E-003 的資料)以舊寫法註冊。"""
    import dataclasses
    from gash.engine.engine import slot_power
    from .test_cards import book
    g = game(book0=book(p2="E-001", p3="T-990"))
    g.db = dict(g.db)
    g.db["T-990"] = dataclasses.replace(g.db["E-003"], number="T-990")

    @reg.event("T-990")
    def legacy(game_, batch, player, page):
        from gash.engine.engine import gain_mp
        gain_mp(game_, batch, player, 5, "T-990")

    assert ("E-001", "event") in tree.TREE_HOOKS and ("T-990", "event") not in tree.TREE_HOOKS
    s = slot0(g, 0)
    base = slot_power(g, 0, s)
    submit(g, {"type": "flip_pages", "player": 0, "count": 0})
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})     # E-001(樹)
    end_turn(g)
    submit(g, {"type": "flip_pages", "player": 1, "count": 0})
    assert slot_power(g, 0, s) == base + 3000                        # 待命於下回合開始階段觸發
    end_turn(g)
    submit(g, {"type": "flip_pages", "player": 0, "count": 0})
    g.state.players[0].pos = 2                                       # 讓第 3 頁翻開
    mp = g.state.players[0].mp
    submit(g, {"type": "use_book_card", "player": 0, "page": 3})     # T-990(舊寫法)
    assert g.state.players[0].mp == mp + 5


# ================================================================ 註冊表一致性(code review CR1)

def snapshot():
    return (dict(tree.EFFECTS), set(tree.TREE_HOOKS), dict(reg.SPELL_RIDERS))


def test_rider_second_registration_rejected_and_registry_unchanged():
    reg.spell_rider("T-910", on_damage=Nothing(), counter=True)
    before = snapshot()
    with pytest.raises(ValueError, match="只能註冊一次"):
        reg.spell_rider("T-910", on_declare=Nothing())          # 不同掛鉤
    with pytest.raises(ValueError, match="只能註冊一次"):
        reg.spell_rider("T-910", counter=True)                  # 單純旗標
    with pytest.raises(ValueError, match="只能註冊一次"):
        reg.spell_rider("T-910", on_damage=Nothing())           # 同掛鉤
    assert snapshot() == before
    rider = reg.SPELL_RIDERS["T-910"]
    assert rider.on_damage is not None and rider.counter is True


def test_rider_legacy_call_after_tree_rejected_and_registry_unchanged():
    reg.spell_rider("T-911", on_damage=Nothing())
    before = snapshot()
    with pytest.raises(ValueError, match="只能註冊一次"):
        reg.spell_rider("T-911", on_damage=lambda game, batch, player: None)
    assert snapshot() == before


def test_rider_failed_validation_leaves_no_partial_state():
    before = snapshot()
    with pytest.raises(ValueError, match="Standby.then"):
        reg.spell_rider("T-912", on_damage=Nothing(),
                        on_declare=Standby(then=Coin()))        # 第二個掛鉤不合法
    assert snapshot() == before
    reg.spell_rider("T-912", on_damage=Nothing(), on_declare=Nothing())   # 之後仍可正常註冊
    assert ("T-912", "rider.on_declare") in tree.TREE_HOOKS


def test_event_failed_validation_leaves_no_claim():
    before = snapshot()
    with pytest.raises(ValueError):
        reg.event("T-913", effect=Choose(target=OwnMamodo(), prompt="coin_confirm"))
    assert snapshot() == before and "T-913" not in reg.EVENT
    reg.event("T-913", effect=Nothing())                        # 未被殘留標記擋住
    assert ("T-913", "event") in tree.TREE_HOOKS


# ================================================================ 新增葉節點(S-027/S-035/S-037/S-040/S-041/S-045/S-046/S-057 共用)

def start_battle_for_leaf_test(g):
    """建立一場戰鬥(不透過 declare_attack,只為了讓葉節點有 game.state.battle 可寫)。"""
    from gash.engine.state import BattleState
    g.state.battle = BattleState(attacker=0, step="defense", attack_page=1,
                                 attack_spell="T-000", attack_slot=slot0(g, 0).uid)
    return g.state.battle


def test_grant_full_immune_matches_primitive():
    from gash.engine.state import DUR_UNTIL_END_NEXT_TURN
    g = game()
    batch = run(g, tree.GrantFullImmune())
    ev = [e for e in batch if e["type"] == "modifier_added"]
    assert len(ev) == 1 and ev[0]["kind"] == "full_immune"
    m = g.state.modifiers[-1]
    assert (m.owner, m.target_player, m.duration, m.source) == (0, 0, DUR_UNTIL_END_NEXT_TURN, "T-000")


def test_schedule_injure_instead_next_win():
    g = game()
    batch = run(g, tree.ScheduleInjureInsteadNextWin())
    assert [e["type"] for e in batch] == ["standby_set"]
    sb = g.state.standby[0]
    assert (sb.kind, sb.source, sb.owner) == ("injure_instead", "T-000", 0)


def test_make_attack_undefendable_sets_current_battle_directly():
    g = game()
    start_battle_for_leaf_test(g)
    batch = run(g, tree.MakeAttackUndefendable())
    assert batch == []  # 直接作用,不像 MakeNextAttackUndefendable 會發 standby_set
    assert g.state.battle.attack_undefendable is True


def test_make_attack_undefendable_without_battle_is_noop():
    g = game()
    batch = run(g, tree.MakeAttackUndefendable())
    assert batch == [] and g.state.battle is None


def test_adjust_defense_damage_without_battle_is_noop():
    g = game()
    batch = run(g, tree.AdjustDefenseDamage(amount=-1))
    assert batch == []


def test_adjust_defense_damage_matches_old_event_shape():
    g = game()
    start_battle_for_leaf_test(g)
    batch = run(g, tree.AdjustDefenseDamage(amount=-1))
    assert without_seq(batch) == [{"type": "effect_applied", "source": "T-000", "amount": -1}]
    assert g.state.battle.data["defense_damage_delta"] == -1
    run(g, tree.AdjustDefenseDamage(amount=-1))  # 可累加
    assert g.state.battle.data["defense_damage_delta"] == -2


def test_disable_book_protection_matches_old_event_shape():
    g = game()
    start_battle_for_leaf_test(g)
    batch = run(g, tree.DisableBookProtection())
    assert without_seq(batch) == [{"type": "effect_applied", "source": "T-000"}]
    assert g.state.battle.data["no_protect_book"] is True


def test_add_attack_bonus_per_heads_scales_with_results():
    g = game()
    start_battle_for_leaf_test(g)
    batch = run(g, tree.AddAttackBonusPerHeads(per_head=2000), results=[True, True, False])
    assert without_seq(batch) == [{"type": "effect_applied", "source": "T-000", "amount": 4000}]
    assert g.state.battle.data["attack_spell_bonus"] == 4000


def test_add_attack_bonus_per_heads_all_tails_is_zero_but_recorded():
    g = game()
    start_battle_for_leaf_test(g)
    batch = run(g, tree.AddAttackBonusPerHeads(per_head=2000), results=[False, False])
    assert without_seq(batch) == [{"type": "effect_applied", "source": "T-000", "amount": 0}]


def test_always_condition_is_true():
    assert tree.Always().test(None, {}) is True


def test_rider_invalid_kwarg_leaves_no_partial_state_and_allows_retry():
    """review R1(2026-09-27):拼錯的 keyword 在任何 TREE_HOOKS / EFFECTS 寫入前就被拒絕。"""
    before = snapshot()
    with pytest.raises(TypeError):
        reg.spell_rider("T-914", on_damage=Nothing(), countr=True)   # 拼字錯誤
    assert snapshot() == before
    reg.spell_rider("T-914", on_damage=Nothing(), counter=True)      # 修正後可重試
    assert reg.SPELL_RIDERS["T-914"].counter is True


# ================================================================ 第三批新增節點(E-005/E-006/E-022/E-026)

def test_heads_count_exact_match():
    assert tree.HeadsCount(0).test(None, {"results": [False, False]}) is True
    assert tree.HeadsCount(0).test(None, {"results": [True, False]}) is False
    assert tree.HeadsCount(2).test(None, {"results": [True, True]}) is True
    assert tree.HeadsCount(2).test(None, {"results": [True, False]}) is False


def test_turn_pages_forward_matches_primitive():
    g = game()
    pos0 = g.state.players[0].pos
    batch = run(g, tree.TurnPagesForward(leaves=2))
    assert g.state.players[0].pos == pos0 + 4
    assert [e["type"] for e in batch] == ["pages_turned"]


def test_turn_pages_back_matches_primitive():
    g = game()
    g.state.players[0].pos = 10
    batch = run(g, tree.TurnPagesBack(leaves=2))
    assert g.state.players[0].pos == 6
    assert [e["type"] for e in batch] == ["pages_turned"]


def test_heal_slot_applies_and_ignores_missing_target():
    g = game()
    a = slot0(g, 0)
    a.injured = True
    run(g, tree.HealSlot(), slot=a.uid)
    assert a.injured is False

    g2 = game()
    batch = run(g2, tree.HealSlot(), slot=9999)   # 目標不存在:無效果、無例外
    assert batch == []


def test_gain_mp_per_heads_scales_and_zero_is_silent():
    g = game()
    g.state.players[0].mp = 0
    batch = run(g, tree.GainMpPerHeads(per_head=2), results=[True, False])
    assert g.state.players[0].mp == 2
    assert [e["type"] for e in batch] == ["mp_changed"]

    g2 = game()
    g2.state.players[0].mp = 0
    batch = run(g2, tree.GainMpPerHeads(per_head=2), results=[False, False])
    assert g2.state.players[0].mp == 0
    assert batch == []   # gain_mp(amount=0) 不發事件,與遷移前一致


def test_partner_discarded_this_turn_options_and_validate():
    g = game()
    g.state.players[0].discard.append("P-001")
    g.state.players[0].discarded_this_turn.append("P-001")
    spec = tree.PartnerDiscardedThisTurn()
    opts = spec.options(g, {"player": 0})
    assert opts == [{"value": 0, "card": "P-001", "slot_uid": slot0(g, 0).uid}]
    with pytest.raises(IllegalCommand):
        spec.validate(g, {"player": 0}, 99)
    spec.validate(g, {"player": 0}, 0)   # 不拋出


def test_partner_discarded_this_turn_excludes_earlier_turn_discards():
    g = game()
    g.state.players[0].discard.append("P-001")   # 不在 discarded_this_turn
    assert tree.PartnerDiscardedThisTurn().options(g, {"player": 0}) == []


def test_attach_partner_from_discard_matches_old_behavior():
    g = game()
    g.state.players[0].discard.append("P-001")
    g.state.players[0].discarded_this_turn.append("P-001")
    a = slot0(g, 0)
    batch = run(g, tree.AttachPartnerFromDiscard(), choice=0)
    assert a.partner == "P-001"
    assert "P-001" not in g.state.players[0].discard
    ev = without_seq([e for e in batch if e["type"] == "card_played"])
    assert ev == [{"type": "card_played", "player": 0, "card": "P-001",
                   "slot": a.uid, "zone": "partner", "from_discard": True}]


def test_attach_partner_from_discard_stale_choice_is_noop():
    g = game()
    batch = run(g, tree.AttachPartnerFromDiscard(), choice=0)   # 棄牌堆是空的
    assert batch == []


# ================================================================ 術卡第二批節點(S-016/S-017/S-031/S-033/S-039)

def test_add_defense_self_bonus_keeps_legacy_event_source():
    g = game()
    start_battle_for_leaf_test(g)
    batch = run(g, tree.AddDefenseSelfBonus(amount=1000))
    assert without_seq(batch) == [{"type": "effect_applied", "source": "defense_bonus", "amount": 1000}]
    assert g.state.battle.data["defense_self_bonus"] == 1000


def test_add_attack_self_bonus_keeps_legacy_event_source():
    g = game()
    start_battle_for_leaf_test(g)
    batch = run(g, tree.AddAttackSelfBonus(amount=2000))
    assert without_seq(batch) == [{"type": "effect_applied", "source": "attack_bonus", "amount": 2000}]
    assert g.state.battle.data["attack_spell_bonus"] == 2000


def test_self_bonus_nodes_without_battle_are_noop():
    g = game()
    assert run(g, tree.AddDefenseSelfBonus(amount=1000)) == []
    assert run(g, tree.AddAttackSelfBonus(amount=2000)) == []


def test_mark_injured_mamodo_discarded_sets_flag_without_event():
    g = game()
    start_battle_for_leaf_test(g)
    assert run(g, tree.MarkInjuredMamodoDiscarded()) == []
    assert g.state.battle.data["injure_to_discard"] is True


def test_add_power_to_all_opponent_mamodo_one_modifier_per_slot():
    from gash.engine.state import DUR_UNTIL_END_NEXT_TURN
    g = game()
    extra = give(g, 1, "M-002")
    batch = run(g, tree.AddPowerToAllOpponentMamodo(amount=-2000, duration=DUR_UNTIL_END_NEXT_TURN))
    assert [e["type"] for e in batch] == ["modifier_added", "modifier_added"]
    mods = g.state.modifiers
    assert sorted(m.target_slot for m in mods) == sorted([slot0(g, 1).uid, extra.uid])
    assert all((m.kind, m.owner, m.target_player, m.amount, m.source)
               == ("power", 0, 1, -2000, "T-000") for m in mods)


def test_opponent_partnered_mamodo_options_and_validate():
    g = game()
    assert tree.OpponentPartneredMamodo().options(g, {"player": 0}) == []
    target = slot0(g, 1)
    target.partner = "P-001"
    spec = tree.OpponentPartneredMamodo()
    assert spec.options(g, {"player": 0}) == [{"value": target.uid, "card": "P-001"}]
    spec.validate(g, {"player": 0}, target.uid)
    with pytest.raises(IllegalCommand):
        spec.validate(g, {"player": 0}, slot0(g, 0).uid)   # 自己的魔物不是合法目標


def test_discard_chosen_partner_and_stale_target_noop():
    g = game()
    target = slot0(g, 1)
    target.partner = "P-001"
    run(g, tree.DiscardChosenPartner(), choice=target.uid)
    assert target.partner is None and "P-001" in g.state.players[1].discard
    assert run(g, tree.DiscardChosenPartner(), choice=target.uid) == []   # 已無夥伴:無效果


# ================================================================ rider 新掛鉤(on_win / on_defense_damaged)與 damage_bonus

def test_reduce_opponent_mp_floors_at_zero():
    g = game()
    g.state.players[1].mp = 2
    batch = run(g, tree.ReduceOpponentMp(amount=3))
    assert g.state.players[1].mp == 0
    assert [e["type"] for e in batch] == ["mp_changed"]


def test_gain_mp_per_damage_scales_and_zero_is_silent():
    g = game()
    g.state.players[0].mp = 0
    run(g, tree.GainMpPerDamage(per_point=2), amount=3)
    assert g.state.players[0].mp == 6
    assert run(g, tree.GainMpPerDamage(per_point=2), amount=0) == []


def test_damage_bonus_spec_threshold():
    from types import SimpleNamespace
    spec = tree.DamageBonusIfAttackTotalAtLeast(threshold=8000, bonus=2)
    assert spec(None, SimpleNamespace(data={"attack_total": 8000})) == 2
    assert spec(None, SimpleNamespace(data={"attack_total": 7999})) == 0
    assert spec(None, SimpleNamespace(data={})) == 0
    with pytest.raises(FrozenInstanceError):
        spec.bonus = 3


def test_rider_on_win_and_on_defense_damaged_accept_trees():
    reg.spell_rider("T-920", on_win=Record("WIN"), on_defense_damaged=Record("HURT", "amount"))
    rider = reg.SPELL_RIDERS["T-920"]
    g = game()
    rider.on_win(g, [], 0)
    rider.on_defense_damaged(g, [], 1, 3)
    assert LOG == ["WIN", ("HURT", 3)]
    assert {("T-920", "rider.on_win"), ("T-920", "rider.on_defense_damaged")} <= tree.TREE_HOOKS


def test_rider_hook_rejects_unsupported_hook_name():
    with pytest.raises(ValueError, match="不支援效果樹"):
        tree.rider_hook("T-921", "damage_bonus", Nothing())
    assert ("T-921", "rider.damage_bonus") not in tree.TREE_HOOKS


def test_spell_rider_rejects_tree_in_non_effect_field_without_partial_state():
    before = snapshot()
    with pytest.raises(ValueError, match="不是效果掛鉤"):
        reg.spell_rider("T-922", on_damage=Nothing(), damage_bonus=Nothing())
    assert snapshot() == before and "T-922" not in reg.SPELL_RIDERS


# ================================================================ E-020:對手擲幣 / 指定 MP 對象

def test_coin_flipper_opponent_flips_but_ctx_player_is_owner():
    g = game()
    g.state.players[0].mp = g.state.players[1].mp = 0
    g.rng = StrictRng(HEADS)
    batch = run(g, Coin(flipper="opponent", then=tree.GainMp(amount=3, target="opponent")))
    assert [e["player"] for e in batch if e["type"] == "coin_flipped"] == [1]
    assert (g.state.players[0].mp, g.state.players[1].mp) == (0, 3)


def test_coin_flipper_opponent_m012_is_asked_to_opponent():
    g = game()
    give(g, 1, "M-012")
    g.rng = StrictRng(TAILS)
    run(g, coin_root_with_flipper("opponent"))
    assert g.state.pending.kind == "coin_confirm" and g.state.pending.player == 1


def coin_root_with_flipper(flipper):
    return Sequence(steps=(Record("A"),
                           Coin(count=1, flipper=flipper, then=Record("HEADS"), otherwise=Record("TAILS")),
                           Record("B")))


def test_gain_mp_targets():
    g = game()
    g.state.players[0].mp = g.state.players[1].mp = 0
    run(g, tree.GainMp(amount=3))
    run(g, tree.GainMp(amount=2, target="opponent"))
    assert (g.state.players[0].mp, g.state.players[1].mp) == (3, 2)


@pytest.mark.parametrize("make", [
    lambda: Coin(flipper="enemy"),
    lambda: tree.GainMp(amount=1, target="both"),
])
def test_invalid_who_rejected_at_construction(make):
    with pytest.raises(ValueError, match="'self' 或 'opponent'"):
        make()


# ================================================================ 事件卡第二批節點(E-002~E-025)

def test_restrict_both_players_order_is_player0_then_player1():
    from gash.engine.state import DUR_TURN, NO_SPELLS
    g = game()
    g.state.turn_player = 1
    events = run(g, tree.RestrictBothPlayers(flag=NO_SPELLS, duration=DUR_TURN), player=1)
    assert [e["target_player"] for e in events] == [0, 1]
    assert all(m.owner == 1 and m.flag == NO_SPELLS for m in g.state.modifiers)


def test_zero_both_players_mp_skips_event_for_zero():
    g = game()
    g.state.players[0].mp, g.state.players[1].mp = 5, 0
    events = run(g, tree.ZeroBothPlayersMp())
    assert without_seq(events) == [{"type": "mp_changed", "player": 0, "delta": -5, "mp": 0,
                                    "reason": "T-000"}]
    assert (g.state.players[0].mp, g.state.players[1].mp) == (0, 0)


def test_turn_pages_forward_opponent_and_peek():
    g = game()
    pos1 = g.state.players[1].pos
    events = run(g, Sequence(steps=(tree.TurnPagesForward(leaves=1, target="opponent"),
                                    tree.PeekOpponentOpenPages())))
    assert g.state.players[1].pos == pos1 + 2
    peek = [e for e in events if e["type"] == "pages_peeked"]
    assert len(peek) == 1 and peek[0]["viewer"] == 0 and peek[0]["player"] == 1


def test_own_injured_mamodo_spec():
    g = game()
    a = slot0(g, 0)
    spec = tree.OwnInjuredMamodo()
    assert spec.options(g, {"player": 0}) == []
    a.injured = True
    assert spec.options(g, {"player": 0}) == [{"value": a.uid, "card": a.top}]
    b = give(g, 0, "M-004")
    with pytest.raises(IllegalCommand):
        spec.validate(g, {"player": 0}, b.uid)          # 健康的魔物不合法


def test_opponent_mamodo_spec():
    g = game()
    x = slot0(g, 1)
    spec = tree.OpponentMamodo()
    assert spec.options(g, {"player": 0}) == [{"value": x.uid, "card": x.top}]
    with pytest.raises(IllegalCommand):
        spec.validate(g, {"player": 0}, slot0(g, 0).uid)  # 自己的魔物不合法


def test_borrow_partner_records_opponent_partner():
    g = game()
    x = slot0(g, 1)
    x.partner = "P-002"
    run(g, tree.BorrowPartner(), choice=x.uid)
    m = g.state.modifiers[-1]
    assert (m.kind, m.owner, m.target_player, m.data) == (
        "borrow_partner", 0, 0, {"slot_uid": x.uid, "card": "P-002"})


def test_discard_chosen_mamodo_and_gone_target_noop():
    g = game()
    b = give(g, 0, "M-004")
    run(g, tree.DiscardChosenMamodo(), slot=b.uid)
    assert b not in g.state.players[0].slots
    assert run(g, tree.DiscardChosenMamodo(), slot=b.uid) == []


def test_heal_first_injured_mamodo():
    g = game()
    assert run(g, tree.HealFirstInjuredMamodo()) == []
    a = slot0(g, 0)
    b = give(g, 0, "M-004", injured=True)
    c = give(g, 0, "M-002", injured=True)
    run(g, tree.HealFirstInjuredMamodo())
    assert (a.injured, b.injured, c.injured) == (False, False, True)


def test_lock_chosen_opponent_mamodo_keeps_legacy_event_shape():
    from gash.engine.state import MAMODO_LOCKED
    g = game()
    x = slot0(g, 1)
    events = run(g, tree.LockChosenOpponentMamodo(), choice=x.uid)
    ev = [e for e in events if e["type"] == "modifier_added"]
    assert len(ev) == 1 and ev[0]["target_slot"] is None       # 事件沿用遷移前的形狀
    m = g.state.modifiers[-1]
    assert (m.flag, m.target_player, m.target_slot) == (MAMODO_LOCKED, 1, x.uid)


# ================================================================ 從魔本選頁(E-012 / E-016 / E-017 / S-043 / S-048)

def set_book(g, player, **pages):
    """把 player 魔本的指定頁換成指定卡:set_book(g, 0, p5="M-024")。"""
    ps = g.state.players[player]
    b = list(ps.book)
    for k, v in pages.items():
        b[int(k[1:]) - 1] = v
    ps.book = tuple(b)


def test_has_options_as_when_condition():
    g = game()
    cond = tree.HasOptions(tree.OwnBookCopiesOf("M-025"))
    assert cond(g, 0) is False
    set_book(g, 0, p5="M-025")
    assert cond(g, 0) is True


def test_bound_and_own_field_has_conditions():
    g = game()
    assert tree.Bound("mode", "fuse").test(g, {"mode": "fuse"})
    assert not tree.Bound("mode", "fuse").test(g, {"mode": "split"})
    assert not tree.Bound("mode", "fuse").test(g, {})
    assert tree.OwnFieldHas("M-001").test(g, {"player": 0})
    assert not tree.OwnFieldHas("M-028").test(g, {"player": 0})


def test_opponent_book_cards_excludes_last_and_consumed():
    g = game()
    set_book(g, 1, p3="S-002")
    spec = tree.OpponentBookCards("spell", exclude_last=True)
    pages = [o["value"] for o in spec.options(g, {"player": 0})]
    assert 32 not in pages and 3 in pages
    g.state.players[1].consumed_pages.add(3)
    assert 3 not in [o["value"] for o in spec.options(g, {"player": 0})]
    assert 32 in [o["value"] for o in tree.OpponentBookCards("spell").options(g, {"player": 0})]


def test_own_book_copies_of_validate_rejects_other_pages():
    g = game()
    set_book(g, 0, p5="M-025")
    spec = tree.OwnBookCopiesOf("M-025")
    spec.validate(g, {"player": 0}, 5)
    with pytest.raises(IllegalCommand):
        spec.validate(g, {"player": 0}, 6)


def test_robnos_transform_mode_options_and_validate():
    g = game()
    spec = tree.RobnosTransformMode()
    assert spec.options(g, {"player": 0}) == []
    give(g, 0, "M-024")
    give(g, 0, "M-024")
    assert [o["value"] for o in spec.options(g, {"player": 0})] == ["fuse"]
    with pytest.raises(IllegalCommand, match="完全體"):
        spec.validate(g, {"player": 0}, "split")
    with pytest.raises(IllegalCommand, match="無效"):
        spec.validate(g, {"player": 0}, "other")
    give(g, 0, "M-025")
    assert [o["value"] for o in spec.options(g, {"player": 0})] == ["fuse", "split"]


def test_discard_own_mamodo_by_number_takes_first_n():
    g = game()
    a, b, c = give(g, 0, "M-024"), give(g, 0, "M-024"), give(g, 0, "M-024")
    run(g, tree.DiscardOwnMamodoByNumber(number="M-024", count=2))
    assert c in g.state.players[0].slots and a not in g.state.players[0].slots
    assert b not in g.state.players[0].slots


def test_place_mamodo_from_book_up_to_stops_when_book_runs_out():
    g = game()
    set_book(g, 0, p5="M-024")
    run(g, tree.PlaceMamodoFromBookUpTo(number="M-024", count=2))
    assert [s.top for s in g.state.players[0].slots].count("M-024") == 1
    assert 5 in g.state.players[0].consumed_pages


def test_stack_from_book_onto_missing_base_is_noop():
    g = game()
    set_book(g, 0, p5="M-027")
    assert run(g, tree.StackFromBookOnto(base="M-028"), page=5) == []
    assert 5 not in g.state.players[0].consumed_pages


def test_discard_from_opponent_book_pay_cost_uses_card_source():
    g = game()
    set_book(g, 1, p3="S-002")
    g.state.players[0].mp = 5
    events = run(g, tree.DiscardFromOpponentBookPayCost(), page=3)
    assert "S-002" in g.state.players[1].discard and 3 in g.state.players[1].consumed_pages
    assert g.state.players[0].mp == 5 - g.db["S-002"].cost
    assert {e["reason"] for e in events if "reason" in e} == {"T-000"}


# ================================================================ E-011 / E-018 / E-027 節點

def paid_reflip_root():
    return Sequence(steps=(
        Record("A"),
        tree.CoinWithPaidReflip(count=1, on=HeadsAtLeast(1), cost=2, prompt="t_retry",
                                then=Record("HEADS")),
        Record("B"),
    ))


def test_paid_reflip_loops_inside_node_and_ascends_once():
    g = game()
    g.state.players[0].mp = 10
    g.rng = StrictRng(TAILS, TAILS, HEADS)
    run(g, paid_reflip_root())
    assert LOG == ["A"] and pending(g) == ("t_retry", 0, [True, False])
    roundtrip_pending(g, CHOICE_KEY)
    submit(g, {"type": "choose", "player": 0, "value": True})
    assert LOG == ["A"] and pending(g)[0] == "t_retry"          # 第二次仍是反面
    submit(g, {"type": "choose", "player": 0, "value": True})
    assert LOG == ["A", "HEADS", "B"]                          # B 只執行一次
    assert g.state.players[0].mp == 10 - 2 - 2 and g.rng.calls == 3


def test_paid_reflip_stop_still_continues_siblings():
    g = game()
    g.state.players[0].mp = 10
    g.rng = StrictRng(TAILS)
    run(g, paid_reflip_root())
    submit(g, {"type": "choose", "player": 0, "value": False})
    assert LOG == ["A", "B"] and g.state.pending is None


def test_paid_reflip_without_mp_completes_immediately():
    g = game()
    g.state.players[0].mp = 1
    g.rng = StrictRng(TAILS)
    run(g, paid_reflip_root())
    assert LOG == ["A", "B"] and g.state.pending is None


def test_paid_reflip_rejects_invalid_value_and_keeps_pending():
    g = game()
    g.state.players[0].mp = 10
    g.rng = StrictRng(TAILS)
    run(g, paid_reflip_root())
    for bad in (1, "yes", None):
        with pytest.raises(IllegalCommand):
            submit(g, {"type": "choose", "player": 0, "value": bad})
        assert pending(g)[0] == "t_retry" and g.state.players[0].mp == 10


def test_paid_reflip_confirm_chain_then_retry_offer():
    g = game()
    g.state.players[0].mp = 10
    give(g, 0, "M-012")
    g.rng = StrictRng(TAILS)
    run(g, paid_reflip_root())
    assert pending(g)[0] == "coin_confirm"
    submit(g, {"type": "choose", "player": 0, "value": None})
    assert pending(g)[0] == "t_retry" and LOG == ["A"]


def test_validate_tree_checks_prompt_on_any_node():
    with pytest.raises(ValueError, match="CoinWithPaidReflip.prompt"):
        tree.validate_tree(tree.CoinWithPaidReflip(prompt="coin_confirm"))


def test_reduce_opponent_mp_unless_reduced_last_turn():
    g = game()
    st = g.state
    st.turn_no = 5
    st.players[1].mp = 20
    node = tree.ReduceOpponentMpUnlessReducedLastTurn(amount=4)
    run(g, node)
    assert st.players[1].mp == 16 and st.players[0].opp_mp_reduced_turns == {5}
    st.turn_no = 6
    events = run(g, node)                              # 直前回合(5)減過 → 減 0
    assert st.players[1].mp == 16
    assert without_seq(events) == [{"type": "effect_applied", "source": "T-000", "skipped": True}]
    assert st.players[0].opp_mp_reduced_turns == {5, 6}   # 減 0 也算使用過
    st.turn_no = 8
    run(g, node)                                       # 直前回合(7)沒用過 → 減 4
    assert st.players[1].mp == 12 and st.players[0].opp_mp_reduced_turns == {8}


def test_same_turn_reduction_does_not_erase_previous_turn_record():
    g = game()
    st = g.state
    st.players[1].mp = 20
    st.turn_no = 5
    run(g, tree.ReduceOpponentMp(amount=3))            # 第 5 回合用 S-020 之類的效果
    st.turn_no = 6
    run(g, tree.ReduceOpponentMp(amount=3))            # 第 6 回合又用一次
    before = st.players[1].mp
    run(g, tree.ReduceOpponentMpUnlessReducedLastTurn(amount=4))
    assert st.players[1].mp == before                   # 第 5 回合的紀錄仍在 → 減 0


def test_zero_both_players_mp_counts_as_reduction_only_if_opponent_had_mp():
    g = game()
    st = g.state
    st.players[1].mp = 0
    run(g, tree.ZeroBothPlayersMp())
    assert st.players[0].opp_mp_reduced_turns == set()
    st.players[1].mp = 1
    run(g, tree.ZeroBothPlayersMp())
    assert st.players[0].opp_mp_reduced_turns == {st.turn_no}


def test_when_otherwise_branch_and_condition_checked_once():
    g = game()
    run(g, When(cond=tree.Bound("x", 1), then=Record("T"), otherwise=Record("O")), x=2)
    assert LOG == ["O"]


def test_as_opponent_swaps_player_for_subtree_only():
    g = game()
    run(g, Sequence(steps=(
        tree.AsOpponent(then=Record("IN", "player")),
        Record("OUT", "player"),
    )))
    assert LOG == [("IN", 1), ("OUT", 0)]


def test_as_opponent_restores_player_after_async_resume():
    g = game()
    x = slot0(g, 1)
    give(g, 1, "M-004")
    run(g, Sequence(steps=(
        tree.AsOpponent(then=Choose(target=OwnMamodo(), bind="s", prompt="t_pick",
                                    then=Record("IN", "player"))),
        Record("OUT", "player"),
    )))
    assert pending(g)[:2] == ("t_pick", 1)                  # 對手決定
    roundtrip_pending(g, CHOICE_KEY)
    submit(g, {"type": "choose", "player": 1, "value": x.uid})
    assert LOG == [("IN", 1), ("OUT", 0)]                   # 恢復後外層仍是效果擁有者


def test_discard_other_partners_keeps_chosen():
    g = game()
    a = slot0(g, 0)
    a.partner = "P-001"
    b = give(g, 0, "M-004", partner="P-002")
    run(g, tree.DiscardOtherPartners(), keep=b.uid)
    assert a.partner is None and b.partner == "P-002"


def test_attachable_partner_pages_and_slots_specs():
    from .test_cards import book
    g = game(book0=book())                                  # 預設牌組本身就有夥伴卡,改用空白魔本
    set_book(g, 0, p9="P-001", p10="P-002")               # P-002 為レイコム家族,場上沒有 → 不可裝
    assert [o["value"] for o in tree.AttachablePartnerPagesInOwnBook().options(g, {"player": 0})] == [9]
    m16 = give(g, 0, "M-016")
    slots = tree.SlotsForBookPartner().options(g, {"player": 0, "page": 9})
    assert [o["value"] for o in slots] == [slot0(g, 0).uid, m16.uid]
    with pytest.raises(IllegalCommand):
        tree.SlotsForBookPartner().validate(g, {"player": 0, "page": 9}, slot0(g, 1).uid)

@dataclass(frozen=True)
class SetCtx(tree.Effect):
    """測試用:把 ctx[key] 設成 value(模擬 then 分支改變了條件依據的狀態)。"""
    key: str = ""
    value: object = None

    def run(self, rt, ctx, path):
        ctx[self.key] = self.value
        LOG.append(("SET", self.value))
        return True


def test_when_condition_evaluated_once_even_if_then_changes_it():
    g = game()
    run(g, When(cond=tree.Bound("x", 1), then=SetCtx("x", 2), otherwise=Record("O")), x=1)
    assert LOG == [("SET", 2)]                               # otherwise 不會再被執行



# ================================================================ 魔物 / 夥伴卡的掛鉤入口

def test_activated_tree_keeps_engine_params_and_passes_self_slot():
    reg.activated("T-930", mode="mp", mp_cost=2, timing="battle", effect=Record("ACT", "self_slot"))
    spec = reg.ACTIVATED["T-930"]
    assert (spec.mode, spec.mp_cost, spec.timing, spec.per_game) == ("mp", 2, "battle", False)
    g = game()
    spec.handler(g, [], 0, slot0(g, 0))
    assert LOG == [("ACT", slot0(g, 0).uid)]
    assert ("T-930", "activated") in tree.TREE_HOOKS


def test_activated_invalid_kwarg_leaves_no_partial_state():
    before = (dict(tree.EFFECTS), set(tree.TREE_HOOKS), dict(reg.ACTIVATED))
    with pytest.raises(TypeError):
        reg.activated("T-931", mode="mp", mp_cots=2, effect=Nothing())
    assert (dict(tree.EFFECTS), set(tree.TREE_HOOKS), dict(reg.ACTIVATED)) == before


def test_activated_tree_and_decorator_conflict_both_ways():
    @reg.activated("T-932", mode="declare")
    def legacy(game, batch, player, slot):
        pass
    with pytest.raises(ValueError):
        reg.activated("T-932", mode="declare", effect=Nothing())
    reg.activated("T-933", mode="declare", effect=Nothing())
    with pytest.raises(ValueError, match="已以效果樹註冊"):
        @reg.activated("T-933", mode="declare")
        def legacy2(game, batch, player, slot):
            pass


@pytest.mark.parametrize("hook,table", [("on_play", "ON_PLAY"), ("on_discard", "ON_DISCARD"),
                                        ("start_phase", "START_PHASE")])
def test_slot_hooks_accept_trees(hook, table):
    getattr(reg, hook)("T-934", effect=Record("H", "self_slot"))
    g = game()
    getattr(reg, table)["T-934"](g, [], 0, slot0(g, 0))
    assert LOG == [("H", slot0(g, 0).uid)]
    with pytest.raises(ValueError):
        getattr(reg, hook)("T-934", effect=Nothing())


def test_trigger_tree_gets_event_in_ctx():
    reg.trigger("T-935", "t_event", effect=Record("TRIG", "event"))
    number, handler = reg.TRIGGERS["t_event"][-1]
    g = game()
    handler(g, [], 0, slot0(g, 0), {"type": "t_event", "x": 1})
    assert number == "T-935" and LOG == [("TRIG", {"type": "t_event", "x": 1})]
    with pytest.raises(ValueError):
        @reg.trigger("T-935", "t_event")
        def legacy(game, batch, owner, slot, ev):
            pass


def test_value_hooks_register_specs_and_reject_duplicates():
    reg.static_power("T-936", value=tree.SelfPowerBonus(amount=1000, when=tree.SelfInjured()))
    fn = reg.STATIC_POWER["T-936"]
    g = game()
    s = slot0(g, 0)
    assert fn(g, 0, s) == 0                               # 頂層不是 T-936
    s.stack.append("T-936")
    assert fn(g, 0, s) == 0
    s.injured = True
    assert fn(g, 0, s) == 1000
    with pytest.raises(ValueError):
        reg.static_power("T-936", value=tree.SelfPowerBonus(amount=1, when=tree.SelfInjured()))
    reg.damage_immunity("T-937", check=tree.Never())
    reg.spell_compat("T-937", check=tree.Never())
    assert reg.DAMAGE_IMMUNITY["T-937"] == tree.Never() == reg.SPELL_COMPAT["T-937"]


def test_self_in_battle_as_and_simple_slot_queries():
    from gash.engine.state import BattleState
    g = game()
    s = slot0(g, 0)
    assert not tree.SelfInBattleAs("attack")(g, 0, s)
    g.state.battle = BattleState(attacker=0, step="defense", attack_page=1, attack_spell="S-001",
                                 attack_slot=s.uid)
    assert tree.SelfInBattleAs("attack")(g, 0, s) and not tree.SelfInBattleAs("defense")(g, 0, s)
    assert tree.OwnMamodoAtLeast(1)(g, 0, s) and not tree.OwnMamodoAtLeast(2)(g, 0, s)
    g.state.players[0].pos = 32
    assert tree.OwnBookAtLastPage()(g, 0, s) and not tree.Never()(g, 0, s)


def test_self_slot_effect_nodes():
    from gash.engine.state import DUR_BATTLE
    g = game()
    s = slot0(g, 0)
    run(g, tree.IncreaseSelfDamage(amount=1, duration=DUR_BATTLE), self_slot=s.uid)
    run(g, tree.PreventDamageToSelf(duration=DUR_BATTLE), self_slot=s.uid)
    assert [(m.kind, m.target_slot, m.amount) for m in g.state.modifiers] == [
        ("damage_delta", s.uid, 1), ("no_damage", s.uid, 0)]
    run(g, tree.ScheduleNextSpellBonus(mamodo="スギナ", power_delta=-1000, cost_delta=-1))
    run(g, tree.ScheduleSkipEndFlip())
    assert [(sb.kind, sb.data) for sb in g.state.standby] == [
        ("spell_bonus", {"mamodo": "スギナ", "power_delta": -1000, "cost_delta": -1,
                         "expires": "next_battle"}),
        ("skip_end_flip", {})]


# ================================================================ 魔物卡第二批(M-011 ~ M-031)

def test_all_and_has_options_with_slot():
    g = game()
    s = slot0(g, 0)
    cond = tree.All(tree.SelfHasNoPartner(), tree.HasOptions(tree.OwnOpenPages()))
    assert cond(g, 0, s) is True
    s.partner = "P-001"
    assert cond(g, 0, s) is False
    assert tree.All()(g, 0, s) is True


def test_open_and_earlier_page_specs():
    g = game()
    ps = g.state.players[0]
    ps.pos = 4
    assert [o["value"] for o in tree.OwnOpenPages().options(g, {"player": 0})] == [4, 5]
    earlier = [o["value"] for o in tree.OwnEarlierPages().options(g, {"player": 0})]
    assert 1 not in earlier and earlier == [p for p in (2, 3) if p not in ps.consumed_pages]
    with pytest.raises(IllegalCommand):
        tree.OwnEarlierPages().validate(g, {"player": 0}, 4)


def test_swap_book_pages_emits_effect_applied():
    g = game()
    ps = g.state.players[0]
    ps.book = list(ps.book)
    a, b = ps.card_at(2), ps.card_at(4)
    events = run(g, tree.SwapBookPages(), open=4, earlier=2)
    assert (ps.card_at(2), ps.card_at(4)) == (b, a)
    assert without_seq(events) == [{"type": "effect_applied", "source": "T-000", "pages": [4, 2]}]


def test_own_book_partner_named_matches_name_not_family():
    from .test_cards import book
    g = game(book0=book())
    set_book(g, 0, p9="P-001", p10="P-010")              # 兩張都是「高嶺清麿」、同家族
    spec = tree.OwnBookPartnerNamed("高嶺清麿")
    assert [o["value"] for o in spec.options(g, {"player": 0})] == [9, 10]
    assert tree.OwnBookPartnerNamed("大海恵").options(g, {"player": 0}) == []


def test_opponent_injured_mamodo_and_discard():
    g = game()
    x = slot0(g, 1)
    assert tree.OpponentInjuredMamodo().options(g, {"player": 0}) == []
    x.injured = True
    assert tree.OpponentInjuredMamodo().options(g, {"player": 0}) == [{"value": x.uid, "card": x.top}]
    run(g, tree.DiscardChosenOpponentMamodo(), choice=x.uid)
    assert x not in g.state.players[1].slots
    assert run(g, tree.DiscardChosenOpponentMamodo(), choice=x.uid) == []


def test_detached_from_self_condition():
    cond = tree.DetachedFromSelf("M-027")
    assert cond.test(None, {"self_slot": 5, "event": {"slot": 5, "detached": "M-027"}})
    assert not cond.test(None, {"self_slot": 5, "event": {"slot": 6, "detached": "M-027"}})
    assert not cond.test(None, {"self_slot": 5, "event": {"slot": 5, "detached": "M-001"}})


def test_can_use_spells_with_attr():
    g = game()
    wood = next(c for c in g.db.values() if c.type == "spell" and c.attr_name == "木")
    other = next(c for c in g.db.values() if c.type == "spell" and c.attr_name != "木")
    spec = tree.CanUseSpellsWithAttr("木")
    assert spec(g, 0, slot0(g, 0), wood) and not spec(g, 0, slot0(g, 0), other)


def test_data_registrations_reject_duplicates(monkeypatch):
    for name in ("STACK_ON", "MAX_COPIES", "MAMODO_ATTACK", "JAMMER"):
        monkeypatch.setattr(reg, name, dict(getattr(reg, name)))
    monkeypatch.setattr(reg, "SPELL_ONLY_STACK", set(reg.SPELL_ONLY_STACK))
    monkeypatch.setattr(reg, "DETACH_KEEP_UNDER", set(reg.DETACH_KEEP_UNDER))
    reg.stack_on("T-960", base=("T-961",), spell_only=True, detach_keep_under=True)
    assert reg.STACK_ON["T-960"] == {"T-961"}
    assert "T-960" in reg.SPELL_ONLY_STACK and "T-960" in reg.DETACH_KEEP_UNDER
    reg.max_copies("T-960", 2)
    reg.mamodo_attack("T-960", mp_cost=1, power=5000, damage=2)
    assert reg.MAMODO_ATTACK["T-960"] == {"mp_cost": 1, "power": 5000, "damage": 2}
    reg.jammer("T-960", mp_cost=2)
    assert reg.JAMMER["T-960"] == {"mp_cost": 2}
    for call in (lambda: reg.jammer("T-960", mp_cost=1),
                 lambda: reg.stack_on("T-960", base=()), lambda: reg.max_copies("T-960", 3),
                 lambda: reg.mamodo_attack("T-960", mp_cost=0, power=0, damage=0)):
        with pytest.raises(ValueError):
            call()


def test_discarded_cards_to_return_spec_offers_skip_only_with_targets():
    g = game()
    ps = g.state.players[0]
    spec = tree.DiscardedCardsToReturn(numbers=("M-024", "M-025"))
    ps.discard[:] = ["M-001", "M-024"]
    ps.consumed_pages.clear()
    assert spec.options(g, {"player": 0}) == []                      # 沒有空頁
    ps.consumed_pages.add(5)
    assert spec.options(g, {"player": 0}) == [{"value": 1, "card": "M-024"},
                                              {"value": None, "label": "skip"}]
    spec.validate(g, {"player": 0}, None)
    with pytest.raises(IllegalCommand):
        spec.validate(g, {"player": 0}, 0)                          # M-001 不是羅布諾斯


def test_return_discard_to_book_and_stale_noop():
    g = game()
    ps = g.state.players[0]
    ps.book = list(ps.book)
    ps.discard[:] = ["M-024"]
    ps.consumed_pages.add(9)
    assert [o["value"] for o in tree.OwnEmptyBookPages().options(g, {"player": 0})][-1] == 9
    events = run(g, tree.ReturnDiscardToBook(), card=0, page=9)
    assert ps.card_at(9) == "M-024" and 9 not in ps.consumed_pages and ps.discard == []
    assert [e["type"] for e in events] == ["card_returned_to_book"]
    assert run(g, tree.ReturnDiscardToBook(), card=0, page=9) == []   # 已放回:無效果


def test_spell_uses_per_turn_while_copies():
    g = game()
    spec = tree.SpellUsesPerTurnWhileCopies(spell="ビライツ", uses=2, number="M-024", copies=2)
    biraitsu, other = g.db["S-042"], g.db["S-001"]
    assert spec(g, 0, biraitsu) is None                       # 場上沒有分身體
    give(g, 0, "M-024")
    assert spec(g, 0, biraitsu) is None                       # 只有 1 隻
    give(g, 0, "M-024")
    assert spec(g, 0, biraitsu) == 2 and spec(g, 0, other) is None


# ================================================================ 夥伴卡(P-001 ~ P-019)

def _battle(g, attacker, attack_slot, attack_spell="S-001"):
    from gash.engine.state import BattleState
    g.state.battle = BattleState(attacker=attacker, step="effects", attack_page=2,
                                 attack_spell=attack_spell, attack_slot=attack_slot)
    return g.state.battle


def test_own_attack_by_judges_by_attacking_mamodo():
    g = game()
    brago = give(g, 0, "M-005")
    cond = tree.OwnAttackBy("ブラゴ")
    assert cond(g, 0) is False                                    # 不在戰鬥中
    _battle(g, 0, brago.uid)
    assert cond(g, 0) is True and cond(g, 1) is False             # 對手不是攻方
    g.state.battle.attack_slot = slot0(g, 0).uid                  # 改由ガッシュ攻擊
    assert cond(g, 0) is False


def test_no_battle_damage_modifier_from_only_counts_same_source_this_battle():
    from gash.engine.effects.primitives import add_modifier
    from gash.engine.state import DUR_BATTLE, DUR_TURN
    g = game()
    cond = tree.NoBattleDamageModifierFrom("P-003")
    add_modifier(g, [], kind="damage_delta", source="P-004", owner=0, duration=DUR_BATTLE, amount=2)
    add_modifier(g, [], kind="damage_delta", source="P-003", owner=0, duration=DUR_TURN, amount=2)
    assert cond(g, 0) is True
    add_modifier(g, [], kind="damage_delta", source="P-003", owner=0, duration=DUR_BATTLE, amount=2)
    assert cond(g, 0) is False


def test_negate_opponent_spell_by_side():
    g = game()
    b = _battle(g, 0, slot0(g, 0).uid)
    attack, defense, any_ = (tree.CanNegateOpponentSpell(w) for w in ("attack", "defense", "any"))
    assert attack(g, 1) and any_(g, 1)
    assert not attack(g, 0) and not defense(g, 0) and not any_(g, 0)   # 防方沒有用術防禦
    b.defense_spell = "S-003"
    assert defense(g, 0) and not defense(g, 1)
    events = run(g, tree.NegateOpponentSpell("any"), player=0)          # 攻方:無效防禦
    assert b.defense_negated and not b.attack_negated
    assert [e["type"] for e in events] == ["defense_negated"]
    run(g, tree.NegateOpponentSpell("any"), player=1)                   # 防方:無效攻擊
    assert b.attack_negated
    assert not any_(g, 0) and not any_(g, 1)                             # 已被無效就不能再用
    b.attack_negated, b.attack_spell = False, None                      # 無術攻擊
    assert not attack(g, 1)


def test_negate_next_damage_this_battle_then_must_be_synchronous():
    with pytest.raises(ValueError, match="Standby.then"):
        tree.validate_tree(tree.NegateNextDamageThisBattle(
            number="M-010", then=Choose(target=OwnMamodo(), prompt="t_pick")))


def test_negate_next_damage_this_battle_schedules_battle_scoped_standby():
    g = game()
    run(g, tree.NegateNextDamageThisBattle(number="M-010"))
    assert g.state.standby == []                                  # 場上沒有 M-010:無效果
    koruru = give(g, 0, "M-009")
    koruru.stack.append("M-010")
    run(g, tree.NegateNextDamageThisBattle(number="M-010"))
    [sb] = g.state.standby
    assert (sb.kind, sb.data["slot_uid"], sb.data["expires"]) == ("negate_damage", koruru.uid, "battle")


def test_discard_top_mamodo_card_keeps_lower_card():
    g = game()
    koruru = give(g, 0, "M-009")
    koruru.stack.append("M-010")
    events = run(g, tree.DiscardTopMamodoCard(number="M-010"), shielded=koruru.uid)
    assert koruru.stack == ["M-009"] and g.state.players[0].discard[-1] == "M-010"
    assert [(e["type"], e["card"], e["zone"]) for e in events] == [("card_discarded", "M-010", "mamodo")]
    assert run(g, tree.DiscardTopMamodoCard(number="M-010"), shielded=koruru.uid) == []   # 頂層已不是
    alone = give(g, 0, "M-010")
    assert run(g, tree.DiscardTopMamodoCard(number="M-010"), shielded=alone.uid) == []    # 沒有下層


def test_turn_opponent_pages_counts_opponent_mamodo_cards_only():
    g = game()
    node = tree.TurnOpponentPagesPerMamodoCardDiscarded()
    opp = g.state.players[1]
    pos = opp.pos
    run(g, node, event={"type": "mamodo_discarded", "player": 0, "cards": ["M-001"]})     # 自己的
    run(g, node, event={"type": "card_discarded", "player": 1, "card": "P-006"})          # 夥伴卡
    run(g, node, event={"type": "card_discarded", "player": 1, "card": "S-001"})          # 術卡
    assert opp.pos == pos
    run(g, node, event={"type": "mamodo_discarded", "player": 1, "cards": ["M-009", "M-010"]})
    assert opp.pos == pos + 2 * 2
    run(g, node, event={"type": "card_discarded", "player": 1, "card": "M-002"})
    assert opp.pos == pos + 2 * 3


def test_reduce_opponent_mp_per_page_turned_back():
    g = game()
    node = tree.ReduceOpponentMpPerPageTurnedBack(per_page=2)
    g.state.players[1].mp = 10
    run(g, node, event={"type": "pages_turned", "player": 1, "count": 2})    # 往前翻
    run(g, node, event={"type": "pages_turned", "player": 0, "count": -1})   # 自己回翻
    assert g.state.players[1].mp == 10 and not g.state.players[0].opp_mp_reduced_turns
    run(g, node, event={"type": "pages_turned", "player": 1, "count": -2})
    assert g.state.players[1].mp == 6
    assert g.state.turn_no in g.state.players[0].opp_mp_reduced_turns       # 算「減少對手 MP」的效果


def test_steal_opponent_mp_gains_only_what_was_reduced():
    # 効果文:相手のＭＰを3へらす。そうしたなら、へらした数と同じ数、自分のＭＰをふやす。
    g = game()
    g.state.players[0].mp, g.state.players[1].mp = 0, 2
    run(g, tree.StealOpponentMp(amount=3))
    assert (g.state.players[0].mp, g.state.players[1].mp) == (2, 0)


def test_set_power_zero_this_turn_gone_target_noop():
    g = game()
    x = give(g, 1, "M-004")
    run(g, tree.SetPowerZeroThisTurn(), choice=x.uid)
    assert [(m.kind, m.target_slot) for m in g.state.modifiers] == [("power_zero", x.uid)]
    g.state.players[1].slots.remove(x)
    assert run(g, tree.SetPowerZeroThisTurn(), choice=x.uid) == []


def test_schedule_next_spell_bonus_optional_flag():
    g = game()
    run(g, tree.ScheduleNextSpellBonus(mamodo="スギナ", power_delta=-1000, cost_delta=-1, optional=True))
    run(g, tree.ScheduleNextSpellBonus(mamodo="フェイン", power_delta=4000))
    assert [sb.data.get("optional") for sb in g.state.standby] == [True, None]


# ================================================================ 登記與命名慣例(effect-tree spec)

EFFECTS_DIR = __import__("pathlib").Path(tree.__file__).parent


def test_node_and_function_names_have_no_card_numbers():
    import inspect
    import re
    names = [n for n, obj in vars(tree).items()
             if (inspect.isclass(obj) or inspect.isfunction(obj)) and getattr(obj, "__module__", "") == tree.__name__]
    assert names and not [n for n in names if re.search(r"[empsEMPS]_?\d{3}", n)]


CARD_FILES = {"events.py": "E", "mamodo.py": "M", "partners.py": "P", "spells.py": "S"}


def _card_sources():
    return {name: (EFFECTS_DIR / "cards" / name).read_text(encoding="utf-8") for name in CARD_FILES}


@pytest.mark.parametrize("name", sorted(CARD_FILES))
def test_registration_files_split_by_card_type_sorted_and_without_logic(name):
    import re
    source = _card_sources()[name]
    numbers = re.findall(r'^reg\.\w+\("([EMPS]-\d{3})"', source, re.M)
    assert numbers and {n[0] for n in numbers} == {CARD_FILES[name]}   # 只含該類別的卡
    assert numbers == sorted(numbers)                      # 依卡號排序,同一張卡的登記因此相鄰
    assert "lambda" not in source and not re.search(r"^\s*def ", source, re.M)


def test_effects_package_has_no_per_card_handler_files():
    assert {p.name for p in EFFECTS_DIR.glob("*.py")} == {"__init__.py", "registry.py", "primitives.py", "tree.py"}
    assert {p.name for p in (EFFECTS_DIR / "cards").glob("*.py")} == {"__init__.py", *CARD_FILES}


def _engine_choice_kinds():
    import re
    kinds = set()
    for path in (EFFECTS_DIR.parent / "engine.py", EFFECTS_DIR / "primitives.py"):
        text = path.read_text(encoding="utf-8")
        kinds |= set(re.findall(r'(?:PendingChoice|choose_or_auto)\((?:[^()]|\n)*?kind="(\w+)"', text))
    return kinds


def _tree_choice_kinds():
    import re
    return {k for source in _card_sources().values() for k in re.findall(r'prompt="([^"]+)"', source)}


def test_choice_kinds_have_no_card_numbers():
    import re
    kinds = _tree_choice_kinds()
    assert kinds and not [k for k in kinds if re.search(r"[empsEMPS]-?\d{3}", k)]


def test_every_choice_kind_has_i18n_title():
    root = EFFECTS_DIR.parents[3]
    titles = json.loads((root / "frontend" / "i18n" / "zh-TW.json").read_text(encoding="utf-8"))
    kinds = _tree_choice_kinds() | _engine_choice_kinds() | set(tree.RESERVED_KINDS)
    assert {"protect", "jammer_negate", "spell_discount"} <= kinds
    assert not [k for k in sorted(kinds) if f"choice.title.{k}" not in titles]
