"""夥伴卡效果(P-001~P-009)。全部為【將此卡棄掉→】一次性效果,依日版 j 文意。"""

from __future__ import annotations

from ..state import DUR_BATTLE
from . import registry as reg
from .primitives import add_modifier, choose_or_auto, schedule_standby


# P-001 高嶺清麿:[待命] 本回合賈修下一場戰鬥攻擊所用的術不可被防禦
@reg.activated("P-001", mode="discard", timing="nonbattle")
def p001(game, batch, player, slot):
    schedule_standby(game, batch, kind="attack_undefendable", source="P-001",
                     owner=player, data={"mamodo": "Zatch Bell"})


# P-002 細川:對手 MP-3,自己獲得實際減少量
@reg.activated("P-002", mode="discard", timing="nonbattle")
def p002(game, batch, player, slot):
    from ..engine import gain_mp
    from .primitives import reduce_mp
    actual = reduce_mp(game, batch, 1 - player, 3, "P-002")
    gain_mp(game, batch, player, actual, "P-002")


def _battle_attack_by(game, player, mamodo_name) -> bool:
    b = game.state.battle
    if b is None or b.attacker != player:
        return False
    slot = game.state.slot_by_uid(player, b.attack_slot)
    return slot is not None and game.db[slot.top].related_mamodo == mamodo_name


def _no_dup(game, source) -> bool:
    return not any(m.kind in ("damage_delta", "damage_double") and m.source == source
                   and m.duration == DUR_BATTLE for m in game.state.modifiers)


# P-003 シェリー:該場戰鬥布拉哥攻擊傷害 +2(不可重複)
@reg.activated("P-003", mode="discard", timing="battle",
               condition=lambda g, p, s: _battle_attack_by(g, p, "Brago") and _no_dup(g, "P-003"))
def p003(game, batch, player, slot):
    b = game.state.battle
    add_modifier(game, batch, kind="damage_delta", source="P-003", owner=player,
                 duration=DUR_BATTLE, target_player=player, target_slot=b.attack_slot, amount=2)


# P-004 連次:該場戰鬥勾夫雷造成的傷害加倍(不可重複)
@reg.activated("P-004", mode="discard", timing="battle",
               condition=lambda g, p, s: _battle_attack_by(g, p, "Gofure") and _no_dup(g, "P-004"))
def p004(game, batch, player, slot):
    b = game.state.battle
    add_modifier(game, batch, kind="damage_double", source="P-004", owner=player,
                 duration=DUR_BATTLE, target_player=player, target_slot=b.attack_slot)


# P-005 春彥:本回合須基納的術費用視為 0
@reg.activated("P-005", mode="discard", timing="nonbattle")
def p005(game, batch, player, slot):
    from ..state import DUR_TURN
    add_modifier(game, batch, kind="spell_cost_zero", source="P-005", owner=player,
                 duration=DUR_TURN, target_player=player, data={"mamodo": "Sugino"})


# P-006 しおり:[待命] 戰鬥中無效對可露露(變身後)的 1 次傷害,然後棄掉變身後
@reg.activated("P-006", mode="discard", timing="any",
               condition=lambda g, p, s: s.top == "M-010")
def p006(game, batch, player, slot):
    schedule_standby(game, batch, kind="negate_damage", source="P-006", owner=player,
                     data={"slot_uid": slot.uid, "after": "p006_after", "player": player})


@reg.choice_resolver("p006_after")
def p006_after(game, batch, value, data):
    player = data["player"]
    slot = game.state.slot_by_uid(player, data["slot_uid"])
    if slot is None or slot.top != "M-010":
        return
    slot.stack.pop()
    game.state.players[player].discard.append("M-010")
    game.emit(batch, "card_discarded", player=player, card="M-010", zone="mamodo",
              reason="P-006")


# P-007 清兵衛:[待命] 本回合下一場戰鬥的菲恩術卡 +4000
@reg.activated("P-007", mode="discard", timing="nonbattle")
def p007(game, batch, player, slot):
    schedule_standby(game, batch, kind="spell_bonus", source="P-007", owner=player,
                     data={"mamodo": "Fein", "power_delta": 4000})


# P-008 パルコ・フォルゴレ:棄掉對手場上 1 張夥伴卡
@reg.activated("P-008", mode="discard", timing="nonbattle",
               condition=lambda g, p, s: any(x.partner for x in g.state.players[1 - p].slots))
def p008(game, batch, player, slot):
    opp = game.state.players[1 - player]
    options = [{"value": x.uid, "card": x.partner} for x in opp.slots if x.partner]
    choose_or_auto(game, batch, kind="p008_pick", player=player, options=options,
                   data={"player": player}, source="P-008")


@reg.choice_resolver("p008_pick")
def p008_pick(game, batch, value, data):
    from ..engine import IllegalCommand
    player = data["player"]
    opp_slot = game.state.slot_by_uid(1 - player, value if isinstance(value, int) else -1)
    if opp_slot is None or not opp_slot.partner:
        raise IllegalCommand("choose.invalid", "須選擇對手場上的夥伴卡")
    number = opp_slot.partner
    opp_slot.partner = None
    game.state.players[1 - player].discard.append(number)
    game.emit(batch, "card_discarded", player=1 - player, card=number,
              zone="partner", reason="P-008")


# P-009 大海惠:將對手剛使用的術無效(防方→無效攻擊;攻方→無效防禦)
def _p009_condition(game, player, slot):
    b = game.state.battle
    if b is None:
        return False
    if b.defender == player:
        return not b.attack_negated
    return b.defense_spell is not None and not b.defense_negated


