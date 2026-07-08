"""視角化序列化:同一份引擎狀態,依觀看者(player0/player1/觀戰/全視角)產出不同視圖。

不變量:任何送出伺服器的狀態/事件都必須經過本模組過濾;
不存在「先送全量、由前端隱藏」的路徑。

viewer 取值:0 / 1 / "spectator" / "all"(本機模式全視角)。
"""

from __future__ import annotations

from ..engine.engine import slot_power, spell_cost
from ..engine.state import BOOK_SIZE, Game

# 帶 viewer 欄位、內容僅該玩家可見的事件型別
_VIEWER_SCOPED_EVENTS = {"book_revealed", "pages_peeked"}
# choice_required 對非決策者需裁剪的欄位
_CHOICE_PRIVATE_FIELDS = ("options", "item", "results")


def can_see_player(viewer, player: int) -> bool:
    return viewer == "all" or viewer == player


def _ability_view(number: str | None) -> dict | None:
    from ..engine.effects import registry as reg
    if number is None:
        return None
    spec = reg.ACTIVATED.get(number)
    if spec is None:
        return None
    return {"mode": spec.mode, "mp_cost": spec.mp_cost,
            "timing": spec.timing, "per_game": spec.per_game}


def _slot_view(game: Game, player: int, slot) -> dict:
    from ..engine.effects import registry as reg
    return {
        "uid": slot.uid,
        "stack": list(slot.stack),
        "top": slot.top,
        "injured": slot.injured,
        "partner": slot.partner,
        "power": slot_power(game, player, slot),
        "ability": _ability_view(slot.top),
        "partner_ability": _ability_view(slot.partner),
        "mamodo_attack": reg.MAMODO_ATTACK.get(slot.top),  # 無術攻擊規格(M-027)
    }


def _player_view(game: Game, p: int, viewer) -> dict:
    ps = game.state.players[p]
    open_pages = []
    for page in ps.open_pages():
        if can_see_player(viewer, p):
            number = ps.card_at(page)
            card = game.db[number]
            entry = {"page": page, "card": number}
            if card.type == "spell":
                entry["cost"] = spell_cost(game, p, page, card)
        else:
            entry = {"page": page}  # 翻開頁內容對非持有者保密(頁碼公開)
        open_pages.append(entry)
    return {
        "mp": ps.mp,
        "pos": min(ps.pos, BOOK_SIZE + 2),
        "book_size": BOOK_SIZE,
        "open_pages": open_pages,
        "consumed_pages": sorted(ps.consumed_pages),
        "slots": [_slot_view(game, p, s) for s in ps.slots],
        "discard": list(ps.discard),
        "used_spell_pages": sorted(ps.used_spell_pages),
        "used_event_this_turn": ps.used_event_this_turn,
    }


def snapshot(game: Game, viewer) -> dict:
    st = game.state
    view: dict = {
        "phase": st.phase,
        "turn_no": st.turn_no,
        "turn_player": st.turn_player,
        "action_player": st.action_player,
        "players": [_player_view(game, 0, viewer), _player_view(game, 1, viewer)],
        "winner": st.winner,
        "end_reason": st.end_reason,
        "event_count": len(game.events),
    }
    if st.battle_in is not None:
        view["battle_in"] = dict(st.battle_in)  # 已宣告的攻擊為公開資訊
    if st.battle is not None:
        b = st.battle
        from ..engine.engine import _side_total
        view["battle"] = {
            "attacker": b.attacker,
            "step": b.step,
            "attack_spell": b.attack_spell,
            "attack_slot": b.attack_slot,
            "attack_negated": b.attack_negated,
            "attack_undefendable": b.attack_undefendable,
            "defense_spell": b.defense_spell,
            "defense_slot": b.defense_slot,
            "defense_negated": b.defense_negated,
            "effect_turn": b.data.get("effect_turn"),
            "attacker_total": _side_total(game, b, "attack"),
            "defender_total": _side_total(game, b, "defense"),
        }
    if st.pending is not None:
        pending: dict = {
            "kind": st.pending.kind,
            "player": st.pending.player,
            "source": st.pending.source,
        }
        if can_see_player(viewer, st.pending.player):
            pending["options"] = st.pending.options  # 選項細節只給決策者
        view["pending"] = pending
    return view


def filter_event(ev: dict, viewer) -> dict | None:
    """回傳該視角可見的事件(可能為裁剪副本);完全公開的事件原樣回傳。"""
    if viewer == "all":
        return ev
    if ev["type"] in _VIEWER_SCOPED_EVENTS:
        if viewer == ev.get("viewer"):
            return ev
        return {k: v for k, v in ev.items() if k != "cards"}
    if ev["type"] == "choice_required":
        if viewer == ev.get("player"):
            return ev
        return {k: v for k, v in ev.items() if k not in _CHOICE_PRIVATE_FIELDS}
    return ev


def filter_events(events: list[dict], viewer) -> list[dict]:
    out = []
    for ev in events:
        f = filter_event(ev, viewer)
        if f is not None:
            out.append(f)
    return out
