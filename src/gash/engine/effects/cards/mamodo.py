"""魔物卡(M-xxx)的效果登記。依卡號排序,排版規則見 `cards/__init__.py`。"""

from ...state import DUR_BATTLE, DUR_TURN, NO_SPELLS
from .. import registry as reg
from ..tree import (
    AddPower, All, AttachPartnerFromBookPage, Bound, CanUseSpellNamed, CanUseSpellsWithAttr, Choose,
    DetachedFromSelf, DiscardChosenOpponentMamodo, DiscardChosenPartner, DiscardFromOpponentBook,
    DiscardedCardsToReturn, GainMp, HasOptions, ImmuneToSpellDamageAtMost, IncreaseSelfDamage,
    Never, Nothing, OpponentBookCards, OpponentInjuredMamodo, OpponentOpenPagesLackDefenseSpell,
    OpponentPartneredMamodo, OwnBookAtLastPage, OwnBookPartnerNamed, OwnEarlierPages,
    OwnEmptyBookPages, OwnMamodoAtLeast, OwnMamodoPowerBonus, OwnMpAtMost, OwnOpenPages,
    PreventDamageToSelf, Ref, RestrictOpponent, ReturnDiscardToBook, RevealOpponentBook,
    ScheduleNextSpellBonus, ScheduleSkipEndFlip, SelfHasNoPartner, SelfHasPartner, SelfInBattleAs,
    SelfInjured, SelfPowerBonus, Sequence, SpellUsesPerTurnWhileCopies, SwapBookPages,
    TurnPagesForward, When,
)

# activated 的 mode / mp_cost / timing / per_game / condition 由引擎檢查,effect 只描述效果本身。

reg.activated("M-001", mode="mp", mp_cost=1, timing="battle", condition=SelfInBattleAs("attack"),
              effect=AddPower(amount=1000, duration=DUR_BATTLE, target=Ref("self_slot")))

reg.start_phase("M-002", effect=When(
    OwnMpAtMost(2),
    then=GainMp(amount=1),
))

reg.static_power("M-003", value=SelfPowerBonus(amount=1000, when=SelfInjured()))
reg.static_power("M-004", value=SelfPowerBonus(amount=1000, when=SelfHasPartner()))

reg.activated("M-005", mode="mp", mp_cost=2, timing="battle", condition=SelfInBattleAs("attack"),
              effect=IncreaseSelfDamage(amount=1, duration=DUR_BATTLE))

reg.on_play("M-006", effect=RestrictOpponent(flag=NO_SPELLS, duration=DUR_TURN))
reg.on_play("M-007", effect=TurnPagesForward(leaves=1, target="opponent"))
reg.stack_on("M-007", base=("M-006",))

reg.activated("M-008", mode="declare", timing="nonbattle",
              effect=ScheduleNextSpellBonus(mamodo="スギナ", power_delta=-1000, cost_delta=-1, optional=True))

reg.on_discard("M-009", effect=GainMp(amount=4))

reg.stack_on("M-010", base=("M-009",))
reg.activated("M-010", mode="mp", mp_cost=1, timing="battle", condition=SelfInBattleAs("defense"),
              effect=AddPower(amount=1000, duration=DUR_BATTLE, target=Ref("self_slot")))

reg.activated("M-011", mode="declare", timing="nonbattle", per_game=True,
              condition=HasOptions(OpponentBookCards("mamodo")), effect=Sequence(steps=(
    RevealOpponentBook(),
    Choose(
        OpponentBookCards("mamodo"), bind="page", prompt="pick_opponent_book_card",
        then=DiscardFromOpponentBook(),
    ),
)))

reg.activated("M-013", mode="mp", mp_cost=2, timing="battle", condition=SelfInjured(),
              effect=PreventDamageToSelf(duration=DUR_BATTLE))

reg.static_power("M-014", value=OwnMamodoPowerBonus(amount=1000, when=OwnMamodoAtLeast(2)))

reg.activated("M-015", mode="mp", mp_cost=5, timing="battle",
              effect=PreventDamageToSelf(duration=DUR_BATTLE))

