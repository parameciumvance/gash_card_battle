"""卡片效果樹註冊檔:依卡號排序,每卡的登記集中一處(多個掛鉤各一個 reg.xxx(...) 且相鄰),
效果邏輯在 tree.py 的節點。

排版規則(讓巢狀層次一眼看得出來):
- 第一行固定是 `reg.xxx("卡號", ...,`,方便依卡號掃描。
- 有子節點的容器節點(Choose / Coin / CoinWithPaidReflip / When / Standby / Sequence /
  AsOpponent,以及 opponent_then_self(...))一律換行,子節點縮排一層;
  該容器的收尾括號獨立一行,與開頭對齊。
- 沒有子節點的葉節點、條件、選項規格寫在同一行。
- 整張卡只有一個葉節點(或只有旗標 / 查詢規格)時,整個註冊寫成一行;參數太長時續行對齊。

只有旗標、沒有邏輯的術卡(如 counter / damage_cap / injure_instead)也一併列在這裡,讓註冊集中。
"""

from ..state import (
    DUR_BATTLE, DUR_TURN, DUR_UNTIL_END_NEXT_TURN, NO_ATTACK_SPELL, NO_MAMODO_EFFECTS,
    NO_PARTNER_EFFECTS, NO_SPELLS,
)
from . import registry as reg
from .tree import (
    AddAttackBonusPerHeads, AddAttackSelfBonus, AddDefenseSelfBonus, AddPower,
    AddPowerToAllOpponentMamodo, AdjustDefenseDamage, All, Always, AttachPartnerFromBookPage,
    AttachPartnerFromDiscard, AttachablePartnerPagesInOwnBook, BoostPartneredMamodo, BorrowPartner,
    Bound, CanNegateOpponentSpell, CanUseSpellNamed, CanUseSpellsWithAttr, Choose, Coin,
    CoinWithPaidReflip, DamageBonusIfAttackTotalAtLeast, DamageOpponentBookAndAllMamodo,
    DeployMamodoFromBook, DeployableMamodoInOwnBook, DetachedFromSelf, DisableBookProtection,
    DiscardChosenMamodo, DiscardChosenOpponentMamodo, DiscardChosenPartner,
    DiscardFromOpponentBook, DiscardFromOpponentBookPayCost, DiscardOtherPartners,
    DiscardOwnMamodoByNumber, DiscardTopMamodoCard, DiscardedCardsToReturn, DoubleAttackDamage,
    GainMp, GainMpPerDamage, GainMpPerHeads, GrantFullImmune, HasOptions, HeadsAtLeast, HeadsCount,
    HealFirstInjuredMamodo, HealSlot, ImmuneToSpellDamageAtMost, IncreaseAttackDamage,
    IncreaseSelfDamage, LockChosenOpponentMamodo, MakeAttackUndefendable,
    MakeNextAttackUndefendable, MarkInjuredMamodoDiscarded, NegateAttack,
    NegateNextDamageThisBattle, NegateOpponentSpell, Never, NextStartPhase,
    NoBattleDamageModifierFrom, Nothing, OpponentBookCards, OpponentInjuredMamodo, OpponentMamodo,
    OpponentOpenPagesLackDefenseSpell, OpponentPartneredMamodo, OwnAttackBy, OwnBookAtLastPage,
    OwnBookCopiesOf, OwnBookPartnerNamed, OwnEarlierPages, OwnEmptyBookPages, OwnFieldHas,
    OwnHasPartner, OwnInjuredMamodo, OwnMamodo, OwnMamodoAtLeast, OwnMamodoPowerBonus, OwnMpAtMost,
    OwnOpenPages, OwnPageTurnBackEffectAvailable, OwnPageTurnEffectAvailable, OwnPartneredMamodo,
    PartnerDiscardedThisTurn, PeekOpponentOpenPages, PlaceMamodoFromBookUpTo, PlayMamodoFromBook,
    PlayablePartnerInDiscard, PreventDamageToSelf, ProtectorsDiscardedThisTurn, ReduceOpponentMp,
    ReduceOpponentMpPerPageTurnedBack, ReduceOpponentMpUnlessReducedLastTurn, Ref,
    RestrictBothPlayers, RestrictOpponent, ReturnDiscardToBook, RevealOpponentBook,
    RobnosTransformMode, ScheduleInjureInsteadNextWin, ScheduleNextSpellBonus,
    ScheduleNoProtectBookNextBattle, ScheduleSkipEndFlip, ScheduleSpellFromAnyPage,
    SelfHasNoPartner, SelfHasPartner, SelfInBattleAs, SelfInjured, SelfPowerBonus, Sequence,
    SetPowerZeroThisTurn, SideIs, SlotsForBookPartner, SpellUsesPerTurnWhileCopies,
    SpellsCostZeroThisTurn, StackFromBookOnto, Standby, StealOpponentMp, SwapBookPages,
    TurnOpponentPagesPerMamodoCardDiscarded, TurnOwnPagesBackOncePerTurn, TurnOwnPagesOncePerTurn,
    TurnPagesBack, TurnPagesForward, When, ZeroBothPlayersMp, has_own_injured_mamodo,
    has_own_mamodo, has_partner_discarded_this_turn, has_two_or_more_mamodo, opponent_has_mamodo,
    opponent_has_partner, opponent_then_self,
)

