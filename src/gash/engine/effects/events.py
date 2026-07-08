"""事件卡效果(E-001~E-015),依日版 j 文意。"""

from __future__ import annotations

from ..cards import MAMODO, PARTNER
from ..state import (
    DUR_NEXT_TURN, DUR_TURN, DUR_UNTIL_END_NEXT_TURN, MAX_FIELD_MAMODO,
    NO_PARTNER_EFFECTS, NO_SPELLS, MamodoSlot, PendingChoice,
)
from . import registry as reg
from .primitives import (
    add_modifier, add_power, add_restriction, choose_or_auto, flip_coins,
    heal_slot, schedule_standby, turn_back_pages, turn_pages,
)


def _own_slots(game, player):
    return game.state.players[player].slots


def _slot_options(game, player, predicate=lambda s: True):
    return [{"value": s.uid, "card": s.top} for s in _own_slots(game, player) if predicate(s)]


# E-001 守る心:下回合自己 1 隻魔物 +3000(待命至下回合開始階段)
@reg.event("E-001", condition=lambda g, p: bool(g.state.players[p].slots))
def e001(game, batch, player, page):
    choose_or_auto(game, batch, kind="e001_pick", player=player,
                   options=_slot_options(game, player), data={"player": player}, source="E-001")


@reg.choice_resolver("e001_pick")
def e001_pick(game, batch, value, data):
    from ..engine import IllegalCommand
    player = data["player"]
    slot = game.state.slot_by_uid(player, value if isinstance(value, int) else -1)
    if slot is None:
        raise IllegalCommand("choose.invalid", "須選擇自己場上的魔物")
    sb = schedule_standby(game, batch, kind="start_phase", source="E-001", owner=player,
                          data={"callback": "e001_fire", "slot_uid": slot.uid,
                                "player": player, "expires": "next_start"})


@reg.choice_resolver("e001_fire")
def e001_fire(game, batch, value, data):
    player = data["player"]
    slot = game.state.slot_by_uid(player, data["slot_uid"])
    if slot is None:
        return
    add_power(game, batch, source="E-001", owner=player, target_player=player,
              target_slot=slot.uid, amount=3000, duration=DUR_TURN)


# E-002 ティーナ:至下回合結束階段,雙方不能使用術卡
@reg.event("E-002")
def e002(game, batch, player, page):
    for p in (0, 1):
        add_restriction(game, batch, source="E-002", owner=player,
                        target_player=p, flag=NO_SPELLS, duration=DUR_UNTIL_END_NEXT_TURN)


# E-003 ブリ:MP+2
@reg.event("E-003")
def e003(game, batch, player, page):
    from ..engine import gain_mp
    gain_mp(game, batch, player, 2, "E-003")


# E-004 友情のカレー:雙方 MP 歸 0
@reg.event("E-004")
def e004(game, batch, player, page):
    for p in (0, 1):
        ps = game.state.players[p]
        if ps.mp:
            game.emit(batch, "mp_changed", player=p, delta=-ps.mp, mp=0, reason="E-004")
            ps.mp = 0


# E-005 鈴芽のお見舞い:擲2硬幣 正正→魔本回翻2張 / 正反→無效 / 反反→翻2張
@reg.event("E-005")
def e005(game, batch, player, page):
    flip_coins(game, batch, player, 2, "E-005", "e005_resolve", {"player": player})


@reg.choice_resolver("e005_resolve")
def e005_resolve(game, batch, results, data):
    player = data["player"]
    heads = sum(results)
    if heads == 2:
        turn_back_pages(game, batch, player, 2, "E-005")
    elif heads == 0:
        turn_pages(game, batch, player, 2, "E-005")


# E-006 秋山勇太:選1隻魔物擲硬幣 正→回復健康 / 反→本回合+1000
@reg.event("E-006", condition=lambda g, p: bool(g.state.players[p].slots))
def e006(game, batch, player, page):
    choose_or_auto(game, batch, kind="e006_pick", player=player,
                   options=_slot_options(game, player), data={"player": player}, source="E-006")


