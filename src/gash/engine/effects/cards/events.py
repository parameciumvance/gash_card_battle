"""事件卡(E-xxx)的效果登記。依卡號排序,排版規則見 `cards/__init__.py`。"""

from ...state import (
    DUR_TURN, DUR_UNTIL_END_NEXT_TURN, NO_MAMODO_EFFECTS, NO_PARTNER_EFFECTS, NO_SPELLS,
)
from .. import registry as reg
from ..tree import (
    AddPower, Always, AttachPartnerFromBookPage, AttachPartnerFromDiscard,
    AttachablePartnerPagesInOwnBook, BoostPartneredMamodo, BorrowPartner, Choose, Coin,
    CoinWithPaidReflip, DeployMamodoFromBook, DeployableMamodoInOwnBook, DiscardChosenMamodo,
    DiscardFromOpponentBookPayCost, DiscardOtherPartners, GainMp, GainMpPerHeads, HasOptions,
    HeadsAtLeast, HeadsCount, HealFirstInjuredMamodo, HealSlot, LockChosenOpponentMamodo,
    NextStartPhase, OpponentBookCards, OpponentMamodo, OpponentPartneredMamodo, OwnHasPartner,
    OwnInjuredMamodo, OwnMamodo, OwnPartneredMamodo, PartnerDiscardedThisTurn,
    PeekOpponentOpenPages, PlayablePartnerInDiscard, ReduceOpponentMpUnlessReducedLastTurn, Ref,
    RestrictBothPlayers, RestrictOpponent, RevealOpponentBook, ScheduleNoProtectBookNextBattle,
    Sequence, SlotsForBookPartner, Standby, TurnPagesBack, TurnPagesForward, When,
    ZeroBothPlayersMp, has_own_injured_mamodo, has_own_mamodo, has_partner_discarded_this_turn,
    has_two_or_more_mamodo, opponent_has_mamodo, opponent_has_partner, opponent_then_self,
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
