"""模擬到停點:NPC 送出候選後,雙方以簡單的回應規則續行,直到可以評估的時點。

停點:對局結束、回合交替、又輪到 NPC 做非戰鬥的決定,或達到步數上限。
`turn_end_value` 在停於「又輪到 NPC」時再延伸一層(pass / 攻擊)到回合結束,讓所有候選以同一基準評分。
對手的回應規則刻意簡單(迎戰、擋得下就以最低費用防禦、魔書受傷時保護、戰鬥中 pass、其他走安全預設);
NPC 在模擬中遇到的中途決策,以各選項立即的評估挑選(不再往下模擬)。
"""

from __future__ import annotations

import copy
import random

from ..engine.awaiting import awaited_player, default_command
from ..engine.engine import IllegalCommand, _side_total, attack_undefendable, slot_power, submit
from ..engine.state import BATTLE, BOOK_SIZE, GAME_OVER, STEP_DEFENSE, Game
from .candidates import candidates, choice_value
from .evaluate import evaluate

MAX_STEPS = 60
# 延伸一層才達到的結果略低於直接達到的:同樣的結果時,偏好早一步達成(例如能致勝就直接攻擊,不先放卡)
EXTENSION_DISCOUNT = 0.01


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


def settle(game: Game, npc: int, max_steps: int = MAX_STEPS, start_turn: int | None = None) -> None:
    """模擬到停點。start_turn:以哪個回合的交替為停點(預設目前的回合;候選已讓回合交替時要傳送出前的回合)。"""
    if start_turn is None:
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


def finish_turn(game: Game, npc: int, start_turn: int) -> None:
    """之後 NPC 一律 pass,模擬到 start_turn 這個回合交替、對局結束或步數上限。"""
    for _ in range(MAX_STEPS):
        if game.state.phase == GAME_OVER or game.state.turn_no != start_turn:
            return
        settle(game, npc, start_turn=start_turn)
        st = game.state
        if st.phase == GAME_OVER or st.turn_no != start_turn or not npc_free(game, npc):
            return
        if not try_submit(game, npc, {"type": "pass"}):
            return


def turn_end_value(game: Game, npc: int, start_turn: int) -> float:
    """以「本回合結束」為共同基準的評分。送出候選後先模擬到停點;若又輪到 NPC 的非戰鬥決定
    (尚未算到結束階段),延伸一層:接著 pass 或宣告各攻擊,各自模擬到回合結束,取最好者。
    否則停在行動後的候選會少算結束階段的強制翻頁,比 pass 佔便宜(例如不攻擊卻使用 P-001)。
    start_turn 是送出候選前的回合:pass 可能已讓回合交替,不能再往下模擬對手的整個回合。"""
    settle(game, npc, start_turn=start_turn)
    st = game.state
    if st.phase == GAME_OVER or st.turn_no != start_turn or not npc_free(game, npc):
        return evaluate(game, npc)
    follow = [{"type": "pass"}] + [c for c in candidates(game, npc) if c["type"] == "declare_attack"]
    best = None
    for cmd in follow:
        sim = clone(game)
        if not try_submit(sim, npc, cmd):
            continue
        finish_turn(sim, npc, start_turn)   # 以送出前的回合為準:pass 可能已讓回合交替
        score = evaluate(sim, npc)
        best = score if best is None else max(best, score)
    return evaluate(game, npc) if best is None else best - EXTENSION_DISCOUNT


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
    """魔書受傷:能以對手的魔物保護時(P-027)優先用它;否則有健康魔物就以魔力最低者保護,
    會致命時負傷魔物也用。魔物受傷不保護。"""
    st = game.state
    item = st.pending.data["ctx"]["items"][0]
    if item["kind"] != "book":
        return {"type": "choose", "value": None}
    options = [o for o in st.pending.options if o.get("value") is not None]
    theirs = [o["value"] for o in options if o.get("player") == 1 - who]
    if theirs:
        return {"type": "choose", "value": theirs[0]}
    slots = [st.slot_by_uid(who, o["value"]) for o in options]
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
    if attack_undefendable(game, st.battle):
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
