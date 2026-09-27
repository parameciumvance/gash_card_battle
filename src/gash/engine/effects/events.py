"""尚未遷移到效果樹的事件卡(依日版 j 文意)。已遷移的事件卡見 tree_cards.py。

剩下的卡各有待設計的節點,見 openspec/changes/effect-tree-migration/tasks.md 第 2 組:
E-011(付費重擲)、E-012 / E-016 / E-017(從魔本選頁)、E-018、E-027。
"""

from __future__ import annotations

from ..cards import MAMODO, PARTNER
from ..state import MAX_FIELD_MAMODO, MamodoSlot, PendingChoice
from . import registry as reg
from .primitives import choose_or_auto, flip_coins


# E-011 鉄のフォルゴレ:擲硬幣 正→棄牌區夥伴放到場上 / 反→可付2MP重擲
def _e011_targets(game, player):
    ps = game.state.players[player]
    out = []
    for i, number in enumerate(ps.discard):
        card = game.db[number]
        if card.type != PARTNER:
            continue
        slot = next((s for s in ps.slots
                     if game.db[s.top].related_mamodo == card.related_mamodo
                     and s.partner is None), None)
        if slot is None:
            continue
        if any(game.db[s.partner].name_ja == card.name_ja for s in ps.slots if s.partner):
            continue
        out.append({"value": i, "card": number, "slot_uid": slot.uid})
    return out


@reg.event("E-011", condition=lambda g, p: bool(_e011_targets(g, p)))
def e011(game, batch, player, page):
    flip_coins(game, batch, player, 1, "E-011", "e011_resolve", {"player": player})


@reg.choice_resolver("e011_resolve")
def e011_resolve(game, batch, results, data):
    player = data["player"]
    if results[0]:
        targets = _e011_targets(game, player)
        if not targets:
            return
        choose_or_auto(game, batch, kind="e011_pick", player=player,
                       options=targets, data={"player": player}, source="E-011")
        return
    # 反面:可付 2 MP 重擲
    if game.state.players[player].mp >= 2:
        game.state.pending = PendingChoice(
            kind="e011_retry", player=player, source="E-011",
            options=[{"value": True, "label": "pay_reflip"}, {"value": False, "label": "stop"}],
            data={"player": player})
        game.emit(batch, "choice_required", kind="e011_retry", player=player)


@reg.choice_resolver("e011_retry")
def e011_retry(game, batch, value, data):
    player = data["player"]
    game.state.pending = None
    if not value:
        return
    from ..engine import IllegalCommand, pay_mp
    if game.state.players[player].mp < 2:
        raise IllegalCommand("choose.invalid", "MP 不足以重擲")
    pay_mp(game, batch, player, 2, "E-011")
    flip_coins(game, batch, player, 1, "E-011", "e011_resolve", {"player": player})


@reg.choice_resolver("e011_pick")
def e011_pick(game, batch, value, data):
    from ..engine import IllegalCommand
    player = data["player"]
    targets = {t["value"]: t for t in _e011_targets(game, player)}
    if value not in targets:
        raise IllegalCommand("choose.invalid", "須選擇棄牌區中可放出的夥伴卡")
    t = targets[value]
    ps = game.state.players[player]
    number = ps.discard.pop(t["value"])
    slot = game.state.slot_by_uid(player, t["slot_uid"])
    slot.partner = number
    game.emit(batch, "card_played", player=player, card=number, slot=slot.uid,
              zone="partner", from_discard=True)
    if number in reg.ON_PLAY:
        reg.ON_PLAY[number](game, batch, player, slot)


# E-012 ガッシュ登場:從魔本任意頁放出 1 張魔物
def _e012_targets(game, player):
    ps = game.state.players[player]
    if len(ps.slots) >= MAX_FIELD_MAMODO:
        return []
    out = []
    for p in range(1, 33):
        if p in ps.consumed_pages:
            continue
        number = ps.card_at(p)
        card = game.db[number]
        if card.type != MAMODO:
            continue
        if number in reg.STACK_ON:
            if not any(s.top in reg.STACK_ON[number] for s in ps.slots):
                continue
        else:
            from ..engine import same_name_in_play
            if same_name_in_play(game, player, card):
                continue
        out.append({"value": p, "card": number})
    return out


@reg.event("E-012", condition=lambda g, p: bool(_e012_targets(g, p)))
def e012(game, batch, player, page):
    choose_or_auto(game, batch, kind="e012_pick", player=player,
                   options=_e012_targets(game, player), data={"player": player}, source="E-012")