@reg.choice_resolver("e006_pick")
def e006_pick(game, batch, value, data):
    from ..engine import IllegalCommand
    player = data["player"]
    slot = game.state.slot_by_uid(player, value if isinstance(value, int) else -1)
    if slot is None:
        raise IllegalCommand("choose.invalid", "須選擇自己場上的魔物")
    game.state.pending = None
    flip_coins(game, batch, player, 1, "E-006", "e006_resolve",
               {"player": player, "slot_uid": slot.uid})


@reg.choice_resolver("e006_resolve")
def e006_resolve(game, batch, results, data):
    player = data["player"]
    slot = game.state.slot_by_uid(player, data["slot_uid"])
    if slot is None:
        return
    if results[0]:
        heal_slot(game, batch, player, slot, "E-006")
    else:
        add_power(game, batch, source="E-006", owner=player, target_player=player,
                  target_slot=slot.uid, amount=1000, duration=DUR_TURN)


# E-007 木山つくし:1隻負傷魔物回復健康
@reg.event("E-007", condition=lambda g, p: any(s.injured for s in g.state.players[p].slots))
def e007(game, batch, player, page):
    choose_or_auto(game, batch, kind="e007_pick", player=player,
                   options=_slot_options(game, player, lambda s: s.injured),
                   data={"player": player}, source="E-007")


@reg.choice_resolver("e007_pick")
def e007_pick(game, batch, value, data):
    from ..engine import IllegalCommand
    player = data["player"]
    slot = game.state.slot_by_uid(player, value if isinstance(value, int) else -1)
    if slot is None or not slot.injured:
        raise IllegalCommand("choose.invalid", "須選擇自己場上的負傷魔物")
    heal_slot(game, batch, player, slot, "E-007")


# E-008 水野鈴芽:本回合雙方夥伴卡效果失效
@reg.event("E-008")
def e008(game, batch, player, page):
    for p in (0, 1):
        add_restriction(game, batch, source="E-008", owner=player,
                        target_player=p, flag=NO_PARTNER_EFFECTS, duration=DUR_TURN)


# E-009 やさしい王様:本回合自己 1 隻魔物 +3000
@reg.event("E-009", condition=lambda g, p: bool(g.state.players[p].slots))
def e009(game, batch, player, page):
    choose_or_auto(game, batch, kind="e009_pick", player=player,
                   options=_slot_options(game, player), data={"player": player}, source="E-009")


@reg.choice_resolver("e009_pick")
def e009_pick(game, batch, value, data):
    from ..engine import IllegalCommand
    player = data["player"]
    slot = game.state.slot_by_uid(player, value if isinstance(value, int) else -1)
    if slot is None:
        raise IllegalCommand("choose.invalid", "須選擇自己場上的魔物")
    add_power(game, batch, source="E-009", owner=player, target_player=player,
              target_slot=slot.uid, amount=3000, duration=DUR_TURN)


# E-010 やさしい清麿:[待命] 借用對手 1 張夥伴卡的效果(本回合 1 次,不棄掉)
@reg.event("E-010", condition=lambda g, p: any(s.partner for s in g.state.players[1 - p].slots))
def e010(game, batch, player, page):
    opp = game.state.players[1 - player]
    options = [{"value": s.uid, "card": s.partner} for s in opp.slots if s.partner]
    choose_or_auto(game, batch, kind="e010_pick", player=player, options=options,
                   data={"player": player}, source="E-010")


@reg.choice_resolver("e010_pick")
def e010_pick(game, batch, value, data):
    from ..engine import IllegalCommand
    player = data["player"]
    opp_slot = game.state.slot_by_uid(1 - player, value if isinstance(value, int) else -1)
    if opp_slot is None or not opp_slot.partner:
        raise IllegalCommand("choose.invalid", "須選擇對手場上的夥伴卡")
    add_modifier(game, batch, kind="borrow_partner", source="E-010", owner=player,
                 duration=DUR_TURN, target_player=player,
                 data={"slot_uid": opp_slot.uid, "card": opp_slot.partner})


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
        if any(game.db[s.partner].name_en == card.name_en for s in ps.slots if s.partner):
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


