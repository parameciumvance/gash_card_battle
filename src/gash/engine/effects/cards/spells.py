"""戰術卡(S-xxx)的效果登記。依卡號排序,排版規則見 `cards/__init__.py`。"""

from ...state import (
    DUR_TURN, DUR_UNTIL_END_NEXT_TURN, DUR_UNTIL_END_OWN_NEXT_TURN, NO_DEFENSE, NO_EFFECTS_AND_SPELLS,
    DUR_BATTLE, NO_DISCARD_COST_EFFECTS, NO_EVENTS, NO_PARTNER_EFFECTS, NO_SPELLS,
)
from .. import registry as reg
from ..tree import (
    GuardBookAndNamedMamodo, LockOpponentMamodoPerHeads, OpponentMamodoCount, OpponentUsedAttrLastTurn,
    RestrictOwnNamedSpells, ScheduleAnyPageUse, ScheduleAttackSpellBoost, opponent_has_mamodo,
    AddSpellPowerPerHeads, AddSpellSelfBonus, CounterBookDamage, EndBattleWithoutCounter, TurnPagesForward, AddAttackSelfBonus, AddDefenseSelfBonus, AddPowerToAllOpponentMamodo,
    AdjustDefenseDamage, All, Always, AttachPartnerFromDiscard, AnyOf, AttackBookDamage, BattleRemembered, Bound, CanStackFromBook, Choose,
    Coin, DamageBonusIfAttackTotalAtLeast, DamageOpponentBookOutsideBattle, DamageOpponentBookAndAllMamodo, DisableProtection,
    DiscardChosenPartner, DiscardFromOpponentBook, DiscardOwnMamodoByNumber, EffectOptions,
    FinishAttackWithoutDamage, GainMpPerDamage, GrantFullImmune, GrantGuardImmune, HasOptions,
    HeadsAtLeast, HealOwnFamily, HealSlot, IncreaseThisSpellDamage, InjureOpponentMamodoInstead,
    LockChosenOpponentMamodo, MakeAttackUndefendable, MakeNextAttackUndefendable,
    MarkInjuredMamodoDiscarded, NegateAttack, NextStartPhase, AttackNotNegated,
    OpponentMamodo, OpponentOpenPageCards, OpponentOpenPagesLackSpell, OpponentPartneredMamodo,
    OrSkip, OwnBookCopiesOf, PlayablePartnerInDiscard, ScheduleNextBattleStandby, OwnFieldHas, OwnInjuredMamodo, PeekOpponentOpenPages,
    PlayMamodoFromBook, ReduceOpponentMp, Ref, RememberInBattle, RememberOpponentMamodo,
    RestrictBothPlayers, RestrictOpponent, RobnosTransformMode, ScheduleAfterBattleAttrPower,
    ScheduleAfterBattleRestriction, ScheduleInjureInsteadNextWin, ScheduleSpellReuse, Sequence,
    SideIs, StackFromBookOnto, Standby, TurnOwnPagesOncePerTurn, UsedSpellPagesThisTurn, When,
    opponent_has_mamodo, DiscardRememberedPartner, IncreaseThisSpellDamagePerHeads, OpponentDidNotDefend,
    OwnDiscardMamodoCards, RememberDeclaredTarget, AsOpponent, AttackAttrIs, AttackDamageIs,
    DiscardRememberedPartners, OpponentDiscardablePartnerCount, OwnUsedSpellNamedLastTurn, RememberPartnersPerHeads,
    RestrictInBattle, ReturnableOwnMamodo, ReturnSlotToBook, StealOpponentMp, UserPowerExceedsOpponentsBy,
    DeployableMamodoInOwnBook, DeployMamodoFromBook, FamilyNoDamage, FamilyUnselectable, GrantFamilyFighting,
    LockUserSlot, ScheduleSpellFromNextSpreads,
)

# S-022 セウシル / S-024 マ・セシルド / S-028 伏せろ!:防禦獲勝時將攻擊無效 = 防方獲勝本就使攻方
# 效果不解決,不需註冊(純資料驅動)。純香草戰術卡(攻/防獲勝→魔書傷害)同樣不需註冊:
# S-001 等第一彈香草戰術,以及第二彈 S-029 S-044 S-047 S-049 S-050 S-051 S-052 S-053 S-054 S-055。
# 第三彈的香草戰術:S-059 S-065 S-071 S-080 S-085 S-091 S-096 S-099 S-102 S-105;S-063 為防禦獲勝時無效(資料驅動)。
# 第 3 賽季的香草戰術:S-107 Ex-013 Ex-017 Ex-020 Ex-038〜Ex-042;Ex-018 / Ex-019 為防禦獲勝時無效(資料驅動)。

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
        then=RememberInBattle(key="defense_coin_heads"),
    ),
), on_effects_end=When(
    BattleRemembered(key="defense_coin_heads"),
    then=NegateAttack(),
))

