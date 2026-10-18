"""戰術卡(S-xxx)的效果登記。依卡號排序,排版規則見 `cards/__init__.py`。"""

from ...state import (
    DUR_TURN, DUR_UNTIL_END_NEXT_TURN, DUR_UNTIL_END_OWN_NEXT_TURN, NO_DEFENSE, NO_EFFECTS_AND_SPELLS,
    DUR_BATTLE, NO_PARTNER_EFFECTS, NO_SPELLS,
)
from .. import registry as reg
from ..tree import (
    AddAttackBonusPerHeads, AddAttackSelfBonus, AddDefenseSelfBonus, AddPowerToAllOpponentMamodo,
    AdjustDefenseDamage, All, Always, AnyOf, AttackBookDamage, BattleRemembered, Bound, CanStackFromBook, Choose,
    Coin, DamageBonusIfAttackTotalAtLeast, DamageOpponentBookOutsideBattle, DamageOpponentBookAndAllMamodo, DisableBookProtection,
    DiscardChosenPartner, DiscardFromOpponentBook, DiscardOwnMamodoByNumber, EffectOptions,
    FinishAttackWithoutDamage, GainMpPerDamage, GrantFullImmune, GrantGuardImmune, HasOptions,
    HeadsAtLeast, HealOwnFamily, HealSlot, IncreaseThisSpellDamage, InjureOpponentMamodoInstead,
    LockChosenOpponentMamodo, MakeAttackUndefendable, MakeNextAttackUndefendable,
    MarkInjuredMamodoDiscarded, NegateAttack, NegateAttackAtEffectsEnd, NextStartPhase,
    OpponentMamodo, OpponentOpenPageCards, OpponentOpenPagesLackSpell, OpponentPartneredMamodo,
    OrSkip, OwnBookCopiesOf, OwnFieldHas, OwnInjuredMamodo, PeekOpponentOpenPages,
    PlayMamodoFromBook, ReduceOpponentMp, Ref, RememberInBattle, RememberOpponentMamodo,
    RestrictBothPlayers, RestrictOpponent, RobnosTransformMode, ScheduleAfterBattleAttrPower,
    ScheduleAfterBattleRestriction, ScheduleInjureInsteadNextWin, ScheduleSpellReuse, Sequence,
    SideIs, StackFromBookOnto, Standby, TurnOwnPagesOncePerTurn, UsedSpellPagesThisTurn, When,
    opponent_has_mamodo,
)

# S-022 セウシル / S-024 マ・セシルド / S-028 伏せろ!:防禦獲勝時將攻擊無效 = 防方獲勝本就使攻方
# 效果不解決,不需註冊(純資料驅動)。純香草戰術卡(攻/防獲勝→魔書傷害)同樣不需註冊:
# S-001 等第一彈香草戰術,以及第二彈 S-029 S-044 S-047 S-049 S-050 S-051 S-052 S-053 S-054 S-055。
# 第三彈的香草戰術:S-059 S-065 S-071 S-080 S-085 S-091 S-096 S-099 S-102 S-105;S-063 為防禦獲勝時無效(資料驅動)。

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

