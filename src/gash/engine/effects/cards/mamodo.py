"""魔物卡(M-xxx)的效果登記。依卡號排序,排版規則見 `cards/__init__.py`。"""

from ...state import (
    DUR_BATTLE, DUR_GAME, DUR_TURN, MAMODO_EFFECTS_LOCKED, NO_MAMODO_EFFECTS, NO_PARTNER_EFFECTS, NO_PROTECT_SLOT,
    NO_SPELLS, NO_STONE_TABLET_EFFECTS,
)
from .. import registry as reg
from ..tree import (
    DeployableAfterDiscard, DeployableMamodoInOwnBook, DiscardChosenMamodo, OpponentBookAtLastPage,
    OwnMamodoToDiscardKeepingField, PlayMamodoFromBook, can_discard_or_deploy,
    AdjustDefenseDamage, AttackWithOwnBookDamageSpell, EffectOptions, HealSlot, InjureChosenOpponentMamodo,
    MakeNextAttackUndefendable, OpponentHealthyMamodo, OpponentIsAttacking, OrSkip, OwnInjuredMamodo,
    RedirectAttackTo, ScheduleEndPhaseDiscardAllPartners, ScheduleOnAttack,
    AddOwnDamageBonus, AddPower, Coin, HeadsAtLeast, NamedMamodoPowerBonus, NamedSpellPowerBonus,
    NextStartPhase, Standby, StealOpponentMp, AddSelfPowerWhenAttacking, All, AlwaysImmune,
    OpponentMamodo, OpponentOpenPageCards, ScheduleDetachSelf, ScheduleUndefendableAtTotal,
    SetSelfPowerToChosenThisTurn,
    CanUseSpellCardNamed, CanUseSpellsOfMamodo, RestrictOpponent,
    AttachablePartnerPagesInOwnBook, LockChosenOpponentMamodo, SelfHasPartnerNamed, SlotsForBookPartner,
    LockOpponentFieldThisBattlePhase, ScheduleBattleLock,
    AttachOpponentPartnerToSelf, OpponentDiscardedPartner,
    AttachPartnerFromBookPage, AwaitBookReviewEnd, Bound, CanUseSpellNamed, CanUseSpellsWithAttr,
    Choose, DetachedFromSelf, DiscardChosenOpponentMamodo, DiscardChosenPartner,
    DiscardedCardsToReturn, DiscardFromOpponentBook, GainMp, HasOptions, ImmuneToAttackDamage,
    ImmuneToSpellDamageAtMost, IncreaseSelfDamage, NegateAttack, OpponentAttackDamageIs,
    OpponentBookCards, OpponentInjuredMamodo, OpponentMpAtLeast, OpponentOpenPagesLackDefenseSpell,
    OpponentPartneredMamodo, OwnBookAtLastPage, OwnBookPartnerNamed, OwnEarlierPages,
    OwnEmptyBookPages, OwnMamodo, OwnMamodoAtLeast, OwnMamodoPowerBonus, OwnMpAtMost, OwnOpenPages,
    OpponentJustGainedMp, GainMpAsOpponentJustGained, OwnOtherMamodo, OwnSideInBattle, PeekOpponentOpenPages, PreventDamageToSelf, ProtectAnyway,
    ReduceOpponentMp, Ref, RestrictOpponent, ScheduleFreeSpell, ReturnDiscardToBook, RevealOpponentBook, ScheduleNextSpellBonus,
    ScheduleSkipEndFlip, ScheduleSpellFromNextSpreads, SelfHasNoPartner, SelfHasPartner,
    SelfInjured, SelfPowerBonus, Sequence, SpellUsesPerTurnWhileCopies,
    SwapBookPages, TurnPagesForward, When,
)

# activated 的 mode / mp_cost / timing / own_turn / per_game / condition 由引擎檢查,effect 只描述效果本身。

reg.activated("M-001", mode="mp", mp_cost=1, timing="battle", condition=OwnSideInBattle("attack"),
              effect=AddPower(amount=1000, duration=DUR_BATTLE, target=Ref("self_slot")))

reg.start_phase("M-002", effect=When(
    OwnMpAtMost(2),
    then=GainMp(amount=1),
))

reg.static_power("M-003", value=SelfPowerBonus(amount=1000, when=SelfInjured()))
reg.static_power("M-004", value=SelfPowerBonus(amount=1000, when=SelfHasPartner()))

