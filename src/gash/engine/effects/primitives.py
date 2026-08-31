"""效果原語:卡片 handler 用來組合效果的共用積木。

硬幣判定為互動式:擲出後若玩家場上有可用的 M-012(凱喬美《幸運兒》),
會進入 pending 讓玩家決定是否重擲,確定後才呼叫 callback 繼續解決。
"""

from __future__ import annotations

from ..state import BOOK_SIZE, GAME_OVER, Modifier, PendingChoice, Standby
from . import registry as reg


# ---------------------------------------------------------------- modifier / standby

def add_modifier(game, batch, *, kind, source, owner, duration,
                 target_player=None, target_slot=None, amount=0, flag=None, data=None):
    m = Modifier(kind=kind, source=source, owner=owner, duration=duration,
                 created_turn=game.state.turn_no, target_player=target_player,
                 target_slot=target_slot, amount=amount, flag=flag, data=data or {})
    game.state.modifiers.append(m)
    game.emit(batch, "modifier_added", kind=kind, source=source,
              target_player=target_player, target_slot=target_slot,
              amount=amount, flag=flag, duration=duration)
    return m


def add_power(game, batch, *, source, owner, target_player, target_slot, amount, duration):
    return add_modifier(game, batch, kind="power", source=source, owner=owner,
                        duration=duration, target_player=target_player,
                        target_slot=target_slot, amount=amount)


def add_restriction(game, batch, *, source, owner, target_player, flag, duration):
    return add_modifier(game, batch, kind="restriction", source=source, owner=owner,
                        duration=duration, target_player=target_player, flag=flag)


def schedule_standby(game, batch, *, kind, source, owner, data=None):
    sb = Standby(kind=kind, source=source, owner=owner,
                 created_turn=game.state.turn_no, data=data or {})
    game.state.standby.append(sb)
    game.emit(batch, "standby_set", kind=kind, source=source, owner=owner)
    return sb


# ---------------------------------------------------------------- 翻頁 / MP / 回復

def turn_pages(game, batch, player, leaves, source):
    """效果造成的翻頁(1 張 = 1 對頁),不獲得 MP。翻完即敗。"""
    from ..engine import _game_over
    ps = game.state.players[player]
    ps.pos += 2 * leaves
    game.emit(batch, "pages_turned", player=player, count=leaves, pos=min(ps.pos, BOOK_SIZE + 2), source=source)
    if ps.book_exhausted():
        _game_over(game, batch, winner=1 - player, reason="book_out")


def turn_back_pages(game, batch, player, leaves, source):
    ps = game.state.players[player]
    ps.pos = max(2, ps.pos - 2 * leaves)
    game.emit(batch, "pages_turned", player=player, count=-leaves, pos=ps.pos, source=source)


def reduce_mp(game, batch, player, amount, source) -> int:
    """減少 MP(不低於 0),回傳實際減少量。"""
    ps = game.state.players[player]
    actual = min(amount, ps.mp)
    if actual:
        ps.mp -= actual
        game.emit(batch, "mp_changed", player=player, delta=-actual, mp=ps.mp, reason=source)
    return actual


def heal_slot(game, batch, player, slot, source):
    if slot.injured:
        slot.injured = False
        game.emit(batch, "mamodo_healed", player=player, slot=slot.uid, card=slot.top, source=source)


# ---------------------------------------------------------------- 書內 / 墓地搜卡

def book_page_options(game, player, pred=None, exclude_last=False):
    """魔本中(尚未離開的)符合條件的頁位選項:[{'page': n, 'card': 卡號}]。"""
    ps = game.state.players[player]
    opts = []
    for page in range(1, BOOK_SIZE + 1):
        if page in ps.consumed_pages:
            continue
        if exclude_last and page == BOOK_SIZE:
            continue
        number = ps.card_at(page)
        if pred is None or pred(page, game.db[number]):
            opts.append({"page": page, "card": number, "value": page})
    return opts


def take_from_book(game, batch, player, page) -> str:
    """卡片離開魔本(該頁標記空缺),回傳卡號;上場/棄置由呼叫端接續。"""
    ps = game.state.players[player]
    ps.consumed_pages.add(page)
    return ps.card_at(page)