reg.spell_rider("S-025", on_declare=When(
    SideIs("defense"),
    then=Coin(
        count=1, on=HeadsAtLeast(1),
        then=RememberInBattle(key="defense_coin_heads"),
    ),
), on_effects_end=When(
    BattleRemembered(key="defense_coin_heads"),
    then=NegateAttack(),
))

reg.spell_nonbattle("S-026", effect=Coin(
    count=1, on=HeadsAtLeast(1),
    then=MakeNextAttackUndefendable(),
))

reg.spell_rider("S-027", on_declare=When(
    SideIs("defense"),
    then=Coin(
        count=2, on=HeadsAtLeast(1),
        then=RememberInBattle(key="defense_coin_heads"),
    ),
), on_effects_end=When(
    BattleRemembered(key="defense_coin_heads"),
    then=AdjustDefenseDamage(amount=-1),
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
        then=DisableProtection(),
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

reg.spell_rider("S-040", on_declare=Coin(
    count=3, on=Always(),
    then=AddSpellPowerPerHeads(per_head=2000),
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
        then=DisableProtection(),
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
        then=RememberInBattle(key="defense_coin_heads"),
    ),
), on_win=When(
    BattleRemembered(key="coin_heads"),
    then=AttackBookDamage(),
    otherwise=FinishAttackWithoutDamage(),
), on_win_owns_damage=True, on_effects_end=When(
    BattleRemembered(key="defense_coin_heads"),
    then=NegateAttack(),
))

# 「次の効果の1つを使う」:攻擊宣告時由攻擊方選擇魔書傷害或對手魔物傷害(選魔物時一併選哪一隻;
# 對手沒有魔物時只有魔書);獲勝時依宣告時的選擇結算。選擇時已明確選了對象,S-057 不改變
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
), on_win_owns_damage=True, chooses_damage_target=True)

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

reg.spell_rider("S-079", on_effects_end=GrantGuardImmune(mamodo="ウォンレイ"))

