"""尚未遷移到效果樹的事件卡(依日版 j 文意)。已遷移的事件卡見 tree_cards.py。

剩下的卡各有待設計的節點,見 openspec/changes/effect-tree-migration/tasks.md 第 2 組:
E-011(付費重擲)、E-018、E-027。
"""

from __future__ import annotations

from ..cards import PARTNER
from ..state import PendingChoice
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


# ======================================================================
# Level 2 事件卡(E-016~E-027)
# ======================================================================

from .primitives import reduce_mp  # noqa: E402


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
