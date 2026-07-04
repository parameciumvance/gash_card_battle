"""術卡附加效果(非香草)。香草術卡(攻/防獲勝→魔本傷害)由卡片資料直接驅動。

宣告時效果(硬幣)依規則於宣告時擲出並確定。
"""

from __future__ import annotations

from ..state import DUR_UNTIL_END_NEXT_TURN, NO_PARTNER_EFFECTS, NO_SPELLS
from . import registry as reg
from .primitives import add_restriction, flip_coins, schedule_standby


# ---- S-003 ラシルド:【反擊】防禦方獲勝時對對手魔本造成傷害
reg.spell_rider("S-003", counter=True)


# ---- 傷害後禁術(擲硬幣):S-004 ジケルド / S-014 ジュロン
def _coin_lock_spells(number):
    def on_damage(game, batch, player):
        flip_coins(game, batch, player, 1, number, "lock_spells_coin",
                   {"player": player, "source": number})
    return on_damage


@reg.choice_resolver("lock_spells_coin")
def lock_spells_coin(game, batch, results, data):
    if results[0]:
        add_restriction(game, batch, source=data["source"], owner=data["player"],
                        target_player=1 - data["player"], flag=NO_SPELLS,
                        duration=DUR_UNTIL_END_NEXT_TURN)


reg.spell_rider("S-004", on_damage=_coin_lock_spells("S-004"))
reg.spell_rider("S-014", on_damage=_coin_lock_spells("S-014"))


# ---- 傷害後禁術(必定):S-009 グラビレイ / S-011 アイアン・グラビレイ
def _lock_spells(number):
    def on_damage(game, batch, player):
        add_restriction(game, batch, source=number, owner=player,
                        target_player=1 - player, flag=NO_SPELLS,
                        duration=DUR_UNTIL_END_NEXT_TURN)
    return on_damage


reg.spell_rider("S-009", on_damage=_lock_spells("S-009"))
reg.spell_rider("S-011", on_damage=_lock_spells("S-011"))


# ---- S-007 フリズド:傷害後,對手夥伴效果失效(至其下回合結束階段)
def _s007_on_damage(game, batch, player):
    add_restriction(game, batch, source="S-007", owner=player,
                    target_player=1 - player, flag=NO_PARTNER_EFFECTS,
                    duration=DUR_UNTIL_END_NEXT_TURN)


reg.spell_rider("S-007", on_damage=_s007_on_damage)


# ---- S-016 / S-017 ゼルク / ゼルセン:以此術防禦時魔力加值
def _defense_self_bonus(amount):
    def on_declare(game, batch, player, side):
        if side == "defense":
            b = game.state.battle
            b.data["defense_self_bonus"] = b.data.get("defense_self_bonus", 0) + amount
            game.emit(batch, "effect_applied", source="defense_bonus", amount=amount)
    return on_declare


reg.spell_rider("S-016", on_declare=_defense_self_bonus(1000))
reg.spell_rider("S-017", on_declare=_defense_self_bonus(2000))


# ---- S-019 ウルク:攻擊獲勝時,[待命] 本回合下一次攻擊不可被防禦(無魔本傷害)
def _s019_on_win(game, batch, player):
    schedule_standby(game, batch, kind="attack_undefendable", source="S-019", owner=player)


reg.spell_rider("S-019", on_win=_s019_on_win, no_book_damage=True)


# ---- S-020 ポルク:攻擊獲勝時對手 MP-3(無魔本傷害)
def _s020_on_win(game, batch, player):
    from .primitives import reduce_mp
    reduce_mp(game, batch, 1 - player, 3, "S-020")


reg.spell_rider("S-020", on_win=_s020_on_win, no_book_damage=True)


# ---- 硬幣無效攻擊:S-021 コポルク(2枚,至少1正)/ S-025 逃げるぞ!(1枚)
def _coin_negate(number, count, need_heads=1):
    def on_declare(game, batch, player, side):
        if side != "defense":
            return
        flip_coins(game, batch, player, count, number, "coin_negate_resolve",
                   {"player": player, "source": number, "need": need_heads})
    return on_declare


@reg.choice_resolver("coin_negate_resolve")
def coin_negate_resolve(game, batch, results, data):
    b = game.state.battle
    if b is None:
        return
    if sum(results) >= data["need"]:
        b.attack_negated = True
        game.emit(batch, "attack_negated", source=data["source"], player=data["player"])


reg.spell_rider("S-021", on_declare=_coin_negate("S-021", 2))
reg.spell_rider("S-025", on_declare=_coin_negate("S-025", 1))


# ---- S-026 ＳＥＴ!:擲硬幣,正面→[待命] 本回合下一場戰鬥對手不能防禦
def _s026_on_declare(game, batch, player, side):
    if side != "attack":
        return
    flip_coins(game, batch, player, 1, "S-026", "s026_resolve", {"player": player})


@reg.choice_resolver("s026_resolve")
def s026_resolve(game, batch, results, data):
    if results[0]:
        schedule_standby(game, batch, kind="attack_undefendable", source="S-026",
                         owner=data["player"])


reg.spell_rider("S-026", on_declare=_s026_on_declare, no_book_damage=True)


# ---- S-027 耐えてくれよ!:擲2硬幣,至少1正→對手攻擊傷害 -1
def _s027_on_declare(game, batch, player, side):
    if side != "defense":
        return
    flip_coins(game, batch, player, 2, "S-027", "s027_resolve", {"player": player})


@reg.choice_resolver("s027_resolve")
def s027_resolve(game, batch, results, data):
    b = game.state.battle
    if b is None:
        return
    if sum(results) >= 1:
        b.data["defense_damage_delta"] = b.data.get("defense_damage_delta", 0) - 1
        game.emit(batch, "effect_applied", source="S-027", amount=-1)


reg.spell_rider("S-027", on_declare=_s027_on_declare)

# ---- S-022 セウシル / S-024 マ・セシルド / S-028 伏せろ!:
#      防禦獲勝時將攻擊無效 = 防方獲勝本就使攻方效果不解決,無需額外處理(純資料驅動)
