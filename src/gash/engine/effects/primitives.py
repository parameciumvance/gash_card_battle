"""效果原語:卡片 handler 用來組合效果的共用積木。

硬幣判定為互動式:擲出後若玩家場上有可用的 M-012(康裘美《幸運兒》),
會進入 pending 讓玩家決定是否重擲,確定後才呼叫 callback 繼續解決。
"""

from __future__ import annotations

from ..state import BOOK_SIZE, GAME_OVER, Modifier, PendingChoice, Standby
from . import registry as reg


# ---------------------------------------------------------------- modifier / standby

def add_modifier(game, batch, *, kind, source, owner, duration,
                 target_player=None, target_slot=None, amount=0, flag=None, data=None):
    m = Modifier(kind=kind, source=source, owner=owner, duration=duration,
                 created_turn=game.state.turn_no, target_player=target_player,
                 target_slot=target_slot, amount=amount, flag=flag, data=data or {})
    game.state.modifiers.append(m)
    game.emit(batch, "modifier_added", kind=kind, source=source,
              target_player=target_player, target_slot=target_slot,
              amount=amount, flag=flag, duration=duration)
    return m


def add_power(game, batch, *, source, owner, target_player, target_slot, amount, duration):
    return add_modifier(game, batch, kind="power", source=source, owner=owner,
                        duration=duration, target_player=target_player,
                        target_slot=target_slot, amount=amount)


def add_restriction(game, batch, *, source, owner, target_player, flag, duration):
    return add_modifier(game, batch, kind="restriction", source=source, owner=owner,
                        duration=duration, target_player=target_player, flag=flag)


def schedule_standby(game, batch, *, kind, source, owner, data=None):
    sb = Standby(kind=kind, source=source, owner=owner,
                 created_turn=game.state.turn_no, data=data or {})
    game.state.standby.append(sb)
    game.emit(batch, "standby_set", kind=kind, source=source, owner=owner)
    return sb


# ---------------------------------------------------------------- 翻頁 / MP / 回復

def turn_pages(game, batch, player, leaves, source):
    """效果造成的翻頁(1 張 = 1 對頁),不獲得 MP。翻完即敗。"""
    from ..engine import _game_over
    ps = game.state.players[player]
    ps.pos += 2 * leaves
    game.emit(batch, "pages_turned", player=player, count=leaves, pos=min(ps.pos, BOOK_SIZE + 2), source=source)
    if ps.book_exhausted():
        _game_over(game, batch, winner=1 - player, reason="book_out")


def turn_back_pages(game, batch, player, leaves, source):
    ps = game.state.players[player]
    ps.pos = max(2, ps.pos - 2 * leaves)
    game.emit(batch, "pages_turned", player=player, count=-leaves, pos=ps.pos, source=source)


def reduce_mp(game, batch, player, amount, source) -> int:
    """減少 MP(不低於 0),回傳實際減少量。"""
    ps = game.state.players[player]
    actual = min(amount, ps.mp)
    if actual:
        ps.mp -= actual
        game.emit(batch, "mp_changed", player=player, delta=-actual, mp=ps.mp, reason=source)
    return actual


def heal_slot(game, batch, player, slot, source):
    if slot.injured:
        slot.injured = False
        game.emit(batch, "mamodo_healed", player=player, slot=slot.uid, card=slot.top, source=source)


# ---------------------------------------------------------------- 選擇

def choose_or_auto(game, batch, *, kind, player, options, data=None, source=None):
    """單一選項自動解決;多選項進入 pending。options: [{'value': ..., ...}]"""
    data = data or {}
    if len(options) == 1:
        reg.CHOICE_RESOLVERS[kind](game, batch, options[0]["value"], data)
        return
    game.state.pending = PendingChoice(kind=kind, player=player, options=options,
                                       source=source, data=data)
    game.emit(batch, "choice_required", kind=kind, player=player, options=options)


# ---------------------------------------------------------------- 互動式硬幣

def _reflip_available(game, player) -> bool:
    ps = game.state.players[player]
    return (any(s.top == "M-012" for s in ps.slots)
            and "mamodo:M-012" not in ps.used_abilities)


def flip_coins(game, batch, player, count, source, callback, data=None):
    """擲 count 次硬幣;結果確定後呼叫 CHOICE_RESOLVERS[callback](game, batch, results, data)。
    玩家有可用的 M-012 時,先進入重擲確認 pending。"""
    results = []
    for _ in range(count):
        heads = game.rng.random() < 0.5
        results.append(heads)
        game.emit(batch, "coin_flipped", player=player,
                  result="heads" if heads else "tails", source=source)
    data = dict(data or {})
    data.update({"results": results, "callback": callback, "player": player, "source": source})
    if _reflip_available(game, player):
        game.state.pending = PendingChoice(
            kind="coin_confirm", player=player, source=source,
            options=[{"value": None, "label": "keep"}]
            + [{"value": i, "label": "reflip"} for i in range(count)],
            data=data)
        game.emit(batch, "choice_required", kind="coin_confirm", player=player,
                  results=["heads" if r else "tails" for r in results])
        return
    reg.CHOICE_RESOLVERS[callback](game, batch, results, data)


@reg.choice_resolver("coin_confirm")
def _coin_confirm(game, batch, value, data):
    from ..engine import IllegalCommand
    player = data["player"]
    results = data["results"]
    if value is None:
        game.state.pending = None
        reg.CHOICE_RESOLVERS[data["callback"]](game, batch, results, data)
        return
    if not isinstance(value, int) or not 0 <= value < len(results):
        raise IllegalCommand("choose.invalid", "無效的重擲選擇")
    if not _reflip_available(game, player):
        raise IllegalCommand("choose.invalid", "M-012 的效果已不可使用")
    ps = game.state.players[player]
    ps.used_abilities.add("mamodo:M-012")
    game.emit(batch, "ability_used", player=player, card="M-012",
              slot=next(s.uid for s in ps.slots if s.top == "M-012"), zone="mamodo")
    heads = game.rng.random() < 0.5
    results[value] = heads
    game.emit(batch, "coin_flipped", player=player,
              result="heads" if heads else "tails", source=data["source"], reflip=True)
    game.state.pending = None
    if _reflip_available(game, player):
        game.state.pending = PendingChoice(
            kind="coin_confirm", player=player, source=data["source"],
            options=[{"value": None, "label": "keep"}]
            + [{"value": i, "label": "reflip"} for i in range(len(results))],
            data=data)
        game.emit(batch, "choice_required", kind="coin_confirm", player=player,
                  results=["heads" if r else "tails" for r in results])
        return
    reg.CHOICE_RESOLVERS[data["callback"]](game, batch, results, data)
