"""NPC 對手的決策。

`decide` 回傳排序好的候選指令(已帶 player);`submit_ranked` 依序送出,全部被拒時再送安全預設。
NPC 只透過 `determinize` 取得盤面副本,因此決策只取決於 NPC 看得到的資訊與 NPC 自己的隨機來源。
"""

from __future__ import annotations

import random

from ..engine.awaiting import default_command
from ..engine.engine import IllegalCommand, submit
from ..engine.state import Game
from .candidates import candidates
from .determinize import Determinizer
from .evaluate import evaluate
from .settle import settle, try_submit

LEVELS = ("dummy", "normal")
SAMPLES = 16      # 每個決策點的抽樣次數(所有候選共用同一組抽樣)


def decide(game: Game, player: int, level: str, rng: random.Random) -> list[dict]:
    """player 目前的候選指令,依偏好排序(最後一個為安全預設);對局已結束時為空。"""
    default = default_command(game)
    if default is None:
        return []
    fallback = {**default, "player": player}
    if level == "dummy":
        return [fallback]
    cands = candidates(game, player)
    if len(cands) <= 1:
        return [{**c, "player": player} for c in cands] + [fallback]
    det = Determinizer(game, player)
    samples = [det.sample(rng) for _ in range(SAMPLES)]
    scored = []
    for index, cmd in enumerate(cands):
        total, legal = 0.0, 0
        for sample in samples:
            sim = det.build(sample)
            if not try_submit(sim, player, cmd):
                continue
            settle(sim, player)
            total += evaluate(sim, player)
            legal += 1
        if legal:
            scored.append((-total / legal, index, cmd))
    scored.sort(key=lambda t: (t[0], t[1]))
    ranked = [{**cmd, "player": player} for _, _, cmd in scored]
    if fallback not in ranked:
        ranked.append(fallback)
    return ranked


def submit_ranked(game: Game, player: int, ranked: list[dict]) -> tuple[dict, list[dict]] | None:
    """依序送出候選,回傳第一個被引擎接受的指令與其事件;連安全預設都被拒時回傳 None。"""
    fallback = default_command(game)
    tried = ranked + ([{**fallback, "player": player}] if fallback is not None else [])
    for cmd in tried:
        try:
            return cmd, submit(game, cmd)
        except IllegalCommand:
            continue
    return None