def return_to_book(game, batch, player, number, page):
    """自墓地等處把卡放回魔本的空缺頁(M-025)。"""
    ps = game.state.players[player]
    assert page in ps.consumed_pages, "只能放回空缺頁"
    ps.book[page - 1] = number
    ps.consumed_pages.discard(page)
    game.emit(batch, "card_returned_to_book", player=player, card=number, page=page)


def play_mamodo_from_book(game, batch, player, page):
    """效果指示:自魔本任意頁放出魔物(受場上上限/同名上限約束,不合法時無效果)。"""
    from ..engine import MAX_FIELD_MAMODO, same_name_copies
    from ..state import MamodoSlot
    ps = game.state.players[player]
    number = ps.card_at(page)
    card = game.db[number]
    if len(ps.slots) >= MAX_FIELD_MAMODO:
        return None
    if same_name_copies(game, player, card) >= reg.MAX_COPIES.get(number, 1):
        return None
    take_from_book(game, batch, player, page)
    slot = MamodoSlot(uid=game.state.next_uid(), stack=[number])
    ps.slots.append(slot)
    game.emit(batch, "card_played", player=player, card=number, slot=slot.uid,
              zone="mamodo", from_book=True)
    if number in reg.ON_PLAY:
        reg.ON_PLAY[number](game, batch, player, slot)
    return slot


def attach_partner_from_book(game, batch, player, page, slot):
    """效果指示:自魔本任意頁取夥伴卡裝備到指定魔物(已有夥伴時無效果)。"""
    if slot.partner is not None:
        return False
    number = take_from_book(game, batch, player, page)
    slot.partner = number
    game.emit(batch, "card_played", player=player, card=number, slot=slot.uid,
              zone="partner", from_book=True)
    if number in reg.ON_PLAY:
        reg.ON_PLAY[number](game, batch, player, slot)
    return True


def discard_from_book(game, batch, owner, page, source):
    """把魔本中某頁的卡棄掉(E-016/E-017 對對手書)。"""
    from ..engine import to_discard
    ps = game.state.players[owner]
    number = take_from_book(game, batch, owner, page)
    to_discard(ps, number)
    game.emit(batch, "card_discarded", player=owner, card=number, zone="book",
              page=page, reason=source)
    return number


def discard_partner(game, batch, player, slot, source):
    """把場上魔物所裝的夥伴卡棄掉。"""
    from ..engine import to_discard
    if not slot.partner:
        return None
    number = slot.partner
    slot.partner = None
    to_discard(game.state.players[player], number)
    game.emit(batch, "card_discarded", player=player, card=number, zone="partner", reason=source)
    return number


# ---------------------------------------------------------------- 翻頁「效果」每回合一次(P-010/P-018 條款)

def own_page_turn_effect(game, batch, player, leaves, source):
    ps = game.state.players[player]
    ps.page_effect_used = True
    turn_pages(game, batch, player, leaves, source)


def own_page_turnback_effect(game, batch, player, leaves, source):
    ps = game.state.players[player]
    ps.page_back_effect_used = True
    turn_back_pages(game, batch, player, leaves, source)


# ---------------------------------------------------------------- 選擇

def choose_or_auto(game, batch, *, kind, player, options, data=None, source=None):
    """單一選項自動解決;多選項進入 pending。options: [{'value': ..., ...}]"""
    data = data or {}
    if len(options) == 1:
        reg.CHOICE_RESOLVERS[kind](game, batch, options[0]["value"], data)
        return
    game.state.pending = PendingChoice(kind=kind, player=player, options=options,
                                       source=source, data=data)
    game.emit(batch, "choice_required", kind=kind, player=player, options=options)


# ---------------------------------------------------------------- 互動式硬幣

def _reflip_available(game, player) -> bool:
    ps = game.state.players[player]
    return (any(s.top == "M-012" for s in ps.slots)
            and "mamodo:M-012" not in ps.used_abilities)


def _opp_redo_available(game, opp) -> bool:
    """M-019 凱喬美《奇妙動物》:宣告使用→對手重擲(每回合一次)。"""
    from ..engine import restricted, slot_restricted
    from ..state import MAMODO_LOCKED, NO_MAMODO_EFFECTS
    ps = game.state.players[opp]
    slot = next((s for s in ps.slots if s.top == "M-019"), None)
    if slot is None or "mamodo:M-019" in ps.used_abilities:
        return False
    if restricted(game, opp, NO_MAMODO_EFFECTS):
        return False
    return not slot_restricted(game, opp, MAMODO_LOCKED, slot.uid)