# ================================================================ 事件卡

reg.event("E-001", when=has_own_mamodo, effect=Choose(
    OwnMamodo(), bind="slot", prompt="pick_own_mamodo",
    then=Standby(
        NextStartPhase(), expires="next_start",
        then=AddPower(amount=3000, duration=DUR_TURN, target=Ref("slot")),
    ),
))

reg.event("E-002", effect=RestrictBothPlayers(flag=NO_SPELLS, duration=DUR_UNTIL_END_NEXT_TURN))
reg.event("E-003", effect=GainMp(amount=2))
reg.event("E-004", effect=ZeroBothPlayersMp())

reg.event("E-005", effect=Coin(
    count=2, on=HeadsCount(2),
    then=TurnPagesBack(leaves=2),
    otherwise=When(
        HeadsCount(0),
        then=TurnPagesForward(leaves=2),
    ),
))

reg.event("E-006", when=has_own_mamodo, effect=Choose(
    OwnMamodo(), bind="slot", prompt="pick_own_mamodo",
    then=Coin(
        count=1, on=HeadsAtLeast(1),
        then=HealSlot(target=Ref("slot")),
        otherwise=AddPower(amount=1000, duration=DUR_TURN, target=Ref("slot")),
    ),
))

reg.event("E-007", when=has_own_injured_mamodo, effect=Choose(
    OwnInjuredMamodo(), bind="slot", prompt="pick_own_injured_mamodo",
    then=HealSlot(target=Ref("slot")),
))

reg.event("E-008", effect=RestrictBothPlayers(flag=NO_PARTNER_EFFECTS, duration=DUR_TURN))

reg.event("E-009", when=has_own_mamodo, effect=Choose(
    OwnMamodo(), bind="slot", prompt="pick_own_mamodo",
    then=AddPower(amount=3000, duration=DUR_TURN, target=Ref("slot")),
))

reg.event("E-010", when=opponent_has_partner, effect=Choose(
    OpponentPartneredMamodo(), bind="choice", prompt="pick_opponent_partner",
    then=BorrowPartner(),
))

reg.event("E-011", when=HasOptions(PlayablePartnerInDiscard()), effect=CoinWithPaidReflip(
    count=1, on=HeadsAtLeast(1), cost=2, prompt="paid_reflip",
    then=Choose(
        PlayablePartnerInDiscard(), bind="choice", prompt="pick_partner_in_discard",
        then=AttachPartnerFromDiscard(spec=PlayablePartnerInDiscard()),
    ),
))

reg.event("E-012", when=HasOptions(DeployableMamodoInOwnBook()), effect=Choose(
    DeployableMamodoInOwnBook(), bind="page", prompt="pick_mamodo_in_own_book",
    then=DeployMamodoFromBook(),
))

reg.event("E-013", effect=ScheduleNoProtectBookNextBattle())

reg.event("E-014", effect=Sequence(steps=(
    TurnPagesForward(leaves=1, target="opponent"),
    PeekOpponentOpenPages(),
)))

reg.event("E-015", when=has_own_mamodo, effect=Choose(
    OwnMamodo(), bind="slot", prompt="pick_own_mamodo",
    then=AddPower(amount=2000, duration=DUR_UNTIL_END_NEXT_TURN, target=Ref("slot")),
))

