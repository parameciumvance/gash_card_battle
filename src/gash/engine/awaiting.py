"""等待者與安全預設指令:對引擎狀態的純查詢。

房間層的逾時代打與 NPC(木人樁、以及送出失敗時的退路)共用。
"""

from __future__ import annotations

from .state import BATTLE, GAME_OVER, START, Game


def awaited_player(game: Game) -> int | None:
    """目前等待哪位玩家輸入;對局結束回 None。"""
    st = game.state
    if st.phase == GAME_OVER:
        return None
    if st.pending is not None:
        return st.pending.player
    if st.phase == START:
        return st.turn_player
    if st.phase != BATTLE:
        return None
    if st.battle is not None:
        if st.battle.step == "defense":
            return st.battle.defender
        return st.battle.data.get("effect_turn")
    if st.battle_in is not None:
        return 1 - st.battle_in["attacker"]
    return st.action_player


def default_command(game: Game) -> dict | None:
    """逾時代打的安全預設指令(不含 player,由呼叫端補上)。"""
    st = game.state
    if st.phase == GAME_OVER:
        return None
    if st.pending is not None:
        kind = st.pending.kind
        if kind == "protect" or kind == "coin_confirm":
            return {"type": "choose", "value": None}       # 不保護 / 保留硬幣
        if kind == "paid_reflip":
            return {"type": "choose", "value": False}      # 放棄付費重擲
        if kind == "damage_order":
            return {"type": "choose", "value": 0}
        if any(o.get("label") == "skip" for o in st.pending.options):
            return {"type": "choose", "value": None}       # 可選擇不使用的效果:不使用
        opt = st.pending.options[0]
        return {"type": "choose", "value": opt.get("value", opt.get("page"))}
    if st.phase == START:
        return {"type": "flip_pages", "count": 0}
    if st.battle is not None:
        if st.battle.step == "defense":
            return {"type": "no_defense"}
        return {"type": "pass"}
    if st.battle_in is not None:
        return {"type": "battle_in_response", "allow": True}  # 迎戰=依規則強制攻擊
    return {"type": "pass"}
