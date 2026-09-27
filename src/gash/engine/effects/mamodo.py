"""尚未遷移到效果樹的魔物卡(依日版 j 文意)。已遷移的魔物卡見 tree_cards.py。

進度見 openspec/changes/effect-tree-migration/tasks.md 第 4 組。
"""

from __future__ import annotations

from ..state import DUR_BATTLE
from . import registry as reg


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
