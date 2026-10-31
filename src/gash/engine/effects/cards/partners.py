"""搭檔卡(P-xxx)的效果登記。依卡號排序,排版規則見 `cards/__init__.py`。"""

from ...state import (
    DUR_NEXT_TURN, DUR_TURN, NO_ATTACK_SPELL, NO_DEFENSE_SPELL_SLOT, NO_EVENTS, NO_PARTNER_EFFECTS,
    NO_PROTECT_SLOT, PROTECT_ONLY,
)
from .. import registry as reg
from ..tree import (
    AttachablePartnerPagesInOwnBook, AttachPartnerFromBookPage, SlotsForBookPartner,
    AttackByFamilyWithTarget, RestrictOpponentSlotThisBattle, ScheduleBattleLock, ScheduleOnAttack,
    All, AllowAttrSpellsThisTurn, Bound, EffectOptions, ReduceOpponentMp, TotalPowerWhenBattlingWith, AllowProtectWithOpponentMamodo, CanNegateOpponentSpell, Choose,
    DiscardChosenPartner, DiscardTopMamodoCard, DoubleAttackDamage, GainMp,
    GainMpWhenOpponentUsesEvent, GuardOwnMpThisTurn, HasOptions, IncreaseAttackDamage,
    LockChosenOpponentMamodo, MakeNextAttackUndefendable, NegateNextDamageThisBattle,
    NegateOpponentSpell, NoBattleDamageModifierFrom, OpponentMamodo, OpponentMamodoExcept,
    OpponentPartneredMamodo, OwnAttackBy, OwnPageTurnBackEffectAvailable,
    OwnPageTurnEffectAvailable, ProtectorsDiscardedThisTurn, ReduceOpponentMpByStartGain,
    ReduceOpponentMpPerPageTurnedBack, RemoveRestrictions, RestrictOpponent, ScheduleNextSpellBonus,
    ScheduleRedirectDamage, ScheduleSpellFromAnyPage, Sequence, SetPowerZeroThisTurn,
    SpellsCostZeroThisTurn, StealOpponentMp, TurnOpponentPagesPerMamodoCardDiscarded,
    TurnOwnPagesBackOncePerTurn, TurnOwnPagesOncePerTurn, When,
)

# 「このカードを捨て札にする→」為 mode="discard"(引擎把此卡棄掉作為費用;E-010 借用時不棄)。
# 「某魔物の術 / 某魔物による」類效果以「使用戰術的魔物」判定,指令戰術由該魔物使用時也適用。

# 對手回合的「次のバトル」是對手攻擊,一定沒有效果:限自己的回合(P-007 攻防都有作用,不限制)
reg.activated("P-001", mode="discard", timing="nonbattle", own_turn=True,
              effect=MakeNextAttackUndefendable(mamodo="ガッシュ・ベル"))
reg.activated("P-002", mode="discard", timing="nonbattle", effect=StealOpponentMp(amount=3))
# 作用對象(自分の「ブラゴ」/「ゴフレ」による攻撃、重複しない)不是使用條件:不成立時能用但沒有效果
reg.activated("P-003", mode="discard", timing="battle", effect=When(
    All(OwnAttackBy("ブラゴ"), NoBattleDamageModifierFrom("P-003")),
    then=IncreaseAttackDamage(amount=2),
))
reg.activated("P-004", mode="discard", timing="battle", effect=When(
    All(OwnAttackBy("ゴフレ"), NoBattleDamageModifierFrom("P-004")),
    then=DoubleAttackDamage(),
))
reg.activated("P-005", mode="discard", timing="nonbattle", effect=SpellsCostZeroThisTurn(mamodo="スギナ"))

# 沒有 M-010 時能用但沒有效果(NegateNextDamageThisBattle 找不到對象就不排程)
reg.activated("P-006", mode="discard", timing="battle", effect=NegateNextDamageThisBattle(
    number="M-010",
    then=DiscardTopMamodoCard(number="M-010"),
))

