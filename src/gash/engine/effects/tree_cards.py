"""卡片效果樹註冊檔:依卡號排序,每卡一個 reg.xxx(...),效果邏輯在 tree.py 的節點。

排版規則(讓巢狀層次一眼看得出來):
- 第一行固定是 `reg.xxx("卡號", ...,`,方便依卡號掃描。
- 有子節點的容器節點(Choose / Coin / When / Standby / Sequence)一律換行,子節點縮排一層;
  該容器的收尾括號獨立一行,與開頭對齊。
- 沒有子節點的葉節點、條件、選項規格寫在同一行。
- 整張卡只有一個葉節點(或只有旗標)時,整個註冊寫成一行。

只有旗標、沒有邏輯的術卡(如 counter / damage_cap / injure_instead)也一併列在這裡,讓註冊集中。
"""

from ..state import DUR_TURN, DUR_UNTIL_END_NEXT_TURN, NO_PARTNER_EFFECTS, NO_SPELLS
from . import registry as reg
from .tree import (
    AddAttackBonusPerHeads, AddAttackSelfBonus, AddDefenseSelfBonus, AddPower,
    AddPowerToAllOpponentMamodo, AdjustDefenseDamage, Always, AttachPartnerFromDiscard, Choose,
    Coin, DamageBonusIfAttackTotalAtLeast, DamageOpponentBookAndAllMamodo, DisableBookProtection,
    DiscardChosenPartner, GainMp, GainMpPerDamage, GainMpPerHeads, GrantFullImmune,
    HeadsAtLeast, HeadsCount, HealSlot, MakeAttackUndefendable, MakeNextAttackUndefendable,
    MarkInjuredMamodoDiscarded, NegateAttack, NextStartPhase, OpponentPartneredMamodo, OwnMamodo,
    PartnerDiscardedThisTurn, ReduceOpponentMp, Ref, RestrictOpponent, ScheduleInjureInsteadNextWin,
    Sequence, SideIs, Standby,
    TurnPagesBack, TurnPagesForward, When, has_own_mamodo, has_partner_discarded_this_turn,
)

# ================================================================ 事件卡

reg.event("E-001", when=has_own_mamodo, effect=Choose(
    OwnMamodo(), bind="slot", prompt="e001_pick",
    then=Standby(
        NextStartPhase(), expires="next_start",
        then=AddPower(amount=3000, duration=DUR_TURN, target=Ref("slot")),
    ),
))

reg.event("E-005", effect=Coin(
    count=2, on=HeadsCount(2),
    then=TurnPagesBack(leaves=2),
    otherwise=When(
        HeadsCount(0),
        then=TurnPagesForward(leaves=2),
    ),
))

reg.event("E-006", when=has_own_mamodo, effect=Choose(
    OwnMamodo(), bind="slot", prompt="e006_pick",
    then=Coin(
        count=1, on=HeadsAtLeast(1),
        then=HealSlot(target=Ref("slot")),
        otherwise=AddPower(amount=1000, duration=DUR_TURN, target=Ref("slot")),
    ),
))

reg.event("E-020", effect=Sequence(steps=(
    GainMp(amount=3),
    Coin(
        count=1, flipper="opponent", on=HeadsAtLeast(1),
        then=GainMp(amount=3, target="opponent"),
    ),
)))

reg.event("E-022", when=has_partner_discarded_this_turn, effect=Coin(
    count=1, on=HeadsAtLeast(1),
    then=Choose(
        PartnerDiscardedThisTurn(), bind="choice", prompt="e022_pick",
        then=AttachPartnerFromDiscard(),
    ),
))

reg.event("E-026", effect=Coin(
    count=2, on=Always(),
    then=GainMpPerHeads(per_head=2),
))

# ================================================================ 術卡

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
    OpponentPartneredMamodo(), bind="choice", prompt="s039_pick",
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

reg.spell_rider("S-056", on_defense_damaged=GainMpPerDamage(per_point=2))

reg.spell_nonbattle("S-057", effect=Coin(
    count=1, on=HeadsAtLeast(1),
    then=ScheduleInjureInsteadNextWin(),
))

reg.spell_rider("S-058", injure_instead=True)
