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
