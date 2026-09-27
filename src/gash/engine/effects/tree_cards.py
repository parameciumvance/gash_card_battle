"""卡片效果樹註冊檔:依卡號排序,每卡一行 reg.xxx(...),效果邏輯在 tree.py 的節點。"""

from ..state import DUR_TURN, DUR_UNTIL_END_NEXT_TURN, NO_SPELLS
from . import registry as reg
from .tree import (
    AddAttackBonusPerHeads, AddPower, AdjustDefenseDamage, Always, Choose, Coin,
    DisableBookProtection, GrantFullImmune, HeadsAtLeast, MakeAttackUndefendable,
    MakeNextAttackUndefendable, NegateAttack, NextStartPhase, OwnMamodo, Ref,
    RestrictOpponent, ScheduleInjureInsteadNextWin, SideIs, Standby, When,
)

reg.event("E-001", when=lambda g, p: bool(g.state.players[p].slots), effect=Choose(OwnMamodo(), bind="slot", prompt="e001_pick", then=Standby(NextStartPhase(), expires="next_start", then=AddPower(amount=3000, duration=DUR_TURN, target=Ref("slot")))))
reg.spell_rider("S-004", on_damage=Coin(count=1, on=HeadsAtLeast(1), then=RestrictOpponent(flag=NO_SPELLS, duration=DUR_UNTIL_END_NEXT_TURN)))
reg.spell_rider("S-014", on_damage=Coin(count=1, on=HeadsAtLeast(1), then=RestrictOpponent(flag=NO_SPELLS, duration=DUR_UNTIL_END_NEXT_TURN)))
reg.spell_rider("S-021", on_declare=When(SideIs("defense"), then=Coin(count=2, on=HeadsAtLeast(1), then=NegateAttack())))
reg.spell_rider("S-025", on_declare=When(SideIs("defense"), then=Coin(count=1, on=HeadsAtLeast(1), then=NegateAttack())))
reg.spell_nonbattle("S-026", effect=Coin(count=1, on=HeadsAtLeast(1), then=MakeNextAttackUndefendable()))
reg.spell_rider("S-027", on_declare=When(SideIs("defense"), then=Coin(count=2, on=HeadsAtLeast(1), then=AdjustDefenseDamage(amount=-1))))
reg.spell_rider("S-035", on_declare=When(SideIs("attack"), then=Coin(count=2, on=HeadsAtLeast(2), then=DisableBookProtection())))
reg.spell_rider("S-037", on_damage=Coin(count=1, on=HeadsAtLeast(1), then=GrantFullImmune()))
reg.spell_rider("S-040", on_declare=When(SideIs("attack"), then=Coin(count=3, on=Always(), then=AddAttackBonusPerHeads(per_head=2000))))
reg.spell_nonbattle("S-041", effect=Coin(count=1, on=HeadsAtLeast(1), then=GrantFullImmune()))
reg.spell_rider("S-045", on_declare=When(SideIs("attack"), then=Coin(count=2, on=HeadsAtLeast(2), then=MakeAttackUndefendable())))
reg.spell_rider("S-046", on_declare=When(SideIs("attack"), then=Coin(count=1, on=HeadsAtLeast(1), then=MakeAttackUndefendable())))
reg.spell_nonbattle("S-057", effect=Coin(count=1, on=HeadsAtLeast(1), then=ScheduleInjureInsteadNextWin()))