# E-013 ナオミちゃん:[待命] 本回合下一場戰鬥,對手不能庇護魔本傷害
@reg.event("E-013")
def e013(game, batch, player, page):
    schedule_standby(game, batch, kind="no_protect_book", source="E-013", owner=player)


# E-014 ウマゴン:翻對手魔本 1 張,檢視其翻開頁面
@reg.event("E-014")
def e014(game, batch, player, page):
    turn_pages(game, batch, 1 - player, 1, "E-014")
    opp = game.state.players[1 - player]
    game.emit(batch, "pages_peeked", player=1 - player, viewer=player,
              cards=[{"page": p, "card": opp.card_at(p)} for p in opp.open_pages()])


# E-015 バルカン３００:至下回合結束階段,自己 1 隻魔物 +2000
@reg.event("E-015", condition=lambda g, p: bool(g.state.players[p].slots))
def e015(game, batch, player, page):
    choose_or_auto(game, batch, kind="e015_pick", player=player,
                   options=_slot_options(game, player), data={"player": player}, source="E-015")


@reg.choice_resolver("e015_pick")
def e015_pick(game, batch, value, data):
    from ..engine import IllegalCommand
    player = data["player"]
    slot = game.state.slot_by_uid(player, value if isinstance(value, int) else -1)
    if slot is None:
        raise IllegalCommand("choose.invalid", "須選擇自己場上的魔物")
    add_power(game, batch, source="E-015", owner=player, target_player=player,
              target_slot=slot.uid, amount=2000, duration=DUR_UNTIL_END_NEXT_TURN)


# ======================================================================
# Level 2 事件卡(E-016~E-027)
# ======================================================================

from ..state import MAMODO_LOCKED, NO_MAMODO_EFFECTS  # noqa: E402
from .primitives import (  # noqa: E402
    add_restriction, book_page_options, discard_from_book, play_mamodo_from_book,
    reduce_mp,
)


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


# E-019 清麿の怒り:將自己場上 1 張魔物卡棄掉
@reg.event("E-019", condition=lambda g, p: bool(g.state.players[p].slots))
def e019(game, batch, player, page):
    options = [{"value": s.uid, "card": s.top} for s in game.state.players[player].slots]
    choose_or_auto(game, batch, kind="e019_pick", player=player, options=options,
                   data={"player": player}, source="E-019")


@reg.choice_resolver("e019_pick")
def e019_pick(game, batch, value, data):
    from ..engine import IllegalCommand, _discard_slot
    player = data["player"]
    slot = game.state.slot_by_uid(player, value if isinstance(value, int) else -1)
    if slot is None:
        raise IllegalCommand("choose.invalid", "須選擇自己場上的魔物")
    _discard_slot(game, batch, player, slot, reason="E-019")


# E-020 恵のコンサート:MP+3;對手擲幣正→對手 MP+3
@reg.event("E-020")
def e020(game, batch, player, page):
    from ..engine import gain_mp
    gain_mp(game, batch, player, 3, "E-020")
    flip_coins(game, batch, 1 - player, 1, "E-020", "e020_resolve", {"player": player})


@reg.choice_resolver("e020_resolve")
def e020_resolve(game, batch, results, data):
    from ..engine import gain_mp
    if results[0]:
        gain_mp(game, batch, 1 - data["player"], 3, "E-020")


# E-021 ひと安心!:場上≥2魔物時,回復1隻負傷 和/或 MP+2(j 版)
@reg.event("E-021", condition=lambda g, p: len(g.state.players[p].slots) >= 2)
def e021(game, batch, player, page):
    injured = [s for s in game.state.players[player].slots if s.injured]
    if injured:
        heal_slot(game, batch, player, injured[0], "E-021")
    from ..engine import gain_mp
    gain_mp(game, batch, player, 2, "E-021")


