"""視角化序列化:同一份引擎狀態,依觀看者(player0/player1/觀戰/全視角)產出不同視圖。

不變量:任何送出伺服器的狀態/事件都必須經過本模組過濾;
不存在「先送全量、由前端隱藏」的路徑。

viewer 取值:0 / 1 / "spectator" / "all"(本機模式全視角)。
"""

from __future__ import annotations

from ..engine.engine import (
    _spell_any_page_standby, _spell_usable_by, attack_undefendable, effect_block_sources, event_cost_breakdown,
    event_limit, exhausted_spell_pages, partner_targets, play_block, power_breakdown, reveals_open_pages,
    side_breakdown, spell_block, spell_cost, spell_cost_breakdown, uses_this_turn,
)
from ..engine.state import BOOK_SIZE, Game, slot_columns

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
            "timing": spec.timing, "own_turn": spec.own_turn, "per_game": spec.per_game}


def _used(ps, key: str, number, per_game: bool = False):
    """效果的使用狀態(公開):"game" 一場限 1 次已用、"turn" 本回合已用、False 未用。"""
    if number is None:
        return False
    if per_game and number in ps.used_per_game:
        return "game"
    return "turn" if f"{key}:{number}" in ps.used_abilities else False


def _slot_view(game: Game, player: int, slot) -> dict:
    from ..engine.effects import registry as reg
    ps = game.state.players[player]
    top_spec, partner_spec = reg.ACTIVATED.get(slot.top), reg.ACTIVATED.get(slot.partner)
    power, power_items = power_breakdown(game, player, slot)
    return {
        "uid": slot.uid,
        "column": slot_columns(game.state.players[player].slots)[slot.uid],   # 場上欄位(公開)
        "stack": list(slot.stack),
        "top": slot.top,
        "injured": slot.injured,
        "partner": slot.partner,
        "power": power,
        "power_breakdown": power_items,   # 逐項加總等於 power(公開)
        # 失效中的常駐效果:頂層與搭檔中被「使えない」擋下者與限制來源(限制是公開的)
        "blocked_effects": [{"card": n, "by": by} for n in (slot.top, slot.partner)
                            if reg.has_passive(n) and (by := effect_block_sources(game, player, slot, n))],
        "ability": _ability_view(slot.top),
        "partner_ability": _ability_view(slot.partner),
        "mamodo_attack": reg.MAMODO_ATTACK.get(slot.top),  # 魔物效果攻擊規格(M-027)
        "mamodo_defense": reg.MAMODO_DEFENSE.get(slot.top),  # 魔物效果防禦規格(M-039)
        # 「1アクションを使って…捨て札にできる」:疊放的上層(M-046)/ 搭檔(P-020)
        "action_discard": len(slot.stack) > 1 and reg.ACTION_DISCARD.get(slot.top) == "top",
        "partner_action_discard": reg.ACTION_DISCARD.get(slot.partner) == "partner",
        # 效果已使用(每回合 1 次 / 一場限 1 次):前端據此停用按鈕
        "ability_used": _used(ps, "mamodo", slot.top, bool(top_spec and top_spec.per_game)),
        "partner_ability_used": _used(ps, "partner", slot.partner, bool(partner_spec and partner_spec.per_game)),
        "mamodo_attack_used": _attack_used(ps, slot.top),
        "mamodo_defense_used": _used(ps, "mamodo_defense", slot.top),
    }


def _attack_used(ps, number):
    """魔物效果攻擊本回合已用滿次數(M-068 每回合 2 次)時為 "turn"。"""
    from ..engine.effects import registry as reg
    spec = reg.MAMODO_ATTACK.get(number)
    return "turn" if spec and uses_this_turn(ps, f"mamodo_attack:{number}") >= spec["per_turn"] else False


def _in_use_pages(game: Game, p: int) -> set[int]:
    """玩家 p 已宣告攻防戰術的「使用中頁」:宣告即公開,對所有視角揭露。"""
    st = game.state
    pages: set[int] = set()
    if st.battle_in is not None and st.battle_in.get("attacker") == p:
        page = st.battle_in.get("page")
        if page is not None:  # 魔物效果攻擊(M-027)無頁
            pages.add(page)
    if st.battle is not None:
        b = st.battle
        if b.attacker == p and b.attack_page is not None:
            pages.add(b.attack_page)
        if b.defender == p and b.defense_page is not None:
            pages.add(b.defense_page)
    return pages


def _spell_users(game: Game, p: int, page: int, card) -> list[dict]:
    """可使用此戰術的自己場上魔物(持有者私有):依引擎的相容判定,附依該魔物計算的費用與是否被
    指定魔物的封鎖擋下(E-024 / S-074 / E-043)。"""
    return [{"slot_uid": s.uid, "cost": spell_cost(game, p, page, card, slot=s),
             "locked": spell_block(game, p, s, card=card) == "spell.mamodo_locked"}
            for s in game.state.players[p].slots
            if card.is_command_spell or _spell_usable_by(game, p, s, card)]


def _condition_ok(game: Game, p: int, card) -> bool:
    """事件卡 / 非戰鬥戰術登記的使用條件(例如選得到對象)目前是否成立;與引擎檢查共用同一個函式。"""
    from ..engine.effects import registry as reg
    table = reg.EVENT_CONDITION if card.type == "event" else reg.SPELL_NONBATTLE_CONDITION
    condition = table.get(card.number)
    return bool(condition(game, p)) if condition else True