reg.event("E-016", when=HasOptions(OpponentBookCards("spell", exclude_last=True)), effect=Sequence(steps=(
    RevealOpponentBook(),
    Choose(
        OpponentBookCards("spell", exclude_last=True), bind="page", prompt="pick_opponent_book_card",
        then=DiscardFromOpponentBookPayCost(),
    ),
)))

reg.event("E-017", when=HasOptions(OpponentBookCards("event")), effect=Sequence(steps=(
    RevealOpponentBook(),
    Choose(
        OpponentBookCards("event"), bind="page", prompt="pick_opponent_book_card",
        then=DiscardFromOpponentBookPayCost(),
    ),
)))

reg.event("E-018", effect=ReduceOpponentMpUnlessReducedLastTurn(amount=4))

reg.event("E-019", when=has_own_mamodo, effect=Choose(
    OwnMamodo(), bind="slot", prompt="pick_own_mamodo",
    then=DiscardChosenMamodo(),
))

reg.event("E-020", effect=Sequence(steps=(
    GainMp(amount=3),
    Coin(
        count=1, flipper="opponent", on=HeadsAtLeast(1),
        then=GainMp(amount=3, target="opponent"),
    ),
)))

reg.event("E-021", when=has_two_or_more_mamodo, effect=Sequence(steps=(
    HealFirstInjuredMamodo(),
    GainMp(amount=2),
)))

reg.event("E-022", when=has_partner_discarded_this_turn, effect=Coin(
    count=1, on=HeadsAtLeast(1),
    then=Choose(
        PartnerDiscardedThisTurn(), bind="choice", prompt="pick_partner_in_discard",
        then=AttachPartnerFromDiscard(),
    ),
))

reg.event("E-023", effect=BoostPartneredMamodo(amount=2000, duration=DUR_UNTIL_END_NEXT_TURN))

reg.event("E-024", when=opponent_has_mamodo, effect=Choose(
    OpponentMamodo(), bind="choice", prompt="pick_opponent_mamodo",
    then=LockChosenOpponentMamodo(),
))

reg.event("E-025", effect=RestrictOpponent(flag=NO_MAMODO_EFFECTS, duration=DUR_TURN))

reg.event("E-026", effect=Coin(
    count=2, on=Always(),
    then=GainMpPerHeads(per_head=2),
))

reg.event("E-027", effect=opponent_then_self(When(
    OwnHasPartner(),
    then=Choose(
        OwnPartneredMamodo(), bind="keep", prompt="pick_partner_to_keep",
        then=DiscardOtherPartners(),
    ),
    otherwise=Choose(
        AttachablePartnerPagesInOwnBook(), bind="page", prompt="pick_partner_in_own_book",
        then=Choose(
            SlotsForBookPartner(), bind="slot", prompt="pick_mamodo_for_partner",
            then=AttachPartnerFromBookPage(),
        ),
    ),
)))

# ================================================================ 魔物卡
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

# ================================================================ 夥伴卡
# 「このカードを捨て札にする→」為 mode="discard"(引擎把此卡棄掉作為費用;E-010 借用時不棄)。
# 「某魔物の術 / 某魔物による」類效果以「使用術的魔物」判定,指示術由該魔物使用時也適用。

reg.activated("P-001", mode="discard", timing="nonbattle",
              effect=MakeNextAttackUndefendable(mamodo="ガッシュ・ベル"))
reg.activated("P-002", mode="discard", timing="nonbattle", effect=StealOpponentMp(amount=3))
reg.activated("P-003", mode="discard", timing="battle",
              condition=All(OwnAttackBy("ブラゴ"), NoBattleDamageModifierFrom("P-003")),
              effect=IncreaseAttackDamage(amount=2))
reg.activated("P-004", mode="discard", timing="battle",
              condition=All(OwnAttackBy("ゴフレ"), NoBattleDamageModifierFrom("P-004")),
              effect=DoubleAttackDamage())
reg.activated("P-005", mode="discard", timing="nonbattle", effect=SpellsCostZeroThisTurn(mamodo="スギナ"))

reg.activated("P-006", mode="discard", timing="battle", condition=OwnFieldHas("M-010"),
              effect=NegateNextDamageThisBattle(
    number="M-010",
    then=DiscardTopMamodoCard(number="M-010"),
))

