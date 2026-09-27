"""卡片效果樹註冊檔:依卡號排序,每卡一行 reg.xxx(...),效果邏輯在 tree.py 的節點。

只有旗標、沒有邏輯的術卡(如 counter / injure_instead)也一併列在這裡,讓註冊集中在單一檔案。
"""

from ..cards import PARTNER
from ..state import DUR_TURN, DUR_UNTIL_END_NEXT_TURN, NO_PARTNER_EFFECTS, NO_SPELLS
from . import registry as reg
from .tree import (
    AddAttackBonusPerHeads, AddAttackSelfBonus, AddDefenseSelfBonus, AddPower,
    AddPowerToAllOpponentMamodo, AdjustDefenseDamage, Always, AttachPartnerFromDiscard, Choose,
    Coin, DisableBookProtection, DiscardChosenPartner, GainMpPerHeads, GrantFullImmune,
    HeadsAtLeast, HeadsCount, HealSlot, MakeAttackUndefendable, MakeNextAttackUndefendable,
    MarkInjuredMamodoDiscarded, NegateAttack, NextStartPhase, OpponentPartneredMamodo, OwnMamodo,
    PartnerDiscardedThisTurn, Ref, RestrictOpponent, ScheduleInjureInsteadNextWin, SideIs, Standby,
    TurnPagesBack, TurnPagesForward, When,
)

reg.event("E-001", when=lambda g, p: bool(g.state.players[p].slots), effect=Choose(OwnMamodo(), bind="slot", prompt="e001_pick", then=Standby(NextStartPhase(), expires="next_start", then=AddPower(amount=3000, duration=DUR_TURN, target=Ref("slot")))))
reg.event("E-005", effect=Coin(count=2, on=HeadsCount(2), then=TurnPagesBack(leaves=2), otherwise=When(HeadsCount(0), then=TurnPagesForward(leaves=2))))
reg.event("E-006", when=lambda g, p: bool(g.state.players[p].slots), effect=Choose(OwnMamodo(), bind="slot", prompt="e006_pick", then=Coin(count=1, on=HeadsAtLeast(1), then=HealSlot(target=Ref("slot")), otherwise=AddPower(amount=1000, duration=DUR_TURN, target=Ref("slot")))))
# E-020 恵のコンサート(對手擲幣正→對手 MP+3)暫不遷移:現行 flip_coins 的 callback data 會把
# 呼叫端塞入的 {"player": ...} 覆寫成擲幣者本人(此卡擲幣者剛好是對手),導致 e020_resolve 的
# `1 - data["player"]` 算成效果擁有者自己,MP 沒有真正給到對手——遷移前就存在的既有缺陷。
# 遷移方式待決定,見 openspec/changes/effect-tree-migration/design.md「已知阻礙」。
reg.event("E-022", when=lambda g, p: any(n in g.state.players[p].discarded_this_turn and g.db[n].type == PARTNER for n in g.state.players[p].discard), effect=Coin(count=1, on=HeadsAtLeast(1), then=Choose(PartnerDiscardedThisTurn(), bind="choice", prompt="e022_pick", then=AttachPartnerFromDiscard())))
reg.event("E-026", effect=Coin(count=2, on=Always(), then=GainMpPerHeads(per_head=2)))
reg.spell_rider("S-003", counter=True)
reg.spell_rider("S-004", on_damage=Coin(count=1, on=HeadsAtLeast(1), then=RestrictOpponent(flag=NO_SPELLS, duration=DUR_UNTIL_END_NEXT_TURN)))
reg.spell_rider("S-007", on_damage=RestrictOpponent(flag=NO_PARTNER_EFFECTS, duration=DUR_UNTIL_END_NEXT_TURN))
reg.spell_rider("S-009", on_damage=RestrictOpponent(flag=NO_SPELLS, duration=DUR_UNTIL_END_NEXT_TURN))
reg.spell_rider("S-011", on_damage=RestrictOpponent(flag=NO_SPELLS, duration=DUR_UNTIL_END_NEXT_TURN))
reg.spell_rider("S-014", on_damage=Coin(count=1, on=HeadsAtLeast(1), then=RestrictOpponent(flag=NO_SPELLS, duration=DUR_UNTIL_END_NEXT_TURN)))
reg.spell_rider("S-016", on_declare=When(SideIs("defense"), then=AddDefenseSelfBonus(amount=1000)))
reg.spell_rider("S-017", on_declare=When(SideIs("attack"), then=AddAttackSelfBonus(amount=2000)))
reg.spell_rider("S-021", on_declare=When(SideIs("defense"), then=Coin(count=2, on=HeadsAtLeast(1), then=NegateAttack())))
reg.spell_rider("S-025", on_declare=When(SideIs("defense"), then=Coin(count=1, on=HeadsAtLeast(1), then=NegateAttack())))
reg.spell_nonbattle("S-026", effect=Coin(count=1, on=HeadsAtLeast(1), then=MakeNextAttackUndefendable()))
reg.spell_rider("S-027", on_declare=When(SideIs("defense"), then=Coin(count=2, on=HeadsAtLeast(1), then=AdjustDefenseDamage(amount=-1))))
reg.spell_rider("S-030", counter=True)
reg.spell_rider("S-031", on_declare=When(SideIs("attack"), then=MarkInjuredMamodoDiscarded()))
reg.spell_rider("S-032", damage_cap=3)
reg.spell_rider("S-033", on_damage=AddPowerToAllOpponentMamodo(amount=-2000, duration=DUR_UNTIL_END_NEXT_TURN))
reg.spell_rider("S-034", damage_cap=4)
reg.spell_rider("S-035", on_declare=When(SideIs("attack"), then=Coin(count=2, on=HeadsAtLeast(2), then=DisableBookProtection())))
reg.spell_rider("S-037", on_damage=Coin(count=1, on=HeadsAtLeast(1), then=GrantFullImmune()))
reg.spell_rider("S-038", on_damage=GrantFullImmune())
reg.spell_rider("S-039", on_damage=Choose(OpponentPartneredMamodo(), bind="choice", prompt="s039_pick", then=DiscardChosenPartner()))
reg.spell_rider("S-040", on_declare=When(SideIs("attack"), then=Coin(count=3, on=Always(), then=AddAttackBonusPerHeads(per_head=2000))))
reg.spell_nonbattle("S-041", effect=Coin(count=1, on=HeadsAtLeast(1), then=GrantFullImmune()))
reg.spell_rider("S-045", on_declare=When(SideIs("attack"), then=Coin(count=2, on=HeadsAtLeast(2), then=MakeAttackUndefendable())))
reg.spell_rider("S-046", on_declare=When(SideIs("attack"), then=Coin(count=1, on=HeadsAtLeast(1), then=MakeAttackUndefendable())))
reg.spell_nonbattle("S-057", effect=Coin(count=1, on=HeadsAtLeast(1), then=ScheduleInjureInsteadNextWin()))
reg.spell_rider("S-058", injure_instead=True)