# E-022 コリー:擲幣正→從棄牌區選本回合入墓的夥伴放到場上
def _e022_targets(game, player):
    ps = game.state.players[player]
    out = []
    for i, number in enumerate(ps.discard):
        card = game.db[number]
        if card.type != PARTNER or number not in ps.discarded_this_turn:
            continue
        slot = next((s for s in ps.slots
                     if game.db[s.top].related_mamodo == card.related_mamodo
                     and s.partner is None), None)
        if slot is None:
            continue
        out.append({"value": i, "card": number, "slot_uid": slot.uid})
    return out


@reg.event("E-022", condition=lambda g, p: any(n in g.state.players[p].discarded_this_turn
                                               and g.db[n].type == PARTNER
                                               for n in g.state.players[p].discard))
def e022(game, batch, player, page):
    flip_coins(game, batch, player, 1, "E-022", "e022_resolve", {"player": player})


@reg.choice_resolver("e022_resolve")
def e022_resolve(game, batch, results, data):
    player = data["player"]
    if not results[0]:
        return
    targets = _e022_targets(game, player)
    if not targets:
        return
    choose_or_auto(game, batch, kind="e022_pick", player=player, options=targets,
                   data={"player": player}, source="E-022")


@reg.choice_resolver("e022_pick")
def e022_pick(game, batch, value, data):
    from ..engine import IllegalCommand
    player = data["player"]
    ps = game.state.players[player]
    targets = {t["value"]: t for t in _e022_targets(game, player)}
    if value not in targets:
        raise IllegalCommand("choose.invalid", "須選擇可放回的夥伴")
    number = ps.discard.pop(value)
    slot = game.state.slot_by_uid(player, targets[value]["slot_uid"])
    slot.partner = number
    game.emit(batch, "card_played", player=player, card=number, slot=slot.uid,
              zone="partner", from_discard=True)


# E-023 戦いの目的:[持續] 所有裝夥伴的魔物 +2000(至下回合結束階段)
@reg.event("E-023")
def e023(game, batch, player, page):
    add_modifier(game, batch, kind="power_partnered", source="E-023", owner=player,
                 duration=DUR_UNTIL_END_NEXT_TURN, target_player=player, amount=2000)


# E-024 ダルタニャン教授:[持續] 本回合封鎖對手 1 隻魔物的術與效果
@reg.event("E-024", condition=lambda g, p: bool(g.state.players[1 - p].slots))
def e024(game, batch, player, page):
    opp = game.state.players[1 - player]
    options = [{"value": s.uid, "card": s.top} for s in opp.slots]
    choose_or_auto(game, batch, kind="e024_pick", player=player, options=options,
                   data={"player": player}, source="E-024")


@reg.choice_resolver("e024_pick")
def e024_pick(game, batch, value, data):
    from ..engine import IllegalCommand
    player = data["player"]
    slot = game.state.slot_by_uid(1 - player, value if isinstance(value, int) else -1)
    if slot is None:
        raise IllegalCommand("choose.invalid", "須選擇對手場上的魔物")
    add_restriction(game, batch, source="E-024", owner=player,
                    target_player=1 - player, flag=MAMODO_LOCKED, duration=DUR_TURN)
    game.state.modifiers[-1].target_slot = slot.uid


# E-025 ヨポポのダンス:[持續] 本回合對手不能套用其魔物卡效果
@reg.event("E-025")
def e025(game, batch, player, page):
    add_restriction(game, batch, source="E-025", owner=player,
                    target_player=1 - player, flag=NO_MAMODO_EFFECTS, duration=DUR_TURN)


# E-026 魚を頼んだのに!:擲2硬幣,MP = 正面數×2
@reg.event("E-026")
def e026(game, batch, player, page):
    flip_coins(game, batch, player, 2, "E-026", "e026_resolve", {"player": player})


@reg.choice_resolver("e026_resolve")
def e026_resolve(game, batch, results, data):
    from ..engine import gain_mp
    gain_mp(game, batch, data["player"], sum(results) * 2, "E-026")


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