@reg.activated("P-009", mode="discard", timing="battle", condition=_p009_condition)
def p009(game, batch, player, slot):
    b = game.state.battle
    if b.defender == player:
        b.attack_negated = True
        game.emit(batch, "attack_negated", source="P-009", player=player)
    else:
        b.defense_negated = True
        game.emit(batch, "defense_negated", source="P-009", player=player)


# ======================================================================
# Level 2 夥伴(P-010~P-019)
# ======================================================================

from ..state import (  # noqa: E402
    DUR_TURN, DUR_UNTIL_END_NEXT_TURN, NO_ATTACK_SPELL,
)
from .primitives import (  # noqa: E402
    add_restriction, own_page_turn_effect, own_page_turnback_effect, turn_pages,
)


# P-010 高嶺清麿:[棄掉] 翻自己書 1 頁(翻自己書頁效果每回合一次)
@reg.activated("P-010", mode="discard", timing="nonbattle",
               condition=lambda g, p, s: not g.state.players[p].page_effect_used
               and g.state.players[p].pos + 2 <= 32)
def p010(game, batch, player, slot):
    own_page_turn_effect(game, batch, player, 1, "P-010")


# P-011 エイド:[棄掉][持續] 本回合對手 1 隻魔物魔力視為 0
@reg.activated("P-011", mode="discard", timing="nonbattle",
               condition=lambda g, p, s: bool(g.state.players[1 - p].slots))
def p011(game, batch, player, slot):
    opp = game.state.players[1 - player]
    options = [{"value": s.uid, "card": s.top} for s in opp.slots]
    choose_or_auto(game, batch, kind="p011_pick", player=player, options=options,
                   data={"player": player}, source="P-011")


@reg.choice_resolver("p011_pick")
def p011_pick(game, batch, value, data):
    from ..engine import IllegalCommand
    player = data["player"]
    slot = game.state.slot_by_uid(1 - player, value if isinstance(value, int) else -1)
    if slot is None:
        raise IllegalCommand("choose.invalid", "須選擇對手場上的魔物")
    add_modifier(game, batch, kind="power_zero", source="P-011", owner=player,
                 duration=DUR_TURN, target_player=1 - player, target_slot=slot.uid)


# P-012 シェリー:[棄掉][持續] 本回合對布拉哥攻擊傷害庇護/犧牲的魔物一律入墓
@reg.activated("P-012", mode="discard", timing="nonbattle")
def p012(game, batch, player, slot):
    add_modifier(game, batch, kind="protect_discard", source="P-012", owner=player,
                 duration=DUR_TURN, target_player=player, data={"mamodo": "Brago"})


# P-013 ココ:[此卡在場上] 對手魔物入墓→翻對手書 1 頁(觸發器)
@reg.trigger("P-013", "mamodo_discarded")
def p013(game, batch, owner, slot, ev):
    if ev.get("player") == 1 - owner:  # 對手的魔物入墓
        turn_pages(game, batch, 1 - owner, 1, "P-013")


# P-014 ペリコ:[棄掉][持續] 本回合對手不能使用術卡攻擊
@reg.activated("P-014", mode="discard", timing="nonbattle")
def p014(game, batch, player, slot):
    add_restriction(game, batch, source="P-014", owner=player,
                    target_player=1 - player, flag=NO_ATTACK_SPELL, duration=DUR_TURN)


# P-015 ルク:[棄掉][待命] 本回合一次,可自書任意頁使用 1 張比萊茲術
@reg.activated("P-015", mode="discard", timing="nonbattle")
def p015(game, batch, player, slot):
    schedule_standby(game, batch, kind="spell_any_page", source="P-015", owner=player,
                     data={"spell_name": "Biraitsu"})


# P-016 レンブラント:[棄掉] 將對手該場戰鬥攻擊所用的術無效
@reg.activated("P-016", mode="discard", timing="battle",
               condition=lambda g, p, s: (g.state.battle is not None
                                          and g.state.battle.defender == p
                                          and g.state.battle.attack_spell is not None
                                          and not g.state.battle.attack_negated))
def p016(game, batch, player, slot):
    b = game.state.battle
    b.attack_negated = True
    game.emit(batch, "attack_negated", source="P-016", player=player)


# P-017 ステング:[棄掉] 將對手該場戰鬥防禦所用的術無效
@reg.activated("P-017", mode="discard", timing="battle",
               condition=lambda g, p, s: (g.state.battle is not None
                                          and g.state.battle.attacker == p
                                          and g.state.battle.defense_spell is not None
                                          and not g.state.battle.defense_negated))
def p017(game, batch, player, slot):
    b = game.state.battle
    b.defense_negated = True
    game.emit(batch, "defense_negated", source="P-017", player=player)


# P-018 ジェム:[棄掉] 回翻自己書 1 頁(回翻自己書頁效果每回合一次)
@reg.activated("P-018", mode="discard", timing="nonbattle",
               condition=lambda g, p, s: not g.state.players[p].page_back_effect_used
               and g.state.players[p].pos > 2)
def p018(game, batch, player, slot):
    own_page_turnback_effect(game, batch, player, 1, "P-018")


# P-019 英国紳士:[此卡在場上] 對手回翻自己書頁時對手 MP-2(觸發器)
@reg.trigger("P-019", "pages_turned")
def p019(game, batch, owner, slot, ev):
    opp = 1 - owner
    # 對手回翻自己的書(count<0 且 player==對手)
    if ev.get("player") == opp and ev.get("count", 0) < 0:
        from .primitives import reduce_mp
        reduce_mp(game, batch, opp, 2, "P-019")