def flip_coins(game, batch, player, count, source, callback, data=None):
    """擲 count 次硬幣;結果確定後呼叫 CHOICE_RESOLVERS[callback](game, batch, results, data)。
    確認鏈:對手可用 M-019 時先問是否令整組重擲;玩家有可用 M-012 時再進重擲確認。"""
    results = []
    for _ in range(count):
        heads = game.rng.random() < 0.5
        results.append(heads)
        game.emit(batch, "coin_flipped", player=player,
                  result="heads" if heads else "tails", source=source)
    data = dict(data or {})
    data.update({"results": results, "callback": callback, "player": player, "source": source})
    _coin_confirm_chain(game, batch, data)


def _coin_confirm_chain(game, batch, data):
    player = data["player"]
    results = data["results"]
    source = data["source"]
    opp = 1 - player
    if not data.get("m019_done") and _opp_redo_available(game, opp):
        game.state.pending = PendingChoice(
            kind="opp_coin_redo", player=opp, source="M-019",
            options=[{"value": None, "label": "keep"}, {"value": True, "label": "pay_reflip"}],
            data=data)
        game.emit(batch, "choice_required", kind="opp_coin_redo", player=opp,
                  results=["heads" if r else "tails" for r in results])
        return
    if _reflip_available(game, player):
        game.state.pending = PendingChoice(
            kind="coin_confirm", player=player, source=source,
            options=[{"value": None, "label": "keep"}]
            + [{"value": i, "label": "reflip"} for i in range(len(results))],
            data=data)
        game.emit(batch, "choice_required", kind="coin_confirm", player=player,
                  results=["heads" if r else "tails" for r in results])
        return
    reg.CHOICE_RESOLVERS[data["callback"]](game, batch, results, data)


@reg.choice_resolver("opp_coin_redo")
def _opp_coin_redo(game, batch, value, data):
    opp = 1 - data["player"]
    data["m019_done"] = True
    game.state.pending = None
    if value:
        ps = game.state.players[opp]
        ps.used_abilities.add("mamodo:M-019")
        game.emit(batch, "ability_used", player=opp, card="M-019",
                  slot=next(s.uid for s in ps.slots if s.top == "M-019"), zone="mamodo")
        for i in range(len(data["results"])):
            heads = game.rng.random() < 0.5
            data["results"][i] = heads
            game.emit(batch, "coin_flipped", player=data["player"],
                      result="heads" if heads else "tails", source=data["source"], reflip=True)
    _coin_confirm_chain(game, batch, data)


@reg.choice_resolver("coin_confirm")
def _coin_confirm(game, batch, value, data):
    from ..engine import IllegalCommand
    player = data["player"]
    results = data["results"]
    if value is None:
        game.state.pending = None
        reg.CHOICE_RESOLVERS[data["callback"]](game, batch, results, data)
        return
    if not isinstance(value, int) or not 0 <= value < len(results):
        raise IllegalCommand("choose.invalid", "無效的重擲選擇")
    if not _reflip_available(game, player):
        raise IllegalCommand("choose.invalid", "M-012 的效果已不可使用")
    ps = game.state.players[player]
    ps.used_abilities.add("mamodo:M-012")
    game.emit(batch, "ability_used", player=player, card="M-012",
              slot=next(s.uid for s in ps.slots if s.top == "M-012"), zone="mamodo")
    heads = game.rng.random() < 0.5
    results[value] = heads
    game.emit(batch, "coin_flipped", player=player,
              result="heads" if heads else "tails", source=data["source"], reflip=True)
    game.state.pending = None
    if _reflip_available(game, player):
        game.state.pending = PendingChoice(
            kind="coin_confirm", player=player, source=data["source"],
            options=[{"value": None, "label": "keep"}]
            + [{"value": i, "label": "reflip"} for i in range(len(results))],
            data=data)
        game.emit(batch, "choice_required", kind="coin_confirm", player=player,
                  results=["heads" if r else "tails" for r in results])
        return
    reg.CHOICE_RESOLVERS[data["callback"]](game, batch, results, data)
