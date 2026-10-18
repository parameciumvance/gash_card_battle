"""事件卡(E-xxx)的效果登記。依卡號排序,排版規則見 `cards/__init__.py`。"""

from ...state import (
    DUR_TURN, DUR_UNTIL_END_NEXT_TURN, NO_MAMODO_EFFECTS, NO_PARTNER_EFFECTS, NO_SPELLS,
)
from .. import registry as reg
from ..tree import (
    AddPower, Always, AnyOf, AsOpponent, AttachablePartnerPagesInOwnBook, AttachPartnerFromBookPage,
    AttachPartnerFromDiscard, AwaitBookReviewEnd, BoostPartneredMamodo, BorrowPartner, Bound,
    Choose, Coin, CoinWithPaidReflip, DeployableMamodoInOwnBook, DeployMamodoFromBook,
    DiscardChosenMamodo, DiscardChosenPartner, DiscardedMamodoToReturn,
    DiscardFromOpponentBookPayCost, DiscardOtherPartners, EffectOptions, GainMp, GainMpPerHeads,
    GainMpReducedByOpponent, HasOptions, HeadsAtLeast, HeadsCount, HealAllOwnMamodo, HealSlot,
    LockChosenOpponentMamodo, NextStartPhase, OpponentBookCards, OpponentMamodo,
    OpponentPartneredMamodo, OrSkip, OwnEmptyBookPages, OwnHasPartner, OwnInjuredMamodo, OwnMamodo,
    OwnPartneredMamodo, PartnerDiscardedThisTurn, PeekOpponentOpenPages, PlayablePartnerInDiscard,
    PlayMamodoFromBook, ProtectAnyway, ReduceOpponentMpUnlessReducedLastTurn, Ref,
    RemoveRestrictions, RestrictBothPlayers, RestrictOpponent, RestrictOthersThanChosen,
    ReturnDiscardToBook, RevealOpponentBook, ScheduleEndPhaseMp, ScheduleNoProtectBookNextBattle,
    Sequence, SlotsForBookPartner, Standby, TurnPagesBack, TurnPagesForward, When,
    ZeroBothPlayersMp,
    has_own_injured_mamodo, has_own_mamodo, has_partner_discarded_this_turn, has_two_or_more_mamodo,
    mp_reduced_by_opponent, opponent_has_mamodo, opponent_then_self,
)


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