reg.activated("P-007", mode="discard", timing="nonbattle",
              effect=ScheduleNextSpellBonus(mamodo="フェイン", power_delta=4000))

reg.activated("P-008", mode="discard", timing="nonbattle",
              condition=HasOptions(OpponentPartneredMamodo(discard=True)), effect=Choose(
    OpponentPartneredMamodo(discard=True), bind="choice", prompt="pick_opponent_partner",
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

# ---------------------------------------------------------------- 第三彈

reg.battle_phase_mp_lock("P-020")
reg.action_discard("P-020", "partner")
reg.activated("P-021", mode="discard", timing="nonbattle", effect=GuardOwnMpThisTurn())
reg.activated("P-022", mode="discard", timing="nonbattle", condition=HasOptions(OpponentMamodo()), effect=Choose(
    OpponentMamodo(), bind="choice", prompt="pick_opponent_mamodo",
    then=ScheduleRedirectDamage(mamodo="フリガロ"),
))

# 「このターン中のバトルで」(沒有「次の」):本回合任一場戰鬥中第一張エシュロス戰術
reg.activated("P-023", mode="discard", timing="nonbattle", effect=Sequence(steps=(
    GainMp(amount=2),
    ScheduleNextSpellBonus(mamodo="エシュロス", power_delta=2000, expires="turn"),
)))

reg.reveal_opponent_pages("P-024")
reg.activated("P-025", mode="discard", timing="nonbattle", effect=ScheduleSpellFromAnyPage(spell="ジオルク"))
reg.activated("P-026", mode="discard", timing="nonbattle", condition=HasOptions(OpponentMamodo()), effect=Choose(
    OpponentMamodo(), bind="choice", prompt="pick_opponent_mamodo",
    then=LockChosenOpponentMamodo(flag=PROTECT_ONLY),
))

reg.activated("P-027", mode="discard", timing="battle",
              condition=HasOptions(OpponentMamodoExcept("ゾボロン")), effect=Choose(
    OpponentMamodoExcept("ゾボロン"), bind="slot", prompt="pick_opponent_mamodo",
    then=AllowProtectWithOpponentMamodo(),
))

reg.activated("P-028", mode="discard", timing="battle", effect=NegateNextDamageThisBattle(number="M-042"))
reg.activated("P-029", mode="discard", timing="nonbattle",
              effect=AllowAttrSpellsThisTurn(mamodo="ザバス", attr="風"))
reg.trigger("P-030", "book_card_used", effect=GainMpWhenOpponentUsesEvent(amount=2))
reg.block_opponent_family("P-031", family="ウマゴン", event_name="ウマゴン")
# 「次のターンのスタートフェイズまでスタンバイし、次のターン中ステイ」:下一回合中生效的限制
reg.activated("P-032", mode="discard", timing="nonbattle",
              effect=RestrictOpponent(flag=NO_PARTNER_EFFECTS, duration=DUR_NEXT_TURN))
reg.activated("P-033", mode="discard", timing="nonbattle", condition=HasOptions(OpponentMamodo()), effect=Choose(
    OpponentMamodo(), bind="choice", prompt="pick_opponent_mamodo",
    then=LockChosenOpponentMamodo(flag=NO_ATTACK_SPELL),
))

reg.activated("P-034", mode="discard", timing="nonbattle", effect=RemoveRestrictions(categories=("spells",)))
reg.activated("P-035", mode="discard", timing="nonbattle", effect=ReduceOpponentMpByStartGain(multiplier=2))

# P-036:使用條件以這張搭檔棄掉後的場面判斷(可再放出另一張「高嶺清麿」)
reg.activated("P-036", mode="discard", timing="nonbattle",
              condition=HasOptions(AttachablePartnerPagesInOwnBook(excluding_self=True)), effect=Choose(
    AttachablePartnerPagesInOwnBook(), bind="page", prompt="pick_partner_in_own_book",
    then=Choose(
        SlotsForBookPartner(), bind="slot", prompt="pick_mamodo_for_partner",
        then=AttachPartnerFromBookPage(),
    ),
))

reg.opponent_event_lock("P-038")
reg.action_discard("P-038", "partner")
reg.activated("P-040", mode="discard", timing="battle", condition=CanNegateOpponentSpell("any"),
              effect=NegateOpponentSpell("any"))

# P-042 / P-043「『ダニー』の術や『魔物の効果』で攻撃」:該家族魔物的戰術或魔物效果攻擊(以攻擊的魔物判斷,同 P-001);
# 對手回合的下一場戰鬥是對手攻擊,限自己的回合
reg.activated("P-042", mode="discard", timing="nonbattle", own_turn=True,
              effect=ScheduleBattleLock(mamodo="ダニー", flags=(NO_PARTNER_EFFECTS, NO_EVENTS)))

# P-043:使用時選對手魔物;攻擊時(防禦宣告前)由使用者選其中一個效果,選定的魔物已離場時不詢問
reg.activated("P-043", mode="declare", timing="nonbattle", own_turn=True, condition=HasOptions(OpponentMamodo()),
              effect=Choose(
    OpponentMamodo(), bind="target", prompt="pick_opponent_mamodo",
    then=ScheduleOnAttack(target="target"),
))
reg.on_attack("P-043", when=AttackByFamilyWithTarget(mamodo="ウォンレイ"), effect=Choose(
    EffectOptions((("no_defense_spell", "opponent_no_defense_spell", None),
                   ("no_protect", "opponent_no_protect", None))),
    bind="mode", prompt="pick_effect",
    then=When(
        Bound("mode", "no_defense_spell"),
        then=RestrictOpponentSlotThisBattle(flag=NO_DEFENSE_SPELL_SLOT),
        otherwise=RestrictOpponentSlotThisBattle(flag=NO_PROTECT_SLOT),
    ),
))

# Ex-007 / 010 / 011 / 012:下一場戰鬥中該家族的戰術 1 張「本来のコスト」為 0(追加費用照付,Ex-011 舊規則 FAQ);
# 攻防都有作用,不限自己的回合(同 P-007)
reg.activated("Ex-007", mode="discard", timing="nonbattle",
              effect=ScheduleNextSpellBonus(mamodo="ガッシュ・ベル", base_zero=True))
reg.activated("Ex-008", mode="discard", timing="nonbattle", effect=GainMp(amount=4))
reg.activated("Ex-009", mode="discard", timing="nonbattle", effect=ReduceOpponentMp(amount=4))
reg.activated("Ex-010", mode="discard", timing="nonbattle",
              effect=ScheduleNextSpellBonus(mamodo="ハイド", base_zero=True))
reg.activated("Ex-011", mode="discard", timing="nonbattle",
              effect=ScheduleNextSpellBonus(mamodo="ティオ", base_zero=True))
reg.activated("Ex-012", mode="discard", timing="nonbattle",
              effect=ScheduleNextSpellBonus(mamodo="フェイン", base_zero=True))

reg.activated("Ex-033", mode="discard", timing="nonbattle", effect=Choose(
    EffectOptions((("gain", "gain_mp_3", None), ("reduce", "reduce_opponent_mp_3", None))),
    bind="mode", prompt="pick_effect",
    then=When(
        Bound("mode", "gain"),
        then=GainMp(amount=3),
        otherwise=ReduceOpponentMp(amount=3),
    ),
))

reg.activated("Ex-035", mode="discard", timing="nonbattle",
              effect=ScheduleNextSpellBonus(mamodo="ブラゴ", base_delta=-5))

reg.static_total_power("Ex-036", value=TotalPowerWhenBattlingWith(name="ウォンレイ", amount=2000))
reg.action_discard("Ex-036", "partner")
