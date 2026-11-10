"""事件卡(E-xxx)的效果登記。依卡號排序,排版規則見 `cards/__init__.py`。"""

from ...cards import EVENT
from ...state import (
    DUR_TURN, DUR_UNTIL_END_NEXT_TURN, DUR_UNTIL_END_OWN_NEXT_TURN, EFFECTS_LOCKED, NO_ATTACK, NO_EFFECTS_AND_SPELLS, NO_MAMODO_EFFECTS, NO_PARTNER_EFFECTS,
    NO_SPELLS,
)
from .. import registry as reg
from ..tree import (
    GainMpPerCount, OpponentMamodoWithDiscardCostEffect, OwnDiscardMamodoCards, ScheduleEndPhaseMpHalfBattleLoss,
    DiscardChosenOpponentMamodo,
    DiscardChosenOpponentFieldCard, OpponentFieldCards,
    DiscardThisEventFromBook, OpponentOpenPagesHaveEvent, OwnPageIsPartner, PlayableOnOwnOpenPages,
    TurnOwnPagesBackOncePerTurn,
    AddPowerToOwnStoneTablets, OpponentMamodoByStone,
    DamageChosenOpponentMamodo, DamageOwnMamodoThen, ForceProtectWith, NegateAttack, NegatedOwnEffects,
    UndoNegatedEffect, ScheduleEndPhaseDiscardSlot, SetBothMp, UseAllInChosenOrder,
    battle_phase_first, opponent_has_two_or_more_mamodo,
    AddPower, AddPowerPerOwnMamodo, All, Always, AnyOf, AsOpponent, AttachablePartnerPagesInOwnBook, AttachPartnerFromBookPage,
    AttachPartnerFromDiscard, AwaitBookReviewEnd, BoostPartneredMamodo, BorrowPartner, Bound,
    Choose, Coin, CoinWithPaidReflip, DeployableMamodoInOwnBook, DeployMamodoFromBook,
    DiscardChosenMamodo, DiscardChosenPartner, DiscardedMamodoToReturn,
    DiscardFromOpponentBook, DiscardFromOpponentBookPayCost, DiscardOtherPartners, EffectOptions, GainMp, GainMpPerHeads,
    GainMpReducedByOpponent, HasOptions, HeadsAtLeast, HeadsCount, HealAllOwnMamodo, HealSlot,
    LockChosenOpponentMamodo, ModifyNamedSpellsThisTurn, NextStartPhase, OpponentBookCards, OpponentBookPagesAround, OpponentMamodo,
    OpponentPartneredMamodo, OrSkip, OwnEmptyBookPages, OwnHasPartner, OwnInjuredMamodo, OwnMamodo,
    OwnMamodoAndPartnerCount, OwnPartneredMamodo, PartnerDiscardedThisTurn, PeekOpponentOpenPages, PlayablePartnerInDiscard,
    PlayMamodoFromBook, ProtectAnyway, RaiseEventLimitThisTurn, ReduceOpponentMp, ReduceOpponentMpUnlessReducedLastTurn,
    ReduceOwnMp, Ref,
    RemovePowerUps, RemoveRestrictions, RestrictBothPlayers, RestrictOpponent, RestrictOthersThanChosen, RestrictSelf,
    ReturnDiscardToBook, RevealOpponentBook, ScheduleEndPhaseDiscardExceptKept, ScheduleEndPhaseMp,
    ScheduleEndPhaseTurnOpponent, ScheduleNoProtectNextBattle, SeparateEffects, Sequence, SwapOpponentBookPages,
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

reg.event("E-013", effect=ScheduleNoProtectNextBattle())

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

# E-044:依一般放出的規則;搭檔有多隻可裝的魔物時由使用者選
reg.event("E-044", when=HasOptions(PlayableOnOwnOpenPages()), effect=Choose(
    PlayableOnOwnOpenPages(), bind="page", prompt="pick_own_open_page",
    then=When(
        OwnPageIsPartner(),
        then=Choose(
            SlotsForBookPartner(), bind="slot", prompt="pick_mamodo_for_partner",
            then=AttachPartnerFromBookPage(),
        ),
        otherwise=DeployMamodoFromBook(),
    ),
))

# E-045:對象是具有限制效果的卡(由實作推導,見 tree.py 的 restriction_kinds);不當使用條件(同 E-016),最後一頁除外
reg.event("E-045", effect=Sequence(steps=(
    RevealOpponentBook(),
    When(
        HasOptions(OpponentBookCards(None, exclude_last=True, restricting=True)),
        then=Choose(
            OpponentBookCards(None, exclude_last=True, restricting=True), bind="page",
            prompt="pick_opponent_book_card", auto_single=False,
            then=DiscardFromOpponentBook(),
        ),
        otherwise=AwaitBookReviewEnd(),
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

# 「相手の魔本を見て…相手の捨て札にあるカードと同じカード名のカード1枚」:( )內不同仍算同名(card_name_key);
# 比照 E-017 由使用者在網格選,沒有可選的卡時看完即結束,不付費
reg.event("E-050", effect=Sequence(steps=(
    RevealOpponentBook(),
    When(
        HasOptions(OpponentBookCards(None, same_name_as_discard=True)),
        then=Choose(
            OpponentBookCards(None, same_name_as_discard=True), bind="page", prompt="pick_opponent_book_card",
            auto_single=False, then=DiscardFromOpponentBook(),
        ),
        otherwise=AwaitBookReviewEnd(),
    ),
)))

# 「パートナーカードを何枚でも選び、場に出す」:比照 P-036 逐張選頁與裝備的魔物,每次都可停止;
# 1 隻魔物 1 張搭檔、場上最多 3 隻,所以最多 3 次。至少有 1 張可放出的才能使用
reg.event("E-051", when=HasOptions(AttachablePartnerPagesInOwnBook()), effect=Choose(
    OrSkip(AttachablePartnerPagesInOwnBook()), bind="partner_page_1", prompt="pick_partner_in_own_book",
    then=When(
        Bound("partner_page_1", None),
        otherwise=Choose(
            SlotsForBookPartner(page=Ref("partner_page_1")), bind="slot_1", prompt="pick_mamodo_for_partner",
            then=Sequence(steps=(
                AttachPartnerFromBookPage(page=Ref("partner_page_1"), slot=Ref("slot_1")),
                Choose(
    OrSkip(AttachablePartnerPagesInOwnBook()), bind="partner_page_2", prompt="pick_partner_in_own_book",
    then=When(
        Bound("partner_page_2", None),
        otherwise=Choose(
            SlotsForBookPartner(page=Ref("partner_page_2")), bind="slot_2", prompt="pick_mamodo_for_partner",
            then=Sequence(steps=(
                AttachPartnerFromBookPage(page=Ref("partner_page_2"), slot=Ref("slot_2")),
                Choose(
    OrSkip(AttachablePartnerPagesInOwnBook()), bind="partner_page_3", prompt="pick_partner_in_own_book",
    then=When(
        Bound("partner_page_3", None),
        otherwise=Choose(
            SlotsForBookPartner(page=Ref("partner_page_3")), bind="slot_3", prompt="pick_mamodo_for_partner",
            then=Sequence(steps=(
                AttachPartnerFromBookPage(page=Ref("partner_page_3"), slot=Ref("slot_3")),
            )),
        ),
    ),
),
            )),
        ),
    ),
),
            )),
        ),
    ),
))

# 「選ぶ」:沒有被無效的效果時不能使用;非戰鬥中(沒有戰鬥圖示)、雙方的回合
reg.event("E-052", when=HasOptions(NegatedOwnEffects()), effect=Choose(
    NegatedOwnEffects(), bind="record", prompt="pick_negated_effect", then=UndoNegatedEffect(target=Ref("record")),
))

# 戰鬥圖示:戰鬥中的「効果の使用」使用(引擎判斷時機)。傷害走一般流程(可保護);
# 「ダメージがあたえられたかどうかにかかわらず」傷害流程結束後無效攻擊
reg.event("E-053", when=has_own_mamodo, effect=Sequence(steps=(
    Choose(OwnMamodo(), bind="slot", prompt="pick_own_mamodo", then=DamageOwnMamodoThen(target=Ref("slot"))),
    NegateAttack(),
)))

# 「このカードを捨て札にする→」効果を持つ魔物(啟動效果、干擾、擲幣改正面);選不到時不能使用
reg.event("E-054", when=HasOptions(OpponentMamodoWithDiscardCostEffect()), effect=Choose(
    OpponentMamodoWithDiscardCostEffect(), bind="choice", prompt="pick_opponent_mamodo",
    then=DiscardChosenOpponentMamodo(),
))

# Ex-021「次の効果の両方を使う」:+5000 與結束階段棄掉同一隻;兩個 ● 各自獨立(Ex-070 只取除 +5000)
# 兩個 ● 各有條件:條件成立且選得到對手對應魔物的才能選;一般保護流程(比照 Ex-024)
reg.event("Ex-000", when=HasOptions(EffectOptions((
    ("stone", "damage_opponent_stone_tablet", OpponentMamodoByStone(stone=True)),
    ("other", "damage_opponent_non_stone_tablet", OpponentMamodoByStone(stone=False)),
))), effect=Choose(
    EffectOptions((
        ("stone", "damage_opponent_stone_tablet", OpponentMamodoByStone(stone=True)),
        ("other", "damage_opponent_non_stone_tablet", OpponentMamodoByStone(stone=False)),
    )), bind="mode", prompt="pick_effect",
    then=When(
        Bound("mode", "stone"),
        then=Choose(OpponentMamodoByStone(stone=True), bind="choice", prompt="pick_opponent_mamodo",
                    then=DamageChosenOpponentMamodo()),
        otherwise=Choose(OpponentMamodoByStone(stone=False), bind="choice", prompt="pick_opponent_mamodo",
                         then=DamageChosenOpponentMamodo()),
    ),
))

reg.event("Ex-021", when=has_own_mamodo, effect=Choose(
    OwnMamodo(), bind="slot", prompt="pick_own_mamodo",
    then=SeparateEffects(steps=(
        AddPower(amount=5000, duration=DUR_TURN, target=Ref("slot")),
        ScheduleEndPhaseDiscardSlot(target=Ref("slot")),
    )),
))

# Ex-022:自己的翻頁算「合計1回」的 1 次(同 E-039);已受限制時只翻對手
reg.event("Ex-022", effect=Sequence(steps=(
    TurnPagesForward(leaves=1, target="opponent"),
    TurnOwnPageLimitedThenGainMp(leaves=1),
)))

reg.event("Ex-023", when=has_own_mamodo, effect=Choose(
    OwnMamodo(), bind="slot", prompt="pick_own_mamodo",
    then=AddPower(amount=3000, duration=DUR_TURN, target=Ref("slot")),
))

# Ex-024:傷害,對手可以保護(atwiki 卡頁 FAQ)
reg.event("Ex-024", when=opponent_has_two_or_more_mamodo, effect=Choose(
    OpponentMamodo(), bind="choice", prompt="pick_opponent_mamodo",
    then=DamageChosenOpponentMamodo(),
))

# Ex-045:已使用、仍在頁上的事件卡也算
reg.event("Ex-045", effect=Sequence(steps=(
    PeekOpponentOpenPages(),
    When(OpponentOpenPagesHaveEvent(), then=TurnPagesForward(leaves=1, target="opponent")),
)))

# Ex-046「2枚出さなければならない」:能放 2 隻時才能使用;依序選,第 2 隻放出後重算;不列疊放的魔物
reg.event("Ex-046", when=HasOptions(DeployableMamodoInOwnBook(no_stack=True, pair=True)), effect=Choose(
    DeployableMamodoInOwnBook(no_stack=True, pair=True), bind="page", prompt="pick_mamodo_in_own_book",
    then=Sequence(steps=(
        PlayMamodoFromBook(),
        Choose(
            DeployableMamodoInOwnBook(no_stack=True), bind="second", prompt="pick_mamodo_in_own_book",
            then=PlayMamodoFromBook(page=Ref("second")),
        ),
    )),
))

# Ex-047:能保護就必須以選定的魔物保護,優先於 P-027;不妨礙防禦(atwiki 卡頁 FAQ)
reg.event("Ex-047", when=opponent_has_mamodo, effect=Choose(
    OpponentMamodo(), bind="choice", prompt="pick_opponent_mamodo",
    then=ForceProtectWith(),
))

# Ex-048:高於 4 的一方算「MPをへらす」、低於 4 的一方算「MPをふやす」
reg.event("Ex-048", effect=SetBothMp(value=4))

# 「自分の石版魔物すべてを選ぶ」:之後放出的也加(比照 E-048,使用者決定);比照 E-048 沒有使用條件
reg.event("Ex-069", effect=AddPowerToOwnStoneTablets(amount=2000, duration=DUR_UNTIL_END_OWN_NEXT_TURN))

# 沒有指定對象:雙方的都取除(atwiki 卡頁);複合效果整個取除,減魔力與「設為某值」不算
reg.event("Ex-070", effect=RemovePowerUps())

# 比照 E-024:「魔物の効果」與這隻魔物身上搭檔的效果(之後才裝上的也算),不封戰術;雙方的回合
reg.event("Ex-071", when=opponent_has_mamodo, effect=Choose(
    OpponentMamodo(), bind="choice", prompt="pick_opponent_mamodo",
    then=LockChosenOpponentMamodo(flag=EFFECTS_LOCKED),
))

# 「2枚までを選び」:兩次都可不選;沒有可選的卡時看完即結束(比照 E-017),不付費
reg.event("Ex-072", effect=Sequence(steps=(
    RevealOpponentBook(),
    When(
        HasOptions(OpponentBookCards(None, names=("プロフェッサー・ダルタニアン",))),
        then=Choose(
            OrSkip(OpponentBookCards(None, names=("プロフェッサー・ダルタニアン",))), bind="page",
            prompt="pick_opponent_book_card", then=When(
                Bound("page", None),
                otherwise=Sequence(steps=(
                    DiscardFromOpponentBook(),
                    Choose(
                        OrSkip(OpponentBookCards(None, names=("プロフェッサー・ダルタニアン",))), bind="page_2",
                        prompt="pick_opponent_book_card", then=When(
                            Bound("page_2", None),
                            otherwise=DiscardFromOpponentBook(page=Ref("page_2")),
                        ),
                    ),
                )),
            ),
        ),
        otherwise=AwaitBookReviewEnd(),
    ),
)))

reg.event("Ex-073", effect=GainMpPerCount(count=OwnDiscardMamodoCards()))

# Ex-074「相手の場のMJ12カード1枚を選び、捨て札にする」:由使用者選
reg.event("Ex-074", when=HasOptions(OpponentFieldCards(card_type="mj12")), effect=Choose(
    OpponentFieldCards(card_type="mj12"), bind="field", prompt="pick_opponent_field_card",
    then=DiscardChosenOpponentFieldCard(),
))

reg.event("Ex-100", effect=Coin(
    count=2, on=HeadsAtLeast(2),
    then=GainMp(amount=5),
))

reg.event("Ex-101", effect=ScheduleEndPhaseMpHalfBattleLoss())

# PR-005「すきな順で」:使用者逐一選下一個效果;沒有負傷魔物時省略回復
reg.event("PR-005", when=battle_phase_first, effect=UseAllInChosenOrder(entries=(
    ("heal", "heal_all_injured", OwnInjuredMamodo(), HealAllOwnMamodo()),
    ("mp", "gain_mp_2", None, GainMp(amount=2)),
    ("restrict", "restrict_both_effects_spells", None,
     RestrictBothPlayers(flag=NO_EFFECTS_AND_SPELLS, duration=DUR_TURN)),
)))

# PR-007:這張事件卡移到棄牌區(該頁變空頁)後回翻;自己的回翻算「合計1回」的 1 次(同 P-018)
reg.event("PR-007", effect=Sequence(steps=(
    DiscardThisEventFromBook(),
    TurnOwnPagesBackOncePerTurn(leaves=2),
)))

reg.event("PR-010", effect=ModifyNamedSpellsThisTurn(mamodo="ガッシュ・ベル", name="ザケル", cost=-1, power=2000))

# 「相手は、自分の魔本を見て、今のページより後ろのイベントカード1枚を選び、捨て札にする。そうしたなら、
# 相手の魔本を見て…」:對手先選(強制);對手沒有可選的卡時看完即結束,之後不換自己
reg.event("PR-013", effect=AsOpponent(then=Sequence(steps=(
    RevealOpponentBook(),
    When(
        HasOptions(OpponentBookCards(EVENT, after_current=True)),
        then=Choose(
            OpponentBookCards(EVENT, after_current=True), bind="page", prompt="pick_opponent_book_card",
            auto_single=False, then=Sequence(steps=(
                DiscardFromOpponentBook(),
                AsOpponent(then=Sequence(steps=(
                    RevealOpponentBook(),
                    When(
                        HasOptions(OpponentBookCards(EVENT, after_current=True)),
                        then=Choose(
                            OpponentBookCards(EVENT, after_current=True), bind="page_2",
                            prompt="pick_opponent_book_card", auto_single=False,
                            then=DiscardFromOpponentBook(page=Ref("page_2")),
                        ),
                        otherwise=AwaitBookReviewEnd(),
                    ),
                ))),
            )),
        ),
        otherwise=AwaitBookReviewEnd(),
    ),
))))
