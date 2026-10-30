"""事件卡(E-xxx)的效果登記。依卡號排序,排版規則見 `cards/__init__.py`。"""

from ...state import (
    DUR_TURN, DUR_UNTIL_END_NEXT_TURN, NO_ATTACK, NO_EFFECTS_AND_SPELLS, NO_MAMODO_EFFECTS, NO_PARTNER_EFFECTS,
    NO_SPELLS,
)
from .. import registry as reg
from ..tree import (
    DamageChosenOpponentMamodo, ForceProtectWith, ScheduleEndPhaseDiscardSlot, SetBothMp, UseAllInChosenOrder,
    battle_phase_first, opponent_has_two_or_more_mamodo,
    AddPower, AddPowerPerOwnMamodo, All, Always, AnyOf, AsOpponent, AttachablePartnerPagesInOwnBook, AttachPartnerFromBookPage,
    AttachPartnerFromDiscard, AwaitBookReviewEnd, BoostPartneredMamodo, BorrowPartner, Bound,
    Choose, Coin, CoinWithPaidReflip, DeployableMamodoInOwnBook, DeployMamodoFromBook,
    DiscardChosenMamodo, DiscardChosenPartner, DiscardedMamodoToReturn,
    DiscardFromOpponentBookPayCost, DiscardOtherPartners, EffectOptions, GainMp, GainMpPerHeads,
    GainMpReducedByOpponent, HasOptions, HeadsAtLeast, HeadsCount, HealAllOwnMamodo, HealSlot,
    LockChosenOpponentMamodo, ModifyNamedSpellsThisTurn, NextStartPhase, OpponentBookCards, OpponentBookPagesAround, OpponentMamodo,
    OpponentPartneredMamodo, OrSkip, OwnEmptyBookPages, OwnHasPartner, OwnInjuredMamodo, OwnMamodo,
    OwnMamodoAndPartnerCount, OwnPartneredMamodo, PartnerDiscardedThisTurn, PeekOpponentOpenPages, PlayablePartnerInDiscard,
    PlayMamodoFromBook, ProtectAnyway, RaiseEventLimitThisTurn, ReduceOpponentMp, ReduceOpponentMpUnlessReducedLastTurn,
    ReduceOwnMp, Ref,
    RemoveRestrictions, RestrictBothPlayers, RestrictOpponent, RestrictOthersThanChosen, RestrictSelf,
    ReturnDiscardToBook, RevealOpponentBook, ScheduleEndPhaseDiscardExceptKept, ScheduleEndPhaseMp,
    ScheduleEndPhaseTurnOpponent, ScheduleNoProtectBookNextBattle, Sequence, SwapOpponentBookPages,
    TurnOwnPageLimitedThenGainMp, SlotsForBookPartner, Standby, TurnPagesBack, TurnPagesForward, When,
    ZeroBothPlayersMp,
    dealt_damage_this_turn, has_own_injured_mamodo, has_own_mamodo, has_partner_discarded_this_turn, has_two_or_more_mamodo,
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
reg.event("E-029", effect=RaiseEventLimitThisTurn(limit=3))

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

# 檢視對手魔書的效果不以對象為使用條件:找不到可互換的一對時只檢視
reg.event("E-037", effect=Sequence(steps=(
    RevealOpponentBook(),
    When(
        All(HasOptions(OpponentBookPagesAround("after")), HasOptions(OpponentBookPagesAround("before"))),
        then=Choose(
            OpponentBookPagesAround("after"), bind="later", prompt="pick_opponent_book_card", auto_single=False,
            then=Choose(
                OpponentBookPagesAround("before"), bind="earlier", prompt="pick_opponent_book_card",
                auto_single=False,
                then=SwapOpponentBookPages(),
            ),
        ),
        otherwise=AwaitBookReviewEnd(),
    ),
)))

reg.event("E-038", effect=ScheduleEndPhaseMp(amount=4))
# 「この効果は取りのぞけない」:no_attack 不屬於可移除的限制分類
reg.event("E-039", effect=Sequence(steps=(
    TurnOwnPageLimitedThenGainMp(leaves=1, amount=3),
    RestrictSelf(flag=NO_ATTACK, duration=DUR_TURN),
)))
reg.event("E-040", when=has_two_or_more_mamodo, effect=HealAllOwnMamodo())
reg.event("E-041", when=dealt_damage_this_turn, effect=ScheduleEndPhaseTurnOpponent(leaves=1))

# 自己先選自己留下的 1 隻,對手再選對手留下的 1 隻(只有 1 隻時自動);使用時選定,結束階段棄掉
reg.event("E-042", effect=Sequence(steps=(
    Choose(OwnMamodo(), bind="keep", prompt="pick_mamodo_to_keep"),
    AsOpponent(then=Choose(OwnMamodo(), bind="keep_opponent", prompt="pick_mamodo_to_keep")),
    ScheduleEndPhaseDiscardExceptKept(),
)))

# 「相手は、相手の魔物1体を選ぶ」:由對手選擇保留的魔物;對手沒有魔物時沒有效果
reg.event("E-043", effect=AsOpponent(then=When(
    HasOptions(OwnMamodo()),
    then=Choose(
        OwnMamodo(), bind="slot", prompt="pick_own_mamodo",
        then=RestrictOthersThanChosen(),
    ),
)))

# E-046:擲幣次數為使用當下自己場上魔物與搭檔的數量;0 時不擲(沒有使用條件)
reg.event("E-046", effect=Coin(
    count=OwnMamodoAndPartnerCount(), on=Always(),
    then=GainMpPerHeads(per_head=1),
))

# E-047:只封鎖選定魔物的戰術(魔物效果不受影響)
reg.event("E-047", when=opponent_has_mamodo, effect=Choose(
    OpponentMamodo(), bind="choice", prompt="pick_opponent_mamodo",
    then=LockChosenOpponentMamodo(flag=NO_SPELLS),
))

# E-048:FAQ「魔力が必要なときに改めて計算しなおします」「新たに場に出した魔物は…ふやせます」→ 玩家層級、隨時重算
reg.event("E-048", effect=AddPowerPerOwnMamodo(amount=1000, duration=DUR_UNTIL_END_NEXT_TURN))

reg.event("E-049", effect=Choose(
    EffectOptions((("plus", "both_mp_plus_2", None), ("minus", "both_mp_minus_2", None))),
    bind="mode", prompt="pick_effect",
    then=When(
        Bound("mode", "plus"),
        then=Sequence(steps=(GainMp(amount=2), GainMp(amount=2, target="opponent"))),
        otherwise=Sequence(steps=(ReduceOwnMp(amount=2), ReduceOpponentMp(amount=2))),
    ),
))

reg.event("Ex-023", when=has_own_mamodo, effect=Choose(
    OwnMamodo(), bind="slot", prompt="pick_own_mamodo",
    then=AddPower(amount=3000, duration=DUR_TURN, target=Ref("slot")),
))

# Ex-021「次の効果の両方を使う」:+5000 與結束階段棄掉同一隻
reg.event("Ex-021", when=has_own_mamodo, effect=Choose(
    OwnMamodo(), bind="slot", prompt="pick_own_mamodo",
    then=Sequence(steps=(
        AddPower(amount=5000, duration=DUR_TURN, target=Ref("slot")),
        ScheduleEndPhaseDiscardSlot(target=Ref("slot")),
    )),
))

# Ex-024:傷害,對手可以保護(atwiki 卡頁 FAQ)
reg.event("Ex-024", when=opponent_has_two_or_more_mamodo, effect=Choose(
    OpponentMamodo(), bind="choice", prompt="pick_opponent_mamodo",
    then=DamageChosenOpponentMamodo(),
))

# Ex-047:能保護就必須以選定的魔物保護,優先於 P-027;不妨礙防禦(atwiki 卡頁 FAQ)
reg.event("Ex-047", when=opponent_has_mamodo, effect=Choose(
    OpponentMamodo(), bind="choice", prompt="pick_opponent_mamodo",
    then=ForceProtectWith(),
))

# Ex-048:高於 4 的一方算「MPをへらす」、低於 4 的一方算「MPをふやす」
reg.event("Ex-048", effect=SetBothMp(value=4))

# PR-005「すきな順で」:使用者逐一選下一個效果;沒有負傷魔物時省略回復
reg.event("PR-005", when=battle_phase_first, effect=UseAllInChosenOrder(entries=(
    ("heal", "heal_all_injured", OwnInjuredMamodo(), HealAllOwnMamodo()),
    ("mp", "gain_mp_2", None, GainMp(amount=2)),
    ("restrict", "restrict_both_effects_spells", None,
     RestrictBothPlayers(flag=NO_EFFECTS_AND_SPELLS, duration=DUR_TURN)),
)))

reg.event("PR-010", effect=ModifyNamedSpellsThisTurn(mamodo="ガッシュ・ベル", name="ザケル", cost=-1, power=2000))