# 「このバトルの『効果の使用』の最後に、相手の攻撃を無効にする」:擲幣於宣告時,無效於雙方 pass 之後
reg.spell_rider("S-021", on_declare=When(
    SideIs("defense"),
    then=Coin(
        count=2, on=HeadsAtLeast(1),
        then=NegateAttackAtEffectsEnd(),
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

reg.spell_rider("S-036", on_declare=When(
    SideIs("attack"),
    then=RememberOpponentMamodo(),
), on_win=DamageOpponentBookAndAllMamodo(), on_win_owns_damage=True)

reg.spell_rider("S-037", on_damage=Coin(
    count=1, on=HeadsAtLeast(1),
    then=GrantFullImmune(),
))

reg.spell_rider("S-038", on_damage=GrantFullImmune())

reg.spell_rider("S-039", on_damage=Choose(
    OpponentPartneredMamodo(discard=True), bind="choice", prompt="pick_opponent_partner",
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
                Choose(   # 第二張只剩一張也由玩家選(實體操作:選一張放出、再選一張放出)
                    OwnBookCopiesOf("M-024"), bind="page", prompt="pick_mamodo_in_own_book", auto_single=False,
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

# ---------------------------------------------------------------- 第三彈

reg.spell_rider("S-060", on_declare=When(
    SideIs("attack"),
    then=Coin(
        count=1, on=HeadsAtLeast(1),
        then=DisableBookProtection(),
    ),
))

reg.spell_rider("S-061", counter=True, counter_damage_from_attack=True)

# 「魔力勝負の勝敗にかかわらず、このバトル後」:宣告時排定,本場戰鬥結束時生效(攻擊被無效時不生效)
reg.spell_rider("S-062", on_declare=When(
    SideIs("attack"),
    then=ScheduleAfterBattleAttrPower(attr="氷", amount=2000, duration=DUR_UNTIL_END_OWN_NEXT_TURN),
))

reg.spell_rider("S-064", injure_instead=True)
reg.spell_rider("S-066", counter=True)
reg.spell_rider("S-067", extra_cost=(2, 6, 2000, 1))

# 擲幣於宣告時(規則「宣言時にコインを投げます」);正面時本場戰鬥結束後才開始禁戰術
reg.spell_rider("S-068", on_declare=When(
    SideIs("attack"),
    then=Coin(
        count=1, on=HeadsAtLeast(1),
        then=ScheduleAfterBattleRestriction(flag=NO_SPELLS, duration=DUR_TURN, restricts=("spells",)),
    ),
))

reg.spell_rider("S-069", on_declare=When(
    SideIs("attack"),
    then=Sequence(steps=(
        MakeAttackUndefendable(),
        Coin(
            count=1, on=HeadsAtLeast(1),
            then=RememberInBattle(key="coin_heads"),
        ),
    )),
    otherwise=Coin(
        count=1, on=HeadsAtLeast(1),
        then=NegateAttack(),
    ),
), on_win=When(
    BattleRemembered(key="coin_heads"),
    then=AttackBookDamage(),
    otherwise=FinishAttackWithoutDamage(),
), on_win_owns_damage=True)

# 「次の効果の1つを使う」:攻擊宣告時由攻擊方選擇魔書傷害或對手魔物傷害(選魔物時一併選哪一隻;
# 對手沒有魔物時只有魔書);獲勝時依宣告時的選擇結算
reg.spell_rider("S-070", on_declare=Choose(
    EffectOptions((("book", "damage_book", None), ("mamodo", "damage_mamodo", OpponentMamodo()))),
    bind="mode", prompt="pick_effect",
    then=Sequence(steps=(
        RememberInBattle(key="effect_mode", ref=Ref("mode")),
        When(
            Bound("mode", "mamodo"),
            then=Choose(
                OpponentMamodo(), bind="slot", prompt="pick_opponent_mamodo",
                then=RememberInBattle(key="injure_target", ref=Ref("slot")),
            ),
        ),
    )),
), on_win=When(
    BattleRemembered(key="effect_mode", value="book"),
    then=AttackBookDamage(),
    otherwise=InjureOpponentMamodoInstead(),
), on_win_owns_damage=True)

# 「自分の『ダニー』を『健康状態』にする」:沒有負傷的ダニー也可使用(比照 E-040),只是沒有效果
reg.spell_nonbattle("S-072", effect=HealOwnFamily(family="ダニー"))
reg.spell_nonbattle("S-073", effect=RestrictOpponent(flag=NO_DEFENSE, duration=DUR_TURN))

# 待命至下回合開始階段、下回合中持續:使用時就選好對手的魔物(比照 E-001)
reg.spell_nonbattle("S-074", when=opponent_has_mamodo, effect=Choose(
    OpponentMamodo(), bind="choice", prompt="pick_opponent_mamodo",
    then=Standby(
        NextStartPhase(), expires="next_start", restricts=("spells", "mamodo_effects"),
        then=LockChosenOpponentMamodo(),
    ),
))

reg.spell_nonbattle("S-075",
                    effect=RestrictBothPlayers(flag=NO_EFFECTS_AND_SPELLS, duration=DUR_UNTIL_END_OWN_NEXT_TURN))

reg.spell_rider("S-076", on_declare=When(
    SideIs("attack"),
    then=MarkInjuredMamodoDiscarded(),
))

reg.spell_rider("S-077", on_declare=When(
    SideIs("attack"),
    then=MarkInjuredMamodoDiscarded(),
))

reg.spell_rider("S-078", on_damage=Sequence(steps=(
    PeekOpponentOpenPages(),
    When(
        HasOptions(OpponentOpenPageCards()),
        then=Choose(
            OpponentOpenPageCards(), bind="page", prompt="pick_opponent_book_card",
            then=DiscardFromOpponentBook(),
        ),
    ),
)))

reg.spell_rider("S-079", on_declare=When(
    SideIs("defense"),
    then=GrantGuardImmune(mamodo="ウォンレイ"),
))

reg.spell_rider("S-081", on_declare=When(
    SideIs("attack"),
    then=Coin(
        count=1, on=HeadsAtLeast(1),
        then=DisableBookProtection(),
    ),
))

reg.spell_rider("S-082", on_declare=When(
    SideIs("attack"),
    then=Coin(
        count=1, on=HeadsAtLeast(1),
        then=IncreaseThisSpellDamage(amount=1),
    ),
))

reg.spell_rider("S-083", on_declare=When(
    SideIs("attack"),
    then=Coin(
        count=1, on=HeadsAtLeast(1),
        then=IncreaseThisSpellDamage(amount=2),
    ),
))

reg.spell_rider("S-084", on_declare=When(
    SideIs("attack"),
    then=Coin(
        count=1, on=HeadsAtLeast(1),
        then=MakeAttackUndefendable(),
    ),
))

# 魔書中選得到 M-046、且場上有它的疊放對象(ウマゴン)才能使用(比照 S-048)
reg.spell_nonbattle("S-086", when=CanStackFromBook("M-046"), effect=Choose(
    OwnBookCopiesOf("M-046"), bind="page", prompt="pick_mamodo_in_own_book",
    then=StackFromBookOnto(),
))

reg.spell_rider("S-087", fixed_total={"attack": 8000, "defense": 11000})
reg.spell_rider("S-092", on_declare=When(
    SideIs("attack"),
    then=AddAttackSelfBonus(amount=2000),
))

reg.spell_nonbattle("S-093", effect=Coin(
    count=1, on=HeadsAtLeast(1),
    then=ReduceOpponentMp(amount=3),
))

reg.spell_nonbattle("S-094", effect=Coin(
    count=1, on=HeadsAtLeast(1),
    then=DamageOpponentBookOutsideBattle(),
))

# 宣告防禦時擲幣;正面時魔力勝負時(不論勝敗,防禦沒被無效)起本回合自己的キャンチョメ不受傷害
reg.spell_rider("S-095", on_declare=When(
    SideIs("defense"),
    then=Coin(
        count=1, on=HeadsAtLeast(1),
        then=RememberInBattle(key="defender_no_damage_family", value="キャンチョメ"),
    ),
))

reg.spell_rider("S-097", extra_cost=(2, 2, 4000, 0))

# 「片方または両方を、この順で」:依序詢問。有負傷魔物時先問是否回復,回復後再選要重用的戰術(可不使用);
# 不回復時直接選要重用的戰術(至少一個)。重用的對象在使用時選定(本回合已用過的戰術,S-098 自己除外)
reg.spell_nonbattle("S-098", when=AnyOf(HasOptions(OwnInjuredMamodo()), HasOptions(UsedSpellPagesThisTurn())),
                    effect=When(
    HasOptions(OwnInjuredMamodo()),
    then=When(
        HasOptions(UsedSpellPagesThisTurn()),
        then=Choose(
            OrSkip(EffectOptions((("heal", "heal_injured", OwnInjuredMamodo()),))),
            bind="first", prompt="pick_effect",
            then=When(
                Bound("first", "heal"),
                then=Sequence(steps=(
                    Choose(
                        OwnInjuredMamodo(), bind="slot", prompt="pick_own_injured_mamodo",
                        then=HealSlot(target=Ref("slot")),
                    ),
                    Choose(
                        OrSkip(UsedSpellPagesThisTurn()), bind="reuse_page", prompt="pick_used_spell",
                        then=When(
                            Bound("reuse_page", None),
                            otherwise=ScheduleSpellReuse(),
                        ),
                    ),
                )),
                otherwise=Choose(
                    UsedSpellPagesThisTurn(), bind="reuse_page", prompt="pick_used_spell",
                    then=ScheduleSpellReuse(),
                ),
            ),
        ),
        otherwise=Choose(
            OwnInjuredMamodo(), bind="slot", prompt="pick_own_injured_mamodo",
            then=HealSlot(target=Ref("slot")),
        ),
    ),
    otherwise=Choose(
        UsedSpellPagesThisTurn(), bind="reuse_page", prompt="pick_used_spell",
        then=ScheduleSpellReuse(),
    ),
))

reg.spell_rider("S-100", on_declare=When(
    SideIs("attack"),
    then=MakeAttackUndefendable(),
), damage_regardless=True)

reg.spell_rider("S-101", on_declare=When(
    SideIs("attack"),
    then=RememberOpponentMamodo(),
), on_win=DamageOpponentBookAndAllMamodo(), on_win_owns_damage=True)

reg.spell_rider("S-103", on_win=RestrictOpponent(flag="no_book_cards", duration=DUR_BATTLE))

# 「相手の魔本を見て」:攻擊成功時(造成傷害前)才檢視並判斷 +2(使用者確認;不在宣告時)
reg.spell_rider("S-104", on_win=Sequence(steps=(
    PeekOpponentOpenPages(),
    When(
        OpponentOpenPagesLackSpell(),
        then=IncreaseThisSpellDamage(amount=2),
    ),
)))

reg.spell_rider("S-106", on_declare=When(
    SideIs("defense"),
    then=Sequence(steps=(
        NegateAttack(),
        TurnOwnPagesOncePerTurn(leaves=1),
    )),
))
