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
    """同一局中效果樹註冊的卡(E-001)與仍是裝飾器註冊的卡(M-002 開始階段效果)都正常運作。"""
    from gash.engine.engine import slot_power
    from .test_cards import book
    assert ("E-001", "event") in tree.TREE_HOOKS                # 效果樹註冊
    assert "M-002" in reg.START_PHASE                          # 仍是裝飾器註冊(遷移後需換一張舊寫法的卡)
    assert not any(n == "M-002" for n, _ in tree.TREE_HOOKS)
    g = game(book0=book(first="M-002", p2="E-001"))
    s = slot0(g, 0)
    base = slot_power(g, 0, s)
    mp = g.state.players[0].mp
    submit(g, {"type": "flip_pages", "player": 0, "count": 0})
    assert mp <= 2 and g.state.players[0].mp == mp + 1           # M-002(舊寫法):MP≤2 → +1
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})   # E-001(樹)
    end_turn(g)
    submit(g, {"type": "flip_pages", "player": 1, "count": 0})
    assert slot_power(g, 0, s) == base + 3000                      # 待命於下回合開始階段觸發


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


def test_keep_one_partner_or_fetch_from_book_targets():
    g = game()
    a = slot0(g, 1)
    a.partner = "P-001"
    b = give(g, 1, "M-004", partner="P-002")
    run(g, tree.KeepOnePartnerOrFetchFromBook(target="opponent"))
    assert a.partner == "P-001" and b.partner is None
    with pytest.raises(ValueError):
        tree.KeepOnePartnerOrFetchFromBook(target="both")