reg.activated("M-016", mode="declare", timing="nonbattle", per_game=True,
              condition=All(HasOptions(OwnOpenPages()), HasOptions(OwnEarlierPages())), effect=Choose(
    OwnOpenPages(), bind="open", prompt="pick_own_open_page",
    then=Choose(
        OwnEarlierPages(), bind="earlier", prompt="pick_own_earlier_page",
        then=SwapBookPages(),
    ),
))

reg.activated("M-017", mode="mp", mp_cost=2, timing="battle", condition=SelfInBattleAs("attack"),
              effect=AddPower(amount=2000, duration=DUR_BATTLE, target=Ref("self_slot")))

reg.activated("M-018", mode="mp", mp_cost=1, timing="nonbattle", effect=When(
    OpponentOpenPagesLackDefenseSpell(),
    then=GainMp(amount=2),
))

# M-019 的「令對手重擲」在擲幣確認鏈(primitives.flip_coins)中詢問,不由玩家主動宣告
reg.activated("M-019", mode="declare", timing="any", condition=Never(), effect=Nothing())

reg.activated("M-020", mode="mp", mp_cost=1, timing="nonbattle",
              condition=All(SelfHasNoPartner(), HasOptions(OwnBookPartnerNamed("大海恵"))), effect=Choose(
    OwnBookPartnerNamed("大海恵"), bind="page", prompt="pick_partner_in_own_book",
    then=AttachPartnerFromBookPage(slot=Ref("self_slot")),
))

reg.activated("M-021", mode="mp", mp_cost=1, timing="nonbattle",
              condition=All(SelfHasNoPartner(), HasOptions(OwnBookPartnerNamed("窪塚泳太"))), effect=Choose(
    OwnBookPartnerNamed("窪塚泳太"), bind="page", prompt="pick_partner_in_own_book",
    then=AttachPartnerFromBookPage(slot=Ref("self_slot")),
))

reg.activated("M-022", mode="mp", mp_cost=5, timing="nonbattle",
              condition=HasOptions(OpponentPartneredMamodo()), effect=Choose(
    OpponentPartneredMamodo(), bind="choice", prompt="pick_opponent_partner",
    then=DiscardChosenPartner(),
))

reg.spell_compat("M-023", check=CanUseSpellsWithAttr("木"))
reg.max_copies("M-024", 2)
reg.spell_use_limit("M-024",
                    value=SpellUsesPerTurnWhileCopies(spell="ビライツ", uses=2, number="M-024", copies=2))

reg.on_play("M-025", effect=Sequence(steps=(
    Choose(
        DiscardedCardsToReturn(numbers=("M-024", "M-025")), bind="card", prompt="pick_card_in_own_discard",
        then=When(
            Bound("card", None),
            otherwise=Choose(
                OwnEmptyBookPages(), bind="page", prompt="pick_own_empty_page",
                then=ReturnDiscardToBook(),
            ),
        ),
    ),
    GainMp(amount=2),
)))

# M-026 為ジャマー:不能主動宣告,對手用完魔物的啟動效果後由引擎詢問是否支付 2MP 使其無效
reg.jammer("M-026", mp_cost=2)

reg.stack_on("M-027", base=("M-028",), spell_only=True, detach_keep_under=True)
reg.mamodo_attack("M-027", mp_cost=1, power=5000, damage=2)

reg.trigger("M-028", "stack_detached", effect=When(
    DetachedFromSelf("M-027"),
    then=TurnPagesForward(leaves=2, target="opponent"),
))

reg.spell_compat("M-029", check=CanUseSpellNamed(mamodo="ガッシュ・ベル", name="ザケル"))
reg.activated("M-029", mode="mp", mp_cost=7, timing="nonbattle",
              condition=HasOptions(OpponentInjuredMamodo()), effect=Choose(
    OpponentInjuredMamodo(), bind="choice", prompt="pick_opponent_injured_mamodo",
    then=DiscardChosenOpponentMamodo(),
))

reg.activated("M-030", mode="declare", timing="nonbattle", per_game=True, condition=OwnBookAtLastPage(),
              effect=ScheduleSkipEndFlip())

reg.damage_immunity("M-031", check=ImmuneToSpellDamageAtMost(total=6000))