reg.activated("P-007", mode="discard", timing="nonbattle",
              effect=ScheduleNextSpellBonus(mamodo="フェイン", power_delta=4000))

reg.activated("P-008", mode="discard", timing="nonbattle",
              condition=HasOptions(OpponentPartneredMamodo()), effect=Choose(
    OpponentPartneredMamodo(), bind="choice", prompt="pick_opponent_partner",
    then=DiscardChosenPartner(),
))

reg.activated("P-009", mode="discard", timing="battle", condition=CanNegateOpponentSpell("any"),
              effect=NegateOpponentSpell("any"))
reg.activated("P-010", mode="discard", timing="nonbattle", condition=OwnPageTurnEffectAvailable(),
              effect=TurnOwnPagesOncePerTurn(leaves=1))

reg.activated("P-011", mode="discard", timing="nonbattle",
              condition=HasOptions(OpponentMamodo()), effect=Choose(
    OpponentMamodo(), bind="choice", prompt="pick_opponent_mamodo",
    then=SetPowerZeroThisTurn(),
))

reg.activated("P-012", mode="discard", timing="nonbattle", effect=ProtectorsDiscardedThisTurn(mamodo="ブラゴ"))
reg.trigger("P-013", "mamodo_discarded", effect=TurnOpponentPagesPerMamodoCardDiscarded())
reg.trigger("P-013", "card_discarded", effect=TurnOpponentPagesPerMamodoCardDiscarded())
reg.activated("P-014", mode="discard", timing="nonbattle",
              effect=RestrictOpponent(flag=NO_ATTACK_SPELL, duration=DUR_TURN))
reg.activated("P-015", mode="discard", timing="nonbattle", effect=ScheduleSpellFromAnyPage(spell="ビライツ"))
reg.activated("P-016", mode="discard", timing="battle", condition=CanNegateOpponentSpell("attack"),
              effect=NegateOpponentSpell("attack"))
reg.activated("P-017", mode="discard", timing="battle", condition=CanNegateOpponentSpell("defense"),
              effect=NegateOpponentSpell("defense"))
reg.activated("P-018", mode="discard", timing="nonbattle", condition=OwnPageTurnBackEffectAvailable(),
              effect=TurnOwnPagesBackOncePerTurn(leaves=1))
reg.trigger("P-019", "pages_turned", effect=ReduceOpponentMpPerPageTurnedBack(per_page=2))

# ================================================================ 術卡
# S-022 セウシル / S-024 マ・セシルド / S-028 伏せろ!:防禦獲勝時將攻擊無效 = 防方獲勝本就使攻方
# 效果不解決,不需註冊(純資料驅動)。純香草術卡(攻/防獲勝→魔本傷害)同樣不需註冊:
# S-001 等第一彈香草術,以及第二彈 S-029 S-044 S-047 S-049 S-050 S-051 S-052 S-053 S-054 S-055。

reg.spell_rider("S-003", counter=True)

reg.spell_rider("S-004", on_damage=Coin(
    count=1, on=HeadsAtLeast(1),
    then=RestrictOpponent(flag=NO_SPELLS, duration=DUR_UNTIL_END_NEXT_TURN),
))

reg.spell_rider("S-007", on_damage=RestrictOpponent(flag=NO_PARTNER_EFFECTS, duration=DUR_UNTIL_END_NEXT_TURN))
reg.spell_rider("S-009", on_damage=RestrictOpponent(flag=NO_SPELLS, duration=DUR_UNTIL_END_NEXT_TURN))
reg.spell_rider("S-011", on_damage=RestrictOpponent(flag=NO_SPELLS, duration=DUR_UNTIL_END_NEXT_TURN))

reg.spell_rider("S-014", on_damage=Coin(
    count=1, on=HeadsAtLeast(1),
    then=RestrictOpponent(flag=NO_SPELLS, duration=DUR_UNTIL_END_NEXT_TURN),
))

reg.spell_rider("S-016", on_declare=When(
    SideIs("defense"),
    then=AddDefenseSelfBonus(amount=1000),
))

reg.spell_rider("S-017", on_declare=When(
    SideIs("attack"),
    then=AddAttackSelfBonus(amount=2000),
))

reg.spell_rider("S-019", on_win=MakeNextAttackUndefendable(), no_book_damage=True)
reg.spell_rider("S-020", on_win=ReduceOpponentMp(amount=3), no_book_damage=True)