# 「このカードが場にある→」効果ではないパートナー:排除被動搭檔(P-013 / P-019)
reg.event("E-010", when=HasOptions(OpponentPartneredMamodo(usable_only=True)), effect=Choose(
    OpponentPartneredMamodo(usable_only=True), bind="choice", prompt="pick_opponent_partner",
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

# E-016 / E-017:對手魔書有沒有對象是檢視後才知道的資訊,不當使用條件;沒有時檢視後不棄、不減 MP
reg.event("E-016", effect=Sequence(steps=(
    RevealOpponentBook(),
    When(
        HasOptions(OpponentBookCards("spell", exclude_last=True)),
        then=Choose(
            OpponentBookCards("spell", exclude_last=True), bind="page", prompt="pick_opponent_book_card", auto_single=False,
            then=DiscardFromOpponentBookPayCost(),
        ),
        otherwise=AwaitBookReviewEnd(),
    ),
)))

reg.event("E-017", effect=Sequence(steps=(
    RevealOpponentBook(),
    When(
        HasOptions(OpponentBookCards("event")),
        then=Choose(
            OpponentBookCards("event"), bind="page", prompt="pick_opponent_book_card", auto_single=False,
            then=DiscardFromOpponentBookPayCost(),
        ),
        otherwise=AwaitBookReviewEnd(),
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

# 「片方または両方を、好きな順で」:先選第一個效果,完成後再問是否使用另一個(可不使用)
reg.event("E-021", when=has_two_or_more_mamodo, effect=Sequence(steps=(
    Choose(
        EffectOptions((("heal", "heal_injured", OwnInjuredMamodo()), ("mp", "gain_mp_2", None))),
        bind="first", prompt="pick_effect",
        then=When(
            Bound("first", "heal"),
            then=Choose(
                OwnInjuredMamodo(), bind="slot", prompt="pick_own_injured_mamodo",
                then=HealSlot(target=Ref("slot")),
            ),
            otherwise=When(
                Bound("first", "mp"),
                then=GainMp(amount=2),
            ),
        ),
    ),
    Choose(
        EffectOptions((("heal", "heal_injured", OwnInjuredMamodo()), ("mp", "gain_mp_2", None)),
                      after="first"),
        bind="second", prompt="pick_effect",
        then=When(
            Bound("second", "heal"),
            then=Choose(
                OwnInjuredMamodo(), bind="slot", prompt="pick_own_injured_mamodo",
                then=HealSlot(target=Ref("slot")),
            ),
            otherwise=When(
                Bound("second", "mp"),
                then=GainMp(amount=2),
            ),
        ),
    ),
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

# ---------------------------------------------------------------- 第三彈

reg.event("E-028", when=mp_reduced_by_opponent, effect=GainMpReducedByOpponent())

reg.event("E-030", when=HasOptions(OpponentPartneredMamodo(discard=True)), effect=Choose(
    OpponentPartneredMamodo(discard=True), bind="choice", prompt="pick_opponent_partner",
    then=DiscardChosenPartner(),
))

reg.event("E-031", effect=ProtectAnyway())
reg.event("E-032", effect=GainMp(amount=5))

reg.event("E-033", when=HasOptions(DiscardedMamodoToReturn()), effect=Choose(
    DiscardedMamodoToReturn(), bind="card", prompt="pick_card_in_own_discard",
    then=Choose(
        OwnEmptyBookPages(), bind="page", prompt="pick_own_empty_page",
        then=ReturnDiscardToBook(),
    ),
))

# 「それぞれ1枚まで」:先魔物、後搭檔,各自可不選(大海恵可裝到剛放出的ティオ);兩者都選不到時不能使用
reg.event("E-034", when=AnyOf(HasOptions(DeployableMamodoInOwnBook(name="ティオ")),
                              HasOptions(AttachablePartnerPagesInOwnBook(name="大海恵"))), effect=Sequence(steps=(
    Choose(
        OrSkip(DeployableMamodoInOwnBook(name="ティオ")), bind="page", prompt="pick_mamodo_in_own_book",
        then=When(
            Bound("page", None),
            otherwise=PlayMamodoFromBook(),
        ),
    ),
    Choose(
        OrSkip(AttachablePartnerPagesInOwnBook(name="大海恵")), bind="partner_page", prompt="pick_partner_in_own_book",
        then=When(
            Bound("partner_page", None),
            otherwise=Choose(
                SlotsForBookPartner(page=Ref("partner_page")), bind="slot", prompt="pick_own_mamodo",
                then=AttachPartnerFromBookPage(page=Ref("partner_page"), slot=Ref("slot")),
            ),
        ),
    ),
)))
reg.event("E-035", when=mp_reduced_by_opponent, effect=TurnPagesForward(leaves=2, target="opponent"))
reg.event("E-036", effect=RemoveRestrictions(categories=("spells", "protect", "mamodo_effects"), whose="both"))
reg.event("E-038", effect=ScheduleEndPhaseMp(amount=4))
reg.event("E-040", when=has_two_or_more_mamodo, effect=HealAllOwnMamodo())

# 「相手は、相手の魔物1体を選ぶ」:由對手選擇保留的魔物;對手沒有魔物時沒有效果
reg.event("E-043", effect=AsOpponent(then=When(
    HasOptions(OwnMamodo()),
    then=Choose(
        OwnMamodo(), bind="slot", prompt="pick_own_mamodo",
        then=RestrictOthersThanChosen(),
    ),
)))
