"""視角化序列化:同一份引擎狀態,依觀看者(player0/player1/觀戰/全視角)產出不同視圖。

不變量:任何送出伺服器的狀態/事件都必須經過本模組過濾;
不存在「先送全量、由前端隱藏」的路徑。

viewer 取值:0 / 1 / "spectator" / "all"(本機模式全視角)。
"""

from __future__ import annotations

from ..engine.engine import exhausted_spell_pages, side_breakdown, slot_power, spell_cost
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


def _in_use_pages(game: Game, p: int) -> set[int]:
    """玩家 p 已宣告攻防術的「使用中頁」:宣告即公開,對所有視角揭露。"""
    st = game.state
    pages: set[int] = set()
    if st.battle_in is not None and st.battle_in.get("attacker") == p:
        page = st.battle_in.get("page")
        if page is not None:  # 無術攻擊(M-027)無頁
            pages.add(page)
    if st.battle is not None:
        b = st.battle
        if b.attacker == p and b.attack_page is not None:
            pages.add(b.attack_page)
        if b.defender == p and b.defense_page is not None:
            pages.add(b.defense_page)
    return pages


def _player_view(game: Game, p: int, viewer) -> dict:
    ps = game.state.players[p]
    in_use = _in_use_pages(game, p)
    open_pages = []
    for page in ps.open_pages():
        if can_see_player(viewer, p) or page in in_use:
            number = ps.card_at(page)
            card = game.db[number]
            entry = {"page": page, "card": number}
            if card.type == "spell":
                entry["cost"] = spell_cost(game, p, page, card)
            if page in in_use:
                entry["in_use"] = True  # 持有者視角亦附標,供前端高亮
        else:
            entry = {"page": page}  # 翻開頁內容對非持有者保密(頁碼公開)
        open_pages.append(entry)
    view = {
        "mp": ps.mp,
        "pos": min(ps.pos, BOOK_SIZE + 2),
        "book_size": BOOK_SIZE,
        "open_pages": open_pages,
        "consumed_pages": sorted(ps.consumed_pages),
        "slots": [_slot_view(game, p, s) for s in ps.slots],
        "discard": list(ps.discard),
        "used_spell_pages": sorted(exhausted_spell_pages(game, p)),   # 本回合不能再用的術卡頁
        "used_event_this_turn": ps.used_event_this_turn,
    }
    # 己方完整魔本只對持有者本人揭露(規則上本就已知);對手與觀戰者不含
    if can_see_player(viewer, p):
        view["book"] = list(ps.book)
        view["used_nonbattle_spells"] = sorted(ps.used_nonbattle_spells)
    return view


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
        "effects": _effects_view(game),
    }
    if st.battle_in is not None:
        view["battle_in"] = dict(st.battle_in)  # 已宣告的攻擊為公開資訊
    if st.battle is not None:
        b = st.battle
        att_total, att_items = side_breakdown(game, b, "attack")
        def_total, def_items = side_breakdown(game, b, "defense")
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
            "attacker_total": att_total,
            "defender_total": def_total,
            "attacker_breakdown": att_items,     # 合計魔力的逐項明細(公開)
            "defender_breakdown": def_items,
        }
    if st.pending is not None:
        pending: dict = {
            "kind": st.pending.kind,
            "player": st.pending.player,
            "source": st.pending.source,
            "info": st.pending.info,             # 公開的決策脈絡(如目前擲幣結果)
        }
        if can_see_player(viewer, st.pending.player):
            pending["options"] = st.pending.options  # 選項細節只給決策者
        view["pending"] = pending
    return view


def _effects_view(game: Game) -> list[dict]:
    """作用中的待命與持續效果:只送整理過的公開欄位(建立時已發公開事件),不送 data 內部資料。
    待命在前、持續效果在後,各自依建立順序;戰鬥開始時被消耗的待命已不在 state.standby。"""
    st = game.state
    out = []
    for sb in st.standby:
        out.append({"type": "standby", "kind": sb.kind, "source": sb.source, "owner": sb.owner,
                    "expires": sb.data.get("expires", "turn"), "created_turn": sb.created_turn,
                    "target_slot": sb.data.get("slot_uid"), **_public_data(sb.data)})
    for m in st.modifiers:
        out.append({"type": "modifier", "kind": m.kind, "source": m.source, "owner": m.owner,
                    "duration": m.duration, "created_turn": m.created_turn,
                    "target_player": m.target_player, "target_slot": m.target_slot,
                    "amount": m.amount, "flag": m.flag, **_public_data(m.data)})
    return out


# 效果 data 中可公開、供顯示的欄位(白名單;其餘如續體一律不送)
_PUBLIC_EFFECT_DATA = {"mamodo": str, "card": str, "power_delta": int, "cost_delta": int, "optional": bool}


def _public_data(data: dict) -> dict:
    return {k: data[k] for k, t in _PUBLIC_EFFECT_DATA.items() if isinstance(data.get(k), t)}


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
