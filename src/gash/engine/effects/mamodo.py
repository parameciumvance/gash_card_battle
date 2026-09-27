"""尚未遷移到效果樹的魔物卡(依日版 j 文意)。已遷移的魔物卡見 tree_cards.py。

進度見 openspec/changes/effect-tree-migration/tasks.md 第 4 組。
"""

from __future__ import annotations

from ..state import DUR_BATTLE
from . import registry as reg
from .primitives import choose_or_auto


# M-025 ロブノス(完全体):登場時從墓把 Robnos 卡放回書空頁 + MP+2
@reg.on_play("M-025")
def m025(game, batch, player, slot):
    from ..engine import gain_mp
    ps = game.state.players[player]
    empties = sorted(ps.consumed_pages)
    targets = [i for i, n in enumerate(ps.discard) if n in ("M-024", "M-025")]
    if empties and targets:
        options = [{"value": i, "card": ps.discard[i]} for i in targets]
        choose_or_auto(game, batch, kind="m025_pick", player=player, options=options,
                       data={"player": player}, source="M-025")
    gain_mp(game, batch, player, 2, "M-025")


@reg.choice_resolver("m025_pick")
def m025_pick(game, batch, value, data):
    from ..engine import IllegalCommand
    from .primitives import return_to_book
    player = data["player"]
    ps = game.state.players[player]
    if not isinstance(value, int) or not 0 <= value < len(ps.discard):
        raise IllegalCommand("choose.invalid", "須選擇棄牌區的羅布諾斯卡")
    number = ps.discard[value]
    if number not in ("M-024", "M-025"):
        raise IllegalCommand("choose.invalid", "只能選羅布諾斯卡")
    empties = sorted(ps.consumed_pages)
    if not empties:
        game.state.pending = None
        return
    ps.discard.pop(value)
    return_to_book(game, batch, player, number, empties[0])
    game.state.pending = None


# M-026 マルス:[2MP] 將對手剛套用的 1 個魔物效果無效
@reg.activated("M-026", mode="mp", mp_cost=2, timing="any",
               condition=lambda g, p, s: g.state.battle is not None)
def m026(game, batch, player, slot):
    # 簡化:清除對手本場戰鬥剛加上的 power/damage 類 modifier(最近一筆)
    opp = 1 - player
    for m in reversed(game.state.modifiers):
        if m.owner == opp and m.kind in ("power", "damage_delta", "damage_double") \
                and m.duration == DUR_BATTLE:
            game.state.modifiers.remove(m)
            game.emit(batch, "effect_applied", source="M-026", negated=m.source)
            return