reg.activated("M-005", mode="mp", mp_cost=2, timing="battle",
              effect=IncreaseSelfDamage(amount=1, duration=DUR_BATTLE))

reg.on_play("M-006", effect=RestrictOpponent(flag=NO_SPELLS, duration=DUR_TURN))
reg.on_play("M-007", effect=TurnPagesForward(leaves=1, target="opponent"))
reg.stack_on("M-007", base=("M-006",))

reg.activated("M-008", mode="declare", timing="nonbattle",
              effect=ScheduleNextSpellBonus(mamodo="スギナ", power_delta=-1000, cost_delta=-1, optional=True))

reg.on_discard("M-009", effect=GainMp(amount=4))

reg.stack_on("M-010", base=("M-009",))
reg.activated("M-010", mode="mp", mp_cost=1, timing="battle", condition=OwnSideInBattle("defense"),
              effect=AddPower(amount=1000, duration=DUR_BATTLE, target=Ref("self_slot")))

# 對手魔書有沒有魔物是檢視後才知道的資訊,不當使用條件;沒有時檢視後不棄
reg.activated("M-011", mode="declare", timing="nonbattle", per_game=True, effect=Sequence(steps=(
    RevealOpponentBook(),
    When(
        HasOptions(OpponentBookCards("mamodo")),
        then=Choose(
            OpponentBookCards("mamodo"), bind="page", prompt="pick_opponent_book_card", auto_single=False,
            then=DiscardFromOpponentBook(),
        ),
        otherwise=AwaitBookReviewEnd(),
    ),
)))

# M-012 的「重擲自己擲的硬幣」在擲硬幣子階段中詢問,不由玩家主動宣告
reg.coin_reflip("M-012", coins="self")

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

reg.activated("M-017", mode="mp", mp_cost=2, timing="battle", condition=OwnSideInBattle("attack"),
              effect=AddPower(amount=2000, duration=DUR_BATTLE, target=Ref("self_slot")))

reg.activated("M-018", mode="mp", mp_cost=1, timing="nonbattle", own_turn=True, effect=Sequence(steps=(
    PeekOpponentOpenPages(),
    When(OpponentOpenPagesLackDefenseSpell(), then=GainMp(amount=2)),
)))