def _any_page_spells(game: Game, p: int) -> list[dict]:
    """待命允許從魔書任意頁使用的戰術(P-015):翻開的頁與已離開魔書的頁除外。"""
    ps = game.state.players[p]
    out = []
    for page in range(1, BOOK_SIZE + 1):
        if page in ps.open_pages() or not _spell_any_page_standby(game, p, page):
            continue
        card = game.db[ps.card_at(page)]
        cost, items = spell_cost_breakdown(game, p, page, card)
        out.append({"page": page, "card": card.number, "cost": cost, "cost_breakdown": items,
                    "users": _spell_users(game, p, page, card)})
    return out


def _player_view(game: Game, p: int, viewer) -> dict:
    ps = game.state.players[p]
    in_use = _in_use_pages(game, p)
    open_pages = []
    revealed = reveals_open_pages(game, viewer, p)   # P-024:對手看得到翻開的頁
    for page in ps.open_pages():
        if can_see_player(viewer, p) or page in in_use or revealed:
            number = ps.card_at(page)
            card = game.db[number]
            entry = {"page": page, "card": number}
            if card.type == "spell":
                entry["cost"], entry["cost_breakdown"] = spell_cost_breakdown(game, p, page, card)
                if can_see_player(viewer, p):
                    entry["users"] = _spell_users(game, p, page, card)
            elif card.type == "event":
                entry["cost"], entry["cost_breakdown"] = event_cost_breakdown(game, p, card)   # 含對手 M-040 的加成
            elif can_see_player(viewer, p):   # 魔物 / 搭檔:放出可否(與 play_card 同一判斷)
                entry["play_block"] = play_block(game, p, number)
                if card.type == "partner":
                    entry["targets"] = [s.uid for s in partner_targets(game, p, card)]
            if can_see_player(viewer, p) and (card.type == "event" or card.effect_icon == "nonbattle"):
                entry["condition_ok"] = _condition_ok(game, p, card)
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
        "used_spell_pages": sorted(exhausted_spell_pages(game, p)),   # 本回合不能再用的戰術卡頁
        "events_exhausted": ps.events_used_this_turn >= event_limit(game, p),   # 本回合事件卡已達上限(E-029 可提高)
    }
    # 己方完整魔書只對持有者本人揭露(規則上本就已知);對手與觀戰者不含
    if can_see_player(viewer, p):
        view["book"] = list(ps.book)
        view["any_page_spells"] = _any_page_spells(game, p)
        view["used_nonbattle_pages"] = sorted(ps.used_nonbattle_pages)
    return view


def snapshot(game: Game, viewer) -> dict:
    st = game.state
    view: dict = {
        "phase": st.phase,
        "turn_no": st.turn_no,
        "turn_player": st.turn_player,
        "action_player": st.action_player,
        "consecutive_passes": st.consecutive_passes,   # 非戰鬥中雙方連續 pass 的次數(公開)
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
            "attack_undefendable": attack_undefendable(game, b),
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
        entry = {"type": "modifier", "kind": m.kind, "source": m.source, "owner": m.owner,
                 "duration": m.duration, "created_turn": m.created_turn,
                 "target_player": m.target_player, "target_slot": m.target_slot,
                 "amount": m.amount, "flag": m.flag, **_public_data(m.data)}
        if m.kind == "borrow_partner":   # E-010:借到的效果規格(時機等),前端據此判斷可否使用
            entry["ability"] = _ability_view(m.data.get("card"))
        out.append(entry)
    # 場上的常駐禁止(P-031):不是持續效果,但影響對手可用的行動,一併列出
    from ..engine.effects import registry as reg
    for p, ps in enumerate(st.players):
        for s in ps.slots:
            spec = reg.BLOCK_OPPONENT_FAMILY.get(s.partner)
            if spec is None:
                continue
            event = next((n for n, c in game.db.items() if c.type == "event" and c.name_ja == spec[1]), None)
            out.append({"type": "static", "kind": "block_family", "source": s.partner, "owner": p,
                        "target_player": 1 - p, "target_slot": None, "mamodo": spec[0], "card": event})
    for p, ps in enumerate(st.players):   # P-038:持有者的戰鬥階段中對手不能使用事件卡
        for s in ps.slots:
            if s.partner in reg.OPPONENT_EVENT_LOCK:
                out.append({"type": "static", "kind": "event_lock", "source": s.partner, "owner": p,
                            "target_player": 1 - p, "target_slot": None})
    return out


# 效果 data 中可公開、供顯示的欄位(白名單;其餘如續體一律不送)
_PUBLIC_EFFECT_DATA = {"mamodo": str, "card": str, "power_delta": int, "cost_delta": int, "optional": bool,
                       "used": bool,   # used:E-010 借用的效果本回合是否已使用
                       "attr": str,    # attr:P-029 可使用的戰術屬性(日文元素名)
                       "amount": int,  # amount:E-038 待命的 MP 增加量(持續效果另有同名欄位)
                       "page": int,    # page:S-098 選定要重用的戰術頁(本回合已使用、已公開)
                       "value": int,   # value:P-011「魔力を 0 にする」的值
                       "copy_card": str,   # copy_card:M-035 魔力等於的對手魔物(使用時的卡)
                       "turn": int,    # turn:M-047 離場的回合
                       "min_total": int,   # min_total:M-048 不能防禦的合計魔力門檻
                       "count": int,   # count:E-042 結束階段要棄掉的魔物數
                       "base_zero": bool, "base_delta": int,   # Ex-007 類 / Ex-035:下一場戰鬥的本來費用調整
                       "name": str, "cost": int, "power": int}   # PR-010:戰術名稱、本來費用與魔力的增減


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
