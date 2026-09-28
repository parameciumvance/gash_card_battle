"""模擬到停點:NPC 送出候選後,雙方以簡單的回應規則續行,直到可以評估的時點。

停點:對局結束、回合交替、又輪到 NPC 做非戰鬥的決定,或達到步數上限。
對手的回應規則刻意簡單(迎戰、擋得下就以最低費用防禦、魔本受傷時保護、戰鬥中 pass、其他走安全預設);
NPC 在模擬中遇到的中途決策,以各選項立即的評估挑選(不再往下模擬)。
"""

from __future__ import annotations

import copy
import random

from ..engine.awaiting import awaited_player, default_command
from ..engine.engine import IllegalCommand, _side_total, slot_power, submit
from ..engine.state import BATTLE, BOOK_SIZE, GAME_OVER, STEP_DEFENSE, Game
from .candidates import candidates, choice_value
from .evaluate import evaluate

MAX_STEPS = 60


def clone(game: Game) -> Game:
    rng = random.Random()
    rng.setstate(game.rng.getstate())
    return Game(state=copy.deepcopy(game.state), rng=rng, db=game.db,
                jammer=copy.deepcopy(game.jammer))


def try_submit(game: Game, player: int, command: dict) -> bool:
    try:
        submit(game, {**command, "player": player})
    except IllegalCommand:
        return False
    return True


def npc_free(game: Game, npc: int) -> bool:
    """NPC 在非戰鬥中握有行動權、且沒有待決事項:NPC 的下一個真正的決定。"""
    st = game.state
    return (st.phase == BATTLE and st.pending is None and st.battle is None
            and st.battle_in is None and st.action_player == npc)


def settle(game: Game, npc: int, max_steps: int = MAX_STEPS) -> None:
    start_turn = game.state.turn_no
    for _ in range(max_steps):
        st = game.state
        if st.phase == GAME_OVER or st.turn_no != start_turn:
            return
        who = awaited_player(game)
        if who is None or (who == npc and npc_free(game, npc)):
            return
        if not try_submit(game, who, respond(game, who, npc)):
            if not try_submit(game, who, default_command(game)):
                return


def respond(game: Game, who: int, npc: int) -> dict:
    st = game.state
    if st.pending is not None:
        if st.pending.kind == "protect":
            return _protect(game, who)
        if who == npc:
            return _greedy_choice(game, who)
        return default_command(game)
    if st.battle is not None:
        if st.battle.step == STEP_DEFENSE:
            return _defend(game, who)
        return {"type": "pass"}
    return default_command(game)


def _protect(game: Game, who: int) -> dict:
    """魔本受傷:有健康魔物就以魔力最低者保護;會致命時負傷魔物也用。魔物受傷不保護。"""
    st = game.state
    item = st.pending.data["ctx"]["items"][0]
    if item["kind"] != "book":
        return {"type": "choose", "value": None}
    slots = [st.slot_by_uid(who, o["value"]) for o in st.pending.options if o.get("value") is not None]
    slots = [s for s in slots if s is not None]
    lethal = st.players[who].pos + 2 * item["amount"] > BOOK_SIZE
    usable = [s for s in slots if not s.injured] or (slots if lethal else [])
    if not usable:
        return {"type": "choose", "value": None}
    best = min(usable, key=lambda s: slot_power(game, who, s))
    return {"type": "choose", "value": best.uid}


def _defend(game: Game, who: int) -> dict:
    """在合法的防禦中,選擋得下攻擊(防方合計 ≥ 攻方合計)且費用最低者;沒有就不防禦。"""
    st = game.state
    if st.battle.attack_undefendable:
        return {"type": "no_defense"}
    attack = _side_total(game, st.battle, "attack")
    mp = st.players[who].mp
    best, best_cost = {"type": "no_defense"}, None
    for cmd in candidates(game, who):
        if cmd["type"] != "declare_defense":
            continue
        sim = clone(game)
        if not try_submit(sim, who, cmd):
            continue
        if sim.state.pending is not None:      # 宣告時的詢問(如 M-008 減費):走安全預設
            try_submit(sim, who, default_command(sim))
        battle = sim.state.battle
        if battle is None or _side_total(sim, battle, "defense") < attack:
            continue
        cost = mp - sim.state.players[who].mp
        if best_cost is None or cost < best_cost:
            best, best_cost = cmd, cost
    return best


def _greedy_choice(game: Game, who: int) -> dict:
    """NPC 在模擬中的中途決策:各選項送出後立即評估,取最高者。"""
    options = game.state.pending.options
    best, best_score = None, None
    for i in range(len(options)):
        cmd = {"type": "choose", "value": choice_value(options, i)}
        sim = clone(game)
        if not try_submit(sim, who, cmd):
            continue
        score = evaluate(sim, who)
        if best_score is None or score > best_score:
            best, best_score = cmd, score
    return best or default_command(game)
