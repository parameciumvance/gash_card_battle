"""夥伴卡(P-xxx)的效果登記。依卡號排序,排版規則見 `cards/__init__.py`。"""

from ...state import DUR_TURN, NO_ATTACK_SPELL
from .. import registry as reg
from ..tree import (
    All, CanNegateOpponentSpell, Choose, DiscardChosenPartner, DiscardTopMamodoCard,
    DoubleAttackDamage, HasOptions, IncreaseAttackDamage, MakeNextAttackUndefendable,
    NegateNextDamageThisBattle, NegateOpponentSpell, NoBattleDamageModifierFrom, OpponentMamodo,
    OpponentPartneredMamodo, OwnAttackBy, OwnFieldHas, OwnPageTurnBackEffectAvailable,
    OwnPageTurnEffectAvailable, ProtectorsDiscardedThisTurn, ReduceOpponentMpPerPageTurnedBack,
    RestrictOpponent, ScheduleNextSpellBonus, ScheduleSpellFromAnyPage, SetPowerZeroThisTurn,
    SpellsCostZeroThisTurn, StealOpponentMp, TurnOpponentPagesPerMamodoCardDiscarded,
    TurnOwnPagesBackOncePerTurn, TurnOwnPagesOncePerTurn,
)

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
