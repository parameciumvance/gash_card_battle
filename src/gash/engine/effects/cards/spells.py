"""戰術卡(S-xxx)的效果登記。依卡號排序,排版規則見 `cards/__init__.py`。"""

from ...state import DUR_UNTIL_END_NEXT_TURN, NO_PARTNER_EFFECTS, NO_SPELLS
from .. import registry as reg
from ..tree import (
    AddAttackBonusPerHeads, AddAttackSelfBonus, AddDefenseSelfBonus, AddPowerToAllOpponentMamodo,
    AdjustDefenseDamage, All, Always, Bound, Choose, Coin, DamageBonusIfAttackTotalAtLeast,
    DamageOpponentBookAndAllMamodo, DisableBookProtection, DiscardChosenPartner,
    DiscardOwnMamodoByNumber, GainMpPerDamage, GrantFullImmune, HasOptions, HeadsAtLeast,
    MakeAttackUndefendable, MakeNextAttackUndefendable, MarkInjuredMamodoDiscarded, NegateAttack,
    OpponentPartneredMamodo, OwnBookCopiesOf, OwnFieldHas, PlayMamodoFromBook, ReduceOpponentMp,
    RestrictOpponent, RobnosTransformMode, ScheduleInjureInsteadNextWin, Sequence, SideIs,
    StackFromBookOnto, When,
)

# S-022 セウシル / S-024 マ・セシルド / S-028 伏せろ!:防禦獲勝時將攻擊無效 = 防方獲勝本就使攻方
# 效果不解決,不需註冊(純資料驅動)。純香草戰術卡(攻/防獲勝→魔書傷害)同樣不需註冊:
# S-001 等第一彈香草戰術,以及第二彈 S-029 S-044 S-047 S-049 S-050 S-051 S-052 S-053 S-054 S-055。

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
    OpponentPartneredMamodo(), bind="choice", prompt="pick_opponent_partner",
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

# 至少一種模式可完整執行才能使用(選得到對象);分裂比照效果文由玩家選剛好 2 張
reg.spell_nonbattle("S-043", when=HasOptions(RobnosTransformMode()), effect=Choose(
    RobnosTransformMode(), bind="mode", prompt="pick_transform_mode",
    then=Sequence(steps=(
        When(
            Bound("mode", "fuse"),
            then=Sequence(steps=(
                DiscardOwnMamodoByNumber(number="M-024", count=2),
                Choose(
                    OwnBookCopiesOf("M-025"), bind="page", prompt="pick_mamodo_in_own_book",
                    then=PlayMamodoFromBook(),
                ),
            )),
        ),
        When(
            Bound("mode", "split"),
            then=Sequence(steps=(
                DiscardOwnMamodoByNumber(number="M-025", count=1),
                Choose(
                    OwnBookCopiesOf("M-024"), bind="page", prompt="pick_mamodo_in_own_book",
                    then=PlayMamodoFromBook(),
                ),
                Choose(
                    OwnBookCopiesOf("M-024"), bind="page", prompt="pick_mamodo_in_own_book",
                    then=PlayMamodoFromBook(),
                ),
            )),
        ),
    )),
))

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

# 場上有 M-028 且魔書有 M-027 才能使用(選得到對象)
reg.spell_nonbattle("S-048", when=All(OwnFieldHas("M-028"), HasOptions(OwnBookCopiesOf("M-027"))),
                    effect=Choose(
    OwnBookCopiesOf("M-027"), bind="page", prompt="pick_mamodo_in_own_book",
    then=StackFromBookOnto(base="M-028"),
))

reg.spell_rider("S-056", on_defense_damaged=GainMpPerDamage(per_point=2))

reg.spell_nonbattle("S-057", effect=Coin(
    count=1, on=HeadsAtLeast(1),
    then=ScheduleInjureInsteadNextWin(),
))

reg.spell_rider("S-058", injure_instead=True)