reg.spell_rider("S-021", on_declare=When(
    SideIs("defense"),
    then=Coin(
        count=2, on=HeadsAtLeast(1),
        then=NegateAttack(),
    ),
))

reg.spell_rider("S-025", on_declare=When(
    SideIs("defense"),
    then=Coin(
        count=1, on=HeadsAtLeast(1),
        then=NegateAttack(),
    ),
))

reg.spell_nonbattle("S-026", effect=Coin(
    count=1, on=HeadsAtLeast(1),
    then=MakeNextAttackUndefendable(),
))

reg.spell_rider("S-027", on_declare=When(
    SideIs("defense"),
    then=Coin(
        count=2, on=HeadsAtLeast(1),
        then=AdjustDefenseDamage(amount=-1),
    ),
))

reg.spell_rider("S-030", counter=True)

reg.spell_rider("S-031", on_declare=When(
    SideIs("attack"),
    then=MarkInjuredMamodoDiscarded(),
))

reg.spell_rider("S-032", damage_cap=3)
reg.spell_rider("S-033", on_damage=AddPowerToAllOpponentMamodo(amount=-2000, duration=DUR_UNTIL_END_NEXT_TURN))
reg.spell_rider("S-034", damage_cap=4)

reg.spell_rider("S-035", on_declare=When(
    SideIs("attack"),
    then=Coin(
        count=2, on=HeadsAtLeast(2),
        then=DisableBookProtection(),
    ),
))

reg.spell_rider("S-036", on_win=DamageOpponentBookAndAllMamodo(), on_win_owns_damage=True)

reg.spell_rider("S-037", on_damage=Coin(
    count=1, on=HeadsAtLeast(1),
    then=GrantFullImmune(),
))

reg.spell_rider("S-038", on_damage=GrantFullImmune())

reg.spell_rider("S-039", on_damage=Choose(
    OpponentPartneredMamodo(), bind="choice", prompt="pick_opponent_partner",
    then=DiscardChosenPartner(),
))

reg.spell_rider("S-040", on_declare=When(
    SideIs("attack"),
    then=Coin(
        count=3, on=Always(),
        then=AddAttackBonusPerHeads(per_head=2000),
    ),
))

reg.spell_nonbattle("S-041", effect=Coin(
    count=1, on=HeadsAtLeast(1),
    then=GrantFullImmune(),
))

reg.spell_rider("S-042", damage_bonus=DamageBonusIfAttackTotalAtLeast(threshold=8000, bonus=2))

reg.spell_nonbattle("S-043", effect=Choose(
    RobnosTransformMode(), bind="mode", prompt="pick_transform_mode",
    then=Sequence(steps=(
        When(
            Bound("mode", "fuse"),
            then=Sequence(steps=(
                DiscardOwnMamodoByNumber(number="M-024", count=2),
                Choose(
                    OwnBookCopiesOf("M-025"), bind="page", prompt="pick_mamodo_in_own_book",
                    then=PlayMamodoFromBook(),
                ),
            )),
        ),
        When(
            Bound("mode", "split"),
            then=Sequence(steps=(
                DiscardOwnMamodoByNumber(number="M-025", count=1),
                PlaceMamodoFromBookUpTo(number="M-024", count=2),
            )),
        ),
    )),
))

reg.spell_rider("S-045", on_declare=When(
    SideIs("attack"),
    then=Coin(
        count=2, on=HeadsAtLeast(2),
        then=MakeAttackUndefendable(),
    ),
))

reg.spell_rider("S-046", on_declare=When(
    SideIs("attack"),
    then=Coin(
        count=1, on=HeadsAtLeast(1),
        then=MakeAttackUndefendable(),
    ),
))

reg.spell_nonbattle("S-048", effect=When(
    OwnFieldHas("M-028"),
    then=Choose(
        OwnBookCopiesOf("M-027"), bind="page", prompt="pick_mamodo_in_own_book",
        then=StackFromBookOnto(base="M-028"),
    ),
))

reg.spell_rider("S-056", on_defense_damaged=GainMpPerDamage(per_point=2))

reg.spell_nonbattle("S-057", effect=Coin(
    count=1, on=HeadsAtLeast(1),
    then=ScheduleInjureInsteadNextWin(),
))

reg.spell_rider("S-058", injure_instead=True)
