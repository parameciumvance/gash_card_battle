"""魔物卡效果(M-001~M-015)。香草加成以外的效果依日版 j 文意實作。"""

from __future__ import annotations

from ..cards import MAMODO
from ..state import DUR_BATTLE, DUR_TURN, NO_SPELLS
from . import registry as reg
from .primitives import (
    add_modifier, add_power, add_restriction, choose_or_auto, schedule_standby, turn_pages,
)

# 疊放魔物(變身後)
reg.STACK_ON["M-007"] = {"M-006"}
reg.STACK_ON["M-010"] = {"M-009"}


def _in_battle_as(game, player, slot, side) -> bool:
    b = game.state.battle
    if b is None:
        return False
    if side == "attack":
        return b.attacker == player and b.attack_slot == slot.uid
    return b.defender == player and b.defense_slot == slot.uid


# M-001 ガッシュ《やさしい王様》:[1MP][持續] 攻擊的戰鬥中此魔物 +1000
@reg.activated("M-001", mode="mp", mp_cost=1, timing="battle",
               condition=lambda g, p, s: _in_battle_as(g, p, s, "attack"))
def m001(game, batch, player, slot):
    add_power(game, batch, source="M-001", owner=player, target_player=player,
              target_slot=slot.uid, amount=1000, duration=DUR_BATTLE)


# M-002 ガッシュ《おちこぼれ》:[此卡在場上] 自己開始階段 MP≤2 時 MP+1
@reg.start_phase("M-002")
def m002(game, batch, player, slot):
    if game.state.players[player].mp <= 2:
        from ..engine import gain_mp
        gain_mp(game, batch, player, 1, "M-002")


# M-003 ガッシュ《負傷的英雄》:負傷時 +1000
@reg.static_power("M-003")
def m003(game, player, slot):
    return 1000 if slot.top == "M-003" and slot.injured else 0


# M-004 レイコム:裝有夥伴時 +1000
@reg.static_power("M-004")
def m004(game, player, slot):
    return 1000 if slot.top == "M-004" and slot.partner else 0


# M-005 ブラゴ:[2MP][持續] 攻擊的戰鬥中此魔物攻擊傷害 +1
@reg.activated("M-005", mode="mp", mp_cost=2, timing="battle",
               condition=lambda g, p, s: _in_battle_as(g, p, s, "attack"))
def m005(game, batch, player, slot):
    add_modifier(game, batch, kind="damage_delta", source="M-005", owner=player,
                 duration=DUR_BATTLE, target_player=player, target_slot=slot.uid, amount=1)


# M-006 ゴフレ:登場回合對手不能使用術卡
@reg.on_play("M-006")
def m006(game, batch, player, slot):
    add_restriction(game, batch, source="M-006", owner=player,
                    target_player=1 - player, flag=NO_SPELLS, duration=DUR_TURN)


# M-007 ゴフレ(變身後):登場時翻對手魔本 1 張
@reg.on_play("M-007")
def m007(game, batch, player, slot):
    turn_pages(game, batch, 1 - player, 1, "M-007")


# M-008 スギナ:[宣告使用][待命] 此魔物下一張術費 -1 且魔力 -1000
@reg.activated("M-008", mode="declare", timing="nonbattle")
def m008(game, batch, player, slot):
    schedule_standby(game, batch, kind="spell_bonus", source="M-008", owner=player,
                     data={"mamodo": "Sugino", "power_delta": -1000, "cost_delta": -1})


# M-009 コルル:被棄掉時 MP+4
@reg.on_discard("M-009")
def m009(game, batch, player, slot):
    from ..engine import gain_mp
    gain_mp(game, batch, player, 4, "M-009")


# M-010 コルル(變身後):[1MP][持續] 防禦的戰鬥中此魔物 +1000
@reg.activated("M-010", mode="mp", mp_cost=1, timing="battle",
               condition=lambda g, p, s: _in_battle_as(g, p, s, "defense"))
def m010(game, batch, player, slot):
    add_power(game, batch, source="M-010", owner=player, target_player=player,
              target_slot=slot.uid, amount=1000, duration=DUR_BATTLE)


# M-011 フェイン:[宣告使用] 檢視對手魔本,棄掉 1 張魔物卡(一場遊戲限一次)
def _m011_condition(game, player, slot):
    opp = game.state.players[1 - player]
    return any(
        game.db[opp.card_at(p)].type == MAMODO
        for p in range(1, 33) if p not in opp.consumed_pages
    )


@reg.activated("M-011", mode="declare", timing="nonbattle", per_game=True,
               condition=_m011_condition)
def m011(game, batch, player, slot):
    opp = game.state.players[1 - player]
    pages = [p for p in range(1, 33)
             if p not in opp.consumed_pages and game.db[opp.card_at(p)].type == MAMODO]
    game.emit(batch, "book_revealed", player=1 - player, viewer=player,
              cards=[{"page": p, "card": opp.card_at(p)}
                     for p in range(1, 33) if p not in opp.consumed_pages])
    choose_or_auto(game, batch, kind="m011_pick", player=player,
                   options=[{"value": p, "card": opp.card_at(p)} for p in pages],
                   data={"player": player}, source="M-011")


@reg.choice_resolver("m011_pick")
def m011_pick(game, batch, value, data):
    from ..engine import IllegalCommand
    player = data["player"]
    opp = game.state.players[1 - player]
    if (not isinstance(value, int) or not 1 <= value <= 32
            or value in opp.consumed_pages
            or game.db[opp.card_at(value)].type != MAMODO):
        raise IllegalCommand("choose.invalid", "須選擇對手魔本中的魔物卡")
    number = opp.card_at(value)
    opp.consumed_pages.add(value)
    opp.discard.append(number)
    game.emit(batch, "card_discarded", player=1 - player, card=number,
              zone="book", page=value, reason="M-011")


# M-012 キャンチョメ《幸運兒》:重擲硬幣 — 實作於 primitives.flip_coins(互動式)


# M-013 キャンチョメ《無敵的傢伙》:[2MP][持續] 該場戰鬥不受傷害(僅負傷時可用)
@reg.activated("M-013", mode="mp", mp_cost=2, timing="battle",
               condition=lambda g, p, s: s.injured)
def m013(game, batch, player, slot):
    add_modifier(game, batch, kind="no_damage", source="M-013", owner=player,
                 duration=DUR_BATTLE, target_player=player, target_slot=slot.uid)


# M-014 ティオ《可靠的夥伴》:自己場上 ≥2 隻魔物時全體 +1000
@reg.static_power("M-014")
def m014(game, player, slot):
    return 1000 if len(game.state.players[player].slots) >= 2 else 0


# M-015 ティオ《倔強》:[5MP][持續] 該場戰鬥不受傷害
@reg.activated("M-015", mode="mp", mp_cost=5, timing="battle")
def m015(game, batch, player, slot):
    add_modifier(game, batch, kind="no_damage", source="M-015", owner=player,
                 duration=DUR_BATTLE, target_player=player, target_slot=slot.uid)