# M-019 的「令對手重擲」在擲硬幣子階段中詢問,不由玩家主動宣告
reg.coin_reflip("M-019", coins="opponent")

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
              condition=HasOptions(OpponentPartneredMamodo(discard=True)), effect=Choose(
    OpponentPartneredMamodo(discard=True), bind="choice", prompt="pick_opponent_partner",
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

reg.rule_spell_compat("M-029", check=CanUseSpellNamed(mamodo="ガッシュ・ベル", name="ザケル"))
reg.activated("M-029", mode="mp", mp_cost=7, timing="nonbattle",
              condition=HasOptions(OpponentInjuredMamodo()), effect=Choose(
    OpponentInjuredMamodo(), bind="choice", prompt="pick_opponent_injured_mamodo",
    then=DiscardChosenOpponentMamodo(),
))

reg.activated("M-030", mode="declare", timing="nonbattle", per_game=True, condition=OwnBookAtLastPage(),
              effect=ScheduleSkipEndFlip())

reg.damage_immunity("M-031", check=ImmuneToSpellDamageAtMost(total=6000))

# ---------------------------------------------------------------- 第三彈

# M-032 為ジャマー:對手用完事件卡後由引擎詢問是否棄掉自己使其無效
reg.jammer("M-032", discard_self=True, on="event")
reg.activated("M-033", mode="discard", timing="nonbattle", effect=AddOwnDamageBonus(amount=1))
# M-034 的「改成正面」在擲硬幣子階段中詢問,不由玩家主動宣告
reg.coin_set_heads("M-034")
reg.activated("M-035", mode="mp", mp_cost=1, timing="nonbattle", condition=HasOptions(OpponentMamodo()),
              effect=Choose(
    OpponentMamodo(), bind="choice", prompt="pick_opponent_mamodo",
    then=SetSelfPowerToChosenThisTurn(),
))

reg.spell_compat("M-036", check=CanUseSpellsWithAttr("氷"))
reg.activated("M-037", mode="mp", mp_cost=2, timing="nonbattle",
              effect=ScheduleSpellFromNextSpreads(mamodo="エシュロス", spreads=2))
reg.ignore_spell_block("M-038")
reg.mamodo_attack("M-039", mp_cost=1, power=6500, damage=1)
reg.mamodo_defense("M-039", mp_cost=1, power=6500)
reg.opponent_event_cost("M-040", 1)
reg.activated("M-041", mode="mp", mp_cost=2, timing="nonbattle",
              condition=All(SelfHasNoPartner(), HasOptions(OwnBookPartnerNamed("ヒゲ"))), effect=Choose(
    OwnBookPartnerNamed("ヒゲ"), bind="page", prompt="pick_partner_in_own_book",
    then=AttachPartnerFromBookPage(slot=Ref("self_slot")),
))

reg.activated("M-042", mode="mp", mp_cost=1, timing="nonbattle", effect=ProtectAnyway(target=Ref("self_slot")))
reg.activated("M-043", mode="mp", mp_cost=1, timing="battle", condition=OpponentAttackDamageIs(1),
              effect=NegateAttack())
reg.activated("M-044", mode="declare", timing="nonbattle", condition=OpponentMpAtLeast(8),
              effect=Sequence(steps=(ReduceOpponentMp(amount=3), GainMp(amount=3))))
# 對手翻開頁沒有搭檔卡時只檢視
reg.activated("M-045", mode="mp", mp_cost=1, timing="nonbattle", own_turn=True, effect=Sequence(steps=(
    PeekOpponentOpenPages(),
    Choose(
        OpponentOpenPageCards(card_type="partner"), bind="page", prompt="pick_opponent_book_card",
        then=DiscardFromOpponentBook(),
    ),
)))

reg.stack_on("M-046", family="ウマゴン", spell_only=True)
reg.action_discard("M-046", "top")
reg.mamodo_attack("M-046", mp_cost=1, power=7000, damage=2)
reg.stack_on("M-047", family="ガッシュ・ベル")
reg.treated_as("M-047", "ガッシュ・ベル")
reg.rule_on_play("M-047", effect=ScheduleDetachSelf())
reg.damage_immunity("M-047", check=AlwaysImmune())
reg.activated("M-048", mode="declare", timing="nonbattle", effect=ScheduleUndefendableAtTotal(min_total=10000))
reg.partner_discard_guard("M-049")
reg.activated("M-050", mode="declare", timing="nonbattle", condition=HasOptions(OwnOtherMamodo()), effect=Choose(
    OwnOtherMamodo(), bind="slot", prompt="pick_own_mamodo",
    then=AddPower(amount=2000, duration=DUR_TURN),
))

reg.damage_immunity("M-051", check=AlwaysImmune())
reg.cannot_protect("M-051")
reg.activated("M-052", mode="mp", mp_cost=1, timing="nonbattle", effect=Sequence(steps=(
    AddSelfPowerWhenAttacking(amount=1000, duration=DUR_TURN),
    IncreaseSelfDamage(amount=1, duration=DUR_TURN),
)))
reg.damage_immunity("M-053", check=ImmuneToAttackDamage(1))

# 「このターン中の次のバトルで、自分がこの魔物の術で攻撃」:對手回合的下一場戰鬥是對手攻擊,限自己的回合(同 P-001)
reg.activated("M-054", mode="mp", mp_cost=1, timing="nonbattle", own_turn=True, effect=Coin(
    count=1, on=HeadsAtLeast(1),
    then=MakeNextAttackUndefendable(own_slot=True),
))

# M-055:攻擊時(防禦宣告前)詢問是否使用;對手沒有魔物時不詢問。正面改傷害攻擊方選的魔物,反面戰術無效
reg.activated("M-055", mode="mp", mp_cost=1, timing="nonbattle", own_turn=True, effect=ScheduleOnAttack())
reg.on_attack("M-055", when=AttackWithOwnBookDamageSpell(), effect=Choose(
    OrSkip(EffectOptions((("use", "coin_redirect_damage", None),))), bind="use", prompt="pick_effect",
    then=When(
        Bound("use", "use"),
        then=Coin(
            count=1, on=HeadsAtLeast(1),
            then=Choose(OpponentMamodo(), bind="choice", prompt="pick_opponent_mamodo", then=RedirectAttackTo()),
            otherwise=NegateAttack(),
        ),
    ),
))

reg.activated("M-056", mode="mp", mp_cost=1, timing="nonbattle", own_turn=True, effect=Coin(
    count=1, on=HeadsAtLeast(1),
    then=GainMp(amount=3),
))

# M-057:在對手攻擊的戰鬥中使用,不要求這隻魔物在戰鬥中(同 M-043)
reg.activated("M-057", mode="mp", mp_cost=2, timing="battle", condition=OpponentIsAttacking(), effect=Coin(
    count=1, on=HeadsAtLeast(1),
    then=NegateAttack(),
))

# M-058:「自分は、この魔物の術を使えない」是卡片規則;借來的搭檔離場時回到對手的捨て札(engine.discard_attached_partner)
reg.no_own_spells("M-058")
reg.activated("M-058", mode="mp", mp_cost=3, timing="nonbattle",
              condition=All(SelfHasNoPartner(), HasOptions(OpponentDiscardedPartner())), effect=Choose(
    OpponentDiscardedPartner(), bind="choice", prompt="pick_partner_in_discard",
    then=AttachOpponentPartnerToSelf(),
))

# M-059:負傷不是傷害(不能保護、不看不受傷害)
reg.activated("M-059", mode="discard", timing="nonbattle", condition=HasOptions(OpponentHealthyMamodo()),
              effect=Choose(
    OpponentHealthyMamodo(), bind="choice", prompt="pick_opponent_mamodo",
    then=InjureChosenOpponentMamodo(),
))

reg.activated("M-060", mode="discard", timing="nonbattle", own_turn=True,
              effect=TurnPagesForward(leaves=1, target="opponent"))

# M-061:「このターンのエンドフェイズに」;對手受 M-049 / M-066 保護的搭檔不棄(自己的照棄)
reg.activated("M-061", mode="discard", timing="nonbattle", effect=ScheduleEndPhaseDiscardAllPartners())

# M-062「片方または両方を、この順で」:先選是否棄掉、再選是否放出,至少用一個;
# atwiki 卡頁 FAQ:棄掉後場上滿 3 隻不能放出,解決後場上必須有魔物(棄掉唯一的魔物後必須放出)
reg.activated("M-062", mode="mp", mp_cost=2, timing="nonbattle", own_turn=True, condition=can_discard_or_deploy,
              effect=Sequence(steps=(
    Choose(
        OwnMamodoToDiscardKeepingField(), bind="discard", prompt="pick_own_mamodo",
        then=When(
            Bound("discard", None),
            otherwise=DiscardChosenMamodo(target=Ref("discard")),
        ),
    ),
    Choose(
        DeployableAfterDiscard(), bind="page", prompt="pick_mamodo_in_own_book",
        then=When(
            Bound("page", None),
            otherwise=PlayMamodoFromBook(),
        ),
    ),
)))

# M-063:沒有寫「自分のターン」,不限回合
reg.activated("M-063", mode="declare", timing="nonbattle", condition=OpponentBookAtLastPage(),
              effect=TurnPagesForward(leaves=1, target="opponent"))

# M-064:棄掉自己為費用後選自己的魔物;「このゲーム中」= 該魔物離場前一直有效
reg.activated("M-064", mode="discard", timing="nonbattle", per_game=True, condition=HasOptions(OwnOtherMamodo()),
              effect=Choose(
    OwnMamodo(), bind="slot", prompt="pick_own_mamodo",
    then=AddPower(amount=2000, duration=DUR_GAME, target=Ref("slot")),
))

# M-065:ジャマー;對手的行動使自己的 MP 實際減少時詢問,擲硬幣正面才無效;每個這樣的行動 1 次,每回合不限次數
reg.jammer("M-065", on="mp_reduced", per_turn=None, coin=True)
reg.partner_discard_guard("M-066")

reg.activated("M-067", mode="discard", timing="nonbattle", effect=Standby(
    NextStartPhase(own=True), expires="own_start",
    then=GainMp(amount=4),
))

reg.mamodo_attack("M-068", mp_cost=1, power=6000, damage=1, per_turn=2)
reg.mamodo_attack("M-069", mp_cost=2, power=6000, damage=2)

# 比照 P-042:下一場以ガッシュ・ベル的戰術或魔物效果攻擊的戰鬥中,對手不能用魔物效果與搭檔效果
reg.activated("M-070", mode="declare", timing="nonbattle", own_turn=True,
              effect=ScheduleBattleLock(mamodo="ガッシュ・ベル", flags=(NO_MAMODO_EFFECTS, NO_PARTNER_EFFECTS)))
# 「自分がこの魔物で攻撃したバトルの魔力勝負で負けたとき」:防禦方較大或相同、攻擊被無效(規則頁「魔力勝負」)
reg.attack_lost_mp("M-071", 3)
# 「自分がコイン1個を投げるごとに」:重擲也算,改成正面不算;對手替我擲的不算
reg.coin_thrown_mp("M-072", 1)
# 「自分も相手は…その魔物を選ぶことができない」(卡頁解說:誤植,讀作「自分も相手も…この魔物を」);
# 自己用它的戰術後,下一回合它的魔物效果(含不能被選)不作用
reg.unselectable("M-075")
reg.lock_after_own_spell("M-075")
# 「相手が、相手のスタートフェイズに『ふやせるMPの数』は2まで」:翻頁與開始階段的效果合計
reg.start_phase_mp_cap("M-076", 2)
reg.partner_discard_guard("M-078")
# 「相手は、自分の魔本を見なければ使えない效果を使えない」:效果文含「相手の魔本(の今のページ)を見」的整張卡(使用者決定)
reg.book_hidden("M-079")
# 《乱入》:ジャマー,只在對手的戰鬥階段(干擾戰鬥中不能用);《バトル乱入》:戰鬥圖示,兩個效果分開計次
reg.jammer("M-080", discard_self=True, on="event", opponent_turn=True)
reg.activated("M-080", mode="discard", timing="battle", condition=OpponentIsAttacking(), effect=NegateAttack())
# 「ゾフィス」としてあつかう;《悪しき力》綁在選定的魔物(FAQ A1:同卡號的新魔物不受影響),只封「魔物の効果」
reg.treated_as("M-081", "ゾフィス")
reg.activated("M-081", mode="declare", timing="nonbattle", per_game=True, condition=HasOptions(OpponentMamodo()),
              effect=Choose(
    OpponentMamodo(), bind="choice", prompt="pick_opponent_mamodo",
    then=LockChosenOpponentMamodo(flag=MAMODO_EFFECTS_LOCKED, duration=DUR_GAME),
))
reg.activated("M-082", mode="mp", mp_cost=2, timing="nonbattle", condition=HasOptions(OpponentMamodo()), effect=Choose(
    OpponentMamodo(), bind="choice", prompt="pick_opponent_mamodo",
    then=LockChosenOpponentMamodo(flag=NO_PROTECT_SLOT),
))
# 「自分の魔本の好きなページから」:含未翻開的頁(比照 E-051 選頁、選裝備的魔物)
reg.stack_on("M-083", family="ニャルラト")
reg.activated("M-083", mode="mp", mp_cost=1, timing="nonbattle",
              condition=HasOptions(AttachablePartnerPagesInOwnBook(name="詞音")), effect=Choose(
    AttachablePartnerPagesInOwnBook(name="詞音"), bind="page", prompt="pick_partner_in_own_book",
    then=Choose(
        SlotsForBookPartner(page=Ref("page")), bind="slot", prompt="pick_mamodo_for_partner",
        then=AttachPartnerFromBookPage(page=Ref("page"), slot=Ref("slot")),
    ),
))

# 「相手は、捨て札のカードを、場や魔本にもどすことができない」:不論是誰的棄牌區(game-engine「不能放回棄牌區的卡」)
reg.block_discard_return("M-085")

reg.activated("Ex-002", mode="mp", mp_cost=2, timing="nonbattle", condition=HasOptions(OpponentMamodo()),
              effect=Choose(
    OpponentMamodo(), bind="slot", prompt="pick_opponent_mamodo",
    then=AddPower(amount=-2000, duration=DUR_TURN, target=Ref("slot"), side="opponent"),
))

# Ex-003:沒有寫「自分のターン」,不限回合;最後一頁除外,沒有可棄的卡時只檢視
reg.activated("Ex-003", mode="declare", timing="nonbattle", per_game=True, effect=Sequence(steps=(
    PeekOpponentOpenPages(),
    Choose(
        OpponentOpenPageCards(), bind="page", prompt="pick_opponent_book_card",
        then=DiscardFromOpponentBook(),
    ),
)))

# Ex-025「直後に使う」:對手的上一個行動以效果增加了 MP,且之後沒有其他行動
reg.activated("Ex-025", mode="declare", timing="any", condition=OpponentJustGainedMp(),
              effect=GainMpAsOpponentJustGained())

# Ex-026 的重擲在擲硬幣子階段中詢問,每次付 MP 1、每回合 2 次
reg.coin_reflip("Ex-026", coins="self", mp_cost=1, per_turn=2)

# Ex-027「そうしたなら」:實際減少的量才增加(對手 MP 0 或被 P-021 擋下時不增加)
reg.activated("Ex-027", mode="declare", timing="nonbattle", own_turn=True, effect=StealOpponentMp(amount=1))

# Ex-031:在對手以戰術攻擊的戰鬥中使用;魔物效果攻擊不適用
reg.activated("Ex-031", mode="mp", mp_cost=1, timing="battle", condition=OpponentIsAttacking(spell_only=True),
              effect=AdjustDefenseDamage(amount=-1))

# Ex-032:裝在這隻キッド(同 M-020 / M-021 / M-041)
reg.activated("Ex-032", mode="mp", mp_cost=2, timing="nonbattle",
              condition=All(SelfHasNoPartner(), HasOptions(OwnBookPartnerNamed("ナゾナゾ博士"))), effect=Choose(
    OwnBookPartnerNamed("ナゾナゾ博士"), bind="page", prompt="pick_partner_in_own_book",
    then=AttachPartnerFromBookPage(slot=Ref("self_slot")),
))

# 石版魔物の「魔物の効果」:依當下的最上層判斷,之後放出的也算;「このカードが場にある→」也擋
reg.activated("Ex-049", mode="mp", mp_cost=1, timing="nonbattle",
              effect=RestrictOpponent(flag=NO_STONE_TABLET_EFFECTS, duration=DUR_TURN))
# 「自分の魔本が最後のページのとき」:事件卡與搭檔效果(含「このカードが場にある→」),雙方的回合
reg.last_page_lock("Ex-051")
# 「この魔物に『リィエン』/『ゴルドー』がついていれば使える」
reg.mamodo_attack("Ex-052", mp_cost=1, power=7000, damage=1, condition=SelfHasPartnerNamed("リィエン"))
# 「このターン中に捨て札にしたカード」:對手本回合進棄牌區的卡,不分原因(使用者決定)
reg.block_discarded_names("Ex-053")
# 放出時選對手場上可被選擇的卡;只鎖當時的那些卡,只在這回合的戰鬥階段
reg.on_play("Ex-054", effect=LockOpponentFieldThisBattlePhase())
reg.mamodo_attack("Ex-055", mp_cost=1, power=6500, damage=2, condition=SelfHasPartnerNamed("ゴルドー"))

# 石版魔物:「このカードが場にある→」戰術相容(被「魔物の効果を使えない」擋下時不能使用)
reg.spell_compat("Ex-056", check=CanUseSpellsOfMamodo("マルス"))
reg.spell_compat("Ex-057", check=CanUseSpellsOfMamodo("エシュロス"))
reg.spell_compat("Ex-058", check=CanUseSpellCardNamed("ビライツ"))

# 「この効果は、自分の場にこの魔物以外の魔物がいないとき使える」:雙方都不能選(含「すべてを選ぶ」,FAQ A1 / A2)
reg.unselectable("Ex-099", alone=True)

# PR-001「この魔物の術」依名稱(離場後換另一隻ガッシュ・ベル也適用);「コスト3まで」為實際費用,追加費用照付
reg.activated("PR-001", mode="declare", timing="nonbattle", per_game=True, effect=ScheduleFreeSpell(max_cost=3))
reg.activated("PR-002", mode="mp", mp_cost=3, timing="nonbattle",
              effect=AddPower(amount=2000, duration=DUR_TURN, target=Ref("self_slot")))

reg.static_power("PR-003", value=NamedMamodoPowerBonus(name="ガッシュ・ベル", amount=2000))

reg.static_spell_power("PR-004", value=NamedSpellPowerBonus(mamodo="ガッシュ・ベル", name="ザケル", amount=1000))

# PR-008:沒有負傷魔物時不能使用;正面時選 1 隻回復
reg.activated("PR-008", mode="mp", mp_cost=1, timing="nonbattle", condition=HasOptions(OwnInjuredMamodo()),
              effect=Coin(
    count=1, on=HeadsAtLeast(1),
    then=Choose(OwnInjuredMamodo(), bind="slot", prompt="pick_own_injured_mamodo", then=HealSlot(target=Ref("slot"))),
))

reg.end_phase("PR-011", when=OwnMpAtMost(1), effect=GainMp(amount=2))
# 「バトルフェイズに、ダメージ以外の効果で、魔本をめくることはできない」(FAQ:舊「メインフェイズ」讀作バトルフェイズ)
reg.block_effect_page_turn("PR-012")