@reg.choice_resolver("e012_pick")
def e012_pick(game, batch, value, data):
    from ..engine import IllegalCommand
    player = data["player"]
    if value not in {t["value"] for t in _e012_targets(game, player)}:
        raise IllegalCommand("choose.invalid", "須選擇魔本中可放出的魔物卡")
    ps = game.state.players[player]
    number = ps.card_at(value)
    ps.consumed_pages.add(value)
    if number in reg.STACK_ON:
        base = next(s for s in ps.slots if s.top in reg.STACK_ON[number])
        base.stack.append(number)
        base.injured = False
        game.emit(batch, "card_played", player=player, card=number, slot=base.uid,
                  zone="mamodo", stacked=True)
        slot = base
    else:
        slot = MamodoSlot(uid=game.state.next_uid(), stack=[number])
        ps.slots.append(slot)
        game.emit(batch, "card_played", player=player, card=number, slot=slot.uid, zone="mamodo")
    if number in reg.ON_PLAY:
        reg.ON_PLAY[number](game, batch, player, slot)


# ======================================================================
# Level 2 事件卡(E-016~E-027)
# ======================================================================

from .primitives import discard_from_book, reduce_mp  # noqa: E402


# E-016 高嶺清太郎:檢視對手書,選 1 術卡(末頁除外)棄掉,MP -該卡費用
# E-017 高嶺花:檢視對手書,選 1 事件卡棄掉,MP -該卡費用
def _opp_book_options(game, player, card_type, exclude_last):
    opp = game.state.players[1 - player]
    opts = []
    for p in range(1, 33):
        if p in opp.consumed_pages:
            continue
        if exclude_last and p == 32:
            continue
        if game.db[opp.card_at(p)].type == card_type:
            opts.append({"value": p, "card": opp.card_at(p), "page": p})
    return opts


def _reveal_opp_book(game, batch, player):
    opp = game.state.players[1 - player]
    game.emit(batch, "book_revealed", player=1 - player, viewer=player,
              cards=[{"page": p, "card": opp.card_at(p)}
                     for p in range(1, 33) if p not in opp.consumed_pages])


@reg.event("E-016", condition=lambda g, p: bool(_opp_book_options(g, p, "spell", True)))
def e016(game, batch, player, page):
    _reveal_opp_book(game, batch, player)
    choose_or_auto(game, batch, kind="e016_pick", player=player,
                   options=_opp_book_options(game, player, "spell", True),
                   data={"player": player, "type": "spell", "exclude_last": True},
                   source="E-016")


@reg.event("E-017", condition=lambda g, p: bool(_opp_book_options(g, p, "event", False)))
def e017(game, batch, player, page):
    _reveal_opp_book(game, batch, player)
    choose_or_auto(game, batch, kind="e016_pick", player=player,
                   options=_opp_book_options(game, player, "event", False),
                   data={"player": player, "type": "event", "exclude_last": False},
                   source="E-017")


@reg.choice_resolver("e016_pick")
def e016_pick(game, batch, value, data):
    from ..engine import IllegalCommand
    player = data["player"]
    valid = {o["value"] for o in _opp_book_options(game, player, data["type"], data["exclude_last"])}
    if value not in valid:
        raise IllegalCommand("choose.invalid", "須選擇對手書中對應類型的卡")
    cost = game.db[game.state.players[1 - player].card_at(value)].cost or 0
    discard_from_book(game, batch, 1 - player, value, "E-016/017")
    reduce_mp(game, batch, player, cost, "E-016/017")


# E-018 フォルゴレのダンス:對手 MP-4(上一回合已減過對手 MP 則不減 — j 版)
@reg.event("E-018")
def e018(game, batch, player, page):
    # 記錄本回合減 MP;若上一回合曾減則跳過
    st = game.state
    last = st.players[player].__dict__.get("_mp_reduce_turn")
    if last == st.turn_no - 1:
        game.emit(batch, "effect_applied", source="E-018", skipped=True)
        return
    reduce_mp(game, batch, 1 - player, 4, "E-018")
    st.players[player].__dict__["_mp_reduce_turn"] = st.turn_no


# E-027 親友:雙方場上夥伴只留 1 張,無夥伴者自書取 1 張(先對手後自己)
@reg.event("E-027")
def e027(game, batch, player, page):
    _e027_side(game, batch, 1 - player, "E-027")  # 先對手
    _e027_side(game, batch, player, "E-027")       # 後自己


def _e027_side(game, batch, side, source):
    from .primitives import discard_partner, attach_partner_from_book
    ps = game.state.players[side]
    partnered = [s for s in ps.slots if s.partner]
    if partnered:
        # 保留第 1 張,其餘棄掉
        for s in partnered[1:]:
            discard_partner(game, batch, side, s, source)
    else:
        # 無夥伴:自書任意頁取 1 張裝到對應魔物(自動取第一個可裝的)
        for p in range(1, 33):
            if p in ps.consumed_pages:
                continue
            card = game.db[ps.card_at(p)]
            if card.type != PARTNER:
                continue
            slot = next((s for s in ps.slots
                         if game.db[s.top].related_mamodo == card.related_mamodo
                         and s.partner is None), None)
            if slot is not None:
                attach_partner_from_book(game, batch, side, p, slot)
                break