reg.spell_rider("S-081", on_declare=When(
    SideIs("attack"),
    then=Coin(
        count=1, on=HeadsAtLeast(1),
        then=DisableProtection(),
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

# 擲出正面就生效,不詢問是否使用(比照 S-026,使用者確認);費用 0 在下一場戰鬥宣告戰術時自動套用
reg.spell_nonbattle("S-088", effect=Coin(
    count=2, on=HeadsAtLeast(2),
    then=ScheduleNextBattleStandby(kind="spell_base_cost_zero"),
))

# 擲出正面就生效(比照 S-026);對象在攻擊宣告時選,魔力勝負時取其當下的魔力
reg.spell_nonbattle("S-089", effect=Coin(
    count=1, on=HeadsAtLeast(1),
    then=ScheduleNextBattleStandby(kind="attack_power_from_mamodo"),
))

# 棄牌區有可放出的搭檔才能使用(選不到對象時不能使用);放出的搭檔回合結束時棄掉
reg.spell_nonbattle("S-090", when=HasOptions(PlayablePartnerInDiscard()), effect=Coin(
    count=1, on=HeadsAtLeast(1),
    then=Choose(
        PlayablePartnerInDiscard(), bind="choice", prompt="pick_partner_in_discard",
        then=AttachPartnerFromDiscard(spec=PlayablePartnerInDiscard(), until_turn_end=True),
    ),
))

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

# 宣告防禦時擲幣;正面時於「効果の使用」的最後(不論勝敗,防禦沒被無效)起本回合自己的キャンチョメ不受傷害
# (依家族,之後上場的キャンチョメ也算)
reg.spell_rider("S-095", on_declare=When(
    SideIs("defense"),
    then=Coin(
        count=1, on=HeadsAtLeast(1),
        then=RememberInBattle(key="defense_coin_heads"),
    ),
), on_effects_end=When(
    BattleRemembered(key="defense_coin_heads"),
    then=FamilyNoDamage(family="キャンチョメ", duration=DUR_TURN),
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

# 「そうしたなら」:攻擊在「効果の使用」中已被其他效果無效時,這張沒有使它無效,不翻魔書
reg.spell_rider("S-106", on_effects_end=When(
    AttackNotNegated(),
    then=Sequence(steps=(
        NegateAttack(),
        TurnOwnPagesOncePerTurn(leaves=1),
    )),
))

reg.spell_rider("S-108", on_declare=Coin(
    count=1, on=HeadsAtLeast(1),
    then=AddSpellSelfBonus(amount=2000),
))

# S-109:「魔力勝負で勝ったとき、コインを投げて」→ 獲勝時才擲幣(不在宣告時)
reg.spell_rider("S-109", counter=True, on_counter=Coin(
    count=1, on=HeadsAtLeast(1),
    then=CounterBookDamage(),
    otherwise=EndBattleWithoutCounter(),
))

reg.spell_rider("S-110", on_damage=RestrictOpponent(flag=NO_SPELLS, duration=DUR_TURN))

reg.spell_rider("S-111", on_declare=Coin(
    count=1, on=HeadsAtLeast(1),
    then=DisableProtection(),
))

reg.spell_rider("S-112", on_protected=TurnPagesForward(leaves=1, target="opponent"))

# 第 4 賽季第 1 批(season4-spells-basic)。香草戰術:S-119 S-122 S-123 S-124 S-126 S-127 S-138 Ex-062 Ex-066
# Ex-067;S-114 為防禦獲勝時無效(資料驅動)。

# 「自分の『ガッシュ・ベル』は、以下の『魔物の効果』を持つ」:期間中上場的也算,多張不疊加(atwiki FAQ);
# 《格闘》費用 0、合計魔力 10000 攻擊(魔書傷害 1)或防禦,每回合 1 次
reg.spell_nonbattle("S-113", effect=GrantFamilyFighting(family="ガッシュ・ベル", power=10000, damage=1,
                                                         duration=DUR_UNTIL_END_OWN_NEXT_TURN))

# 「次の効果の両方を、この順で使う」:攻擊宣告時擲幣、正面時選對手 1 隻魔物;獲勝時魔書傷害 + 選定魔物的傷害
# (魔物傷害不以魔書受到傷害為條件;S-057 只改變魔書傷害)
reg.spell_rider("S-115", on_declare=Sequence(steps=(
    RememberInBattle(key="declared_targets", value=()),
    Coin(
        count=1, on=HeadsAtLeast(1),
        then=Choose(
            OpponentMamodo(), bind="slot", prompt="pick_opponent_mamodo",
            then=RememberDeclaredTarget(ref=Ref("slot")),
        ),
    ),
)), on_win=DamageOpponentBookAndAllMamodo(), on_win_owns_damage=True)

reg.spell_rider("S-116", on_win=RestrictOpponent(flag=NO_EFFECTS_AND_SPELLS, duration=DUR_UNTIL_END_NEXT_TURN))

# 「このバトル中、相手はイベントカードを使えない」:宣告時起(攻防都適用),這張戰術被無效時解除
reg.spell_rider("S-117", on_declare=RestrictInBattle(flag=NO_EVENTS, who="opponent"))

# 「次の効果の1つを使う」:比照 S-070,攻擊宣告時選擇魔書傷害或棄掉對手 1 張搭檔(一併選擇);獲勝時依選擇結算
reg.spell_rider("S-118", on_declare=Choose(
    EffectOptions((("book", "damage_book", None),
                   ("partner", "discard_opponent_partner", OpponentPartneredMamodo(discard=True)))),
    bind="mode", prompt="pick_effect",
    then=Sequence(steps=(
        RememberInBattle(key="effect_mode", ref=Ref("mode")),
        When(
            Bound("mode", "partner"),
            then=Choose(
                OpponentPartneredMamodo(discard=True), bind="choice", prompt="pick_opponent_partner",
                then=RememberInBattle(key="partner_target", ref=Ref("choice")),
            ),
        ),
    )),
), on_win=When(
    BattleRemembered(key="effect_mode", value="book"),
    then=AttackBookDamage(),
    otherwise=Sequence(steps=(
        DiscardRememberedPartner(key="partner_target"),
        FinishAttackWithoutDamage(),
    )),
), on_win_owns_damage=True, chooses_damage_target=True)

reg.spell_rider("S-120", on_declare=When(
    SideIs("defense"),
    then=Coin(
        count=2, on=HeadsAtLeast(1),
        then=RememberInBattle(key="defense_coin_heads"),
    ),
), on_effects_end=When(
    BattleRemembered(key="defense_coin_heads"),
    then=NegateAttack(),
))

# 自分の「バランシャ」はダメージを受けず、相手は「カードを選ぶ」とき選ぶことができない(期間中上場的也算;
# 「すべてを選ぶ」也排除)
reg.spell_nonbattle("S-121", effect=Sequence(steps=(
    FamilyNoDamage(family="バランシャ", duration=DUR_UNTIL_END_NEXT_TURN),
    FamilyUnselectable(family="バランシャ", duration=DUR_UNTIL_END_NEXT_TURN),
)))

# 對手每張可棄的搭檔依場上順序各擲 1 次(結果不受順序影響,不讓玩家選順序,比照 Ex-044);獲勝時棄掉正面的
reg.spell_rider("S-125", on_declare=When(
    HasOptions(OpponentPartneredMamodo(discard=True)),
    then=Coin(
        count=OpponentDiscardablePartnerCount(), on=Always(),
        then=RememberPartnersPerHeads(),
    ),
), on_win=DiscardRememberedPartners(), no_book_damage=True)

# 魔力勝負に勝ったとき無効(資料驅動);勝敗にかかわらず「雷」属性の攻撃を無効
reg.spell_rider("S-128", on_effects_end=When(
    AttackAttrIs(attr="雷"),
    then=NegateAttack(),
))

reg.spell_rider("S-129", on_declare=When(
    OwnUsedSpellNamedLastTurn(name="アシルド"),
    then=Sequence(steps=(
        AddSpellSelfBonus(amount=4000),
        IncreaseThisSpellDamage(amount=2),
    )),
))

# 防禦時「魔力勝負の勝敗にかかわらず、相手の攻撃のダメージを2へらす」;攻擊時是一般的魔書傷害
reg.spell_rider("S-130", on_effects_end=AdjustDefenseDamage(amount=-2))

# 「このバトル中、自分も相手も、パートナーの効果やイベントの効果を使えない」:宣告時起,被無效時解除
reg.spell_rider("S-131", on_declare=Sequence(steps=(
    RestrictInBattle(flag=NO_PARTNER_EFFECTS, who="both"),
    RestrictInBattle(flag=NO_EVENTS, who="both"),
)))

reg.spell_rider("S-132", on_win=When(
    OpponentDidNotDefend(),
    then=IncreaseThisSpellDamage(amount=1),
))

reg.spell_rider("S-133", on_damage=StealOpponentMp(amount=3))

reg.spell_rider("S-134", on_declare=When(
    SideIs("attack"),
    then=Coin(
        count=1, on=HeadsAtLeast(1),
        then=IncreaseThisSpellDamage(amount=1),
    ),
), fixed_total={"attack": 7000, "defense": 7000})

# ●選んだ相手の魔物の「魔物の効果」や術を使えない ●この術を使うのに使った「ニャルラト」も使えない;
# 選不到對手的魔物時不能使用(比照 S-074)
reg.spell_nonbattle("S-136", when=opponent_has_mamodo, effect=Sequence(steps=(
    Choose(
        OpponentMamodo(), bind="choice", prompt="pick_opponent_mamodo",
        then=LockChosenOpponentMamodo(duration=DUR_UNTIL_END_OWN_NEXT_TURN),
    ),
    LockUserSlot(duration=DUR_UNTIL_END_OWN_NEXT_TURN),
)))

# 「この術のダメージは、コインを2回投げて、オモテの数×1になる」:傷害只在攻擊時有用,攻擊宣告時擲
reg.spell_rider("S-137", on_declare=When(
    SideIs("attack"),
    then=Coin(
        count=2, on=Always(),
        then=IncreaseThisSpellDamagePerHeads(per_head=1),
    ),
))

reg.spell_rider("S-139", on_effects_end=AdjustDefenseDamage(amount=-2))

# 「この術は、自分の場に『ノリトー・ハッサミー』がいなくても使える」;沒有可放出的時不能使用(比照 E-012)
reg.spell_no_user("S-140")
reg.spell_nonbattle("S-140", when=HasOptions(DeployableMamodoInOwnBook(name="ノリトー・ハッサミー")), effect=Choose(
    DeployableMamodoInOwnBook(name="ノリトー・ハッサミー"), bind="page", prompt="pick_mamodo_in_own_book",
    then=DeployMamodoFromBook(),
))

reg.spell_rider("S-141", on_damage=RestrictOpponent(flag=NO_SPELLS, duration=DUR_UNTIL_END_NEXT_TURN))

reg.spell_rider("S-142", on_declare=When(
    SideIs("attack"),
    then=Coin(
        count=1, on=HeadsAtLeast(1),
        then=IncreaseThisSpellDamage(amount=1),
    ),
))

# 「この術の魔力は、自分の捨て札の魔物カードの数×2000になる」:魔力勝負時依當下張數計算
reg.spell_rider("S-143", power_per_count=(OwnDiscardMamodoCards(), 2000))

reg.spell_nonbattle("S-144", effect=RestrictOpponent(flag=NO_DISCARD_COST_EFFECTS, duration=DUR_UNTIL_END_NEXT_TURN))

# 擲出正面就生效,不詢問是否使用(比照 S-026,使用者確認);「4枚後ろ」比照 M-037:翻開頁之後 4 個對頁
reg.spell_nonbattle("S-145", effect=Coin(
    count=1, on=HeadsAtLeast(1),
    then=ScheduleSpellFromNextSpreads(any_spell=True, spreads=4),
))

# 「この術を使う魔物の魔力が、相手のどの魔物の魔力より5000以上、上回っているとき使える」(對手沒有魔物時不能)、
# 「1ターンに1回だけ」;獲勝時對手選自己 1 隻魔物整疊放回魔書的空頁(對手選頁),搭檔進棄牌區,不造成傷害
reg.spell_rider("S-146", declare_condition=UserPowerExceedsOpponentsBy(gap=5000), once_per_turn=True, on_win=Sequence(steps=(
    AsOpponent(then=Choose(
        ReturnableOwnMamodo(), bind="slot", prompt="pick_own_mamodo",
        then=ReturnSlotToBook(),
    )),
    FinishAttackWithoutDamage(),
)), on_win_owns_damage=True)

reg.spell_rider("Ex-014", counter=True)
# Ex-015:攻擊獲勝時(防方獲勝時攻方的效果不解決)
reg.spell_rider("Ex-015", on_win=RestrictOpponent(flag=NO_EFFECTS_AND_SPELLS, duration=DUR_UNTIL_END_NEXT_TURN))
reg.spell_rider("Ex-016", counter=True)

# Ex-043:對手上一個回合宣告過「雷」屬性的戰術(被無效也算)時,宣告時確定加成
reg.spell_rider("Ex-043", on_declare=When(
    OpponentUsedAttrLastTurn("雷"),
    then=Sequence(steps=(AddSpellSelfBonus(amount=4000), IncreaseThisSpellDamage(amount=2))),
))

# Ex-044:對手的每隻魔物依場上順序各擲 1 枚(結果不受順序影響,不讓玩家選順序)
reg.spell_nonbattle("Ex-044", when=opponent_has_mamodo, effect=Coin(
    count=OpponentMamodoCount(), on=Always(),
    then=LockOpponentMamodoPerHeads(duration=DUR_UNTIL_END_NEXT_TURN),
))

reg.spell_rider("Ex-050", on_declare=Coin(
    count=5, on=Always(),
    then=Sequence(steps=(
        AddSpellPowerPerHeads(per_head=1000),
        IncreaseThisSpellDamagePerHeads(per_head=1),
    )),
))

# 「相手の1ダメージの攻撃を無効」「コストを2ふやすことで、相手の2ダメージの攻撃も無効」:宣告時選追加,
# 「効果の使用」的最後依攻擊的當下傷害判斷
reg.spell_rider("Ex-063", extra_cost=(2, 2, 0, 0), extra_cost_effect="negate_2_damage", on_effects_end=When(
    AttackDamageIs(values=(1,), with_extra=(1, 2)),
    then=NegateAttack(),
))

reg.spell_rider("Ex-064", on_effects_end=AdjustDefenseDamage(amount=-1))

reg.spell_rider("Ex-065", on_declare=When(
    SideIs("defense"),
    then=Coin(
        count=2, on=HeadsAtLeast(1),
        then=RememberInBattle(key="defense_coin_heads"),
    ),
), on_effects_end=When(
    BattleRemembered(key="defense_coin_heads"),
    then=NegateAttack(),
))

reg.spell_rider("Ex-068", on_declare=When(
    SideIs("defense"),
    then=AddDefenseSelfBonus(amount=2000),
))

# PR-006:下一場戰鬥的攻擊戰術可從任意頁使用;加成不論來自哪一頁,魔物效果攻擊沒有加成
reg.spell_nonbattle("PR-006", effect=Sequence(steps=(
    ScheduleAnyPageUse(any_spell=True, attack_only=True, next_battle=True),
    ScheduleAttackSpellBoost(power=3000, damage=1),
)))

# PR-009:限制與不受傷害分開管理(P-034 / E-036 只移除「術を使えない」)
reg.spell_nonbattle("PR-009", effect=Sequence(steps=(
    RestrictOwnNamedSpells(mamodo="ガッシュ・ベル", duration=DUR_UNTIL_END_OWN_NEXT_TURN),
    GuardBookAndNamedMamodo(mamodo="ガッシュ・ベル", duration=DUR_UNTIL_END_OWN_NEXT_TURN),
)))
