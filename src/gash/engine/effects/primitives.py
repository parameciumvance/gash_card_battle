"""效果原語:卡片 handler 用來組合效果的共用積木。

硬幣判定為互動式:擲出後進入擲硬幣子階段(見 flip_coins),有可用的影響硬幣效果(M-012 / M-034 / M-019)時
進入 pending 讓玩家決定,子階段結束後才呼叫 callback 繼續解決。
"""

from __future__ import annotations

from ..state import BOOK_SIZE, GAME_OVER, Modifier, PendingChoice, Standby
from . import registry as reg


# ---------------------------------------------------------------- modifier / standby

def family(game, slot) -> str:
    """場上魔物的家族名(戰術使用者、搭檔對應、家族限定效果的判定);視為另一魔物的卡依 reg.TREATED_AS(M-047)。"""
    return reg.TREATED_AS.get(slot.top) or game.db[slot.top].related_mamodo


def mamodo_name(game, slot) -> str:
    """場上魔物的名稱(「」名稱比對、同名限制);視為另一魔物的卡依 reg.TREATED_AS。"""
    return reg.TREATED_AS.get(slot.top) or game.db[slot.top].name_ja


def can_stack_on(game, number, slot) -> bool:
    """疊放魔物 number 可疊在 slot 上:卡號相符,或家族相符且 slot 頂層不是疊放型魔物(M-047)。"""
    if slot.top in reg.STACK_ON.get(number, ()):
        return True
    fam = reg.STACK_ON_FAMILY.get(number)
    return fam is not None and slot.top not in reg.STACK_ON and family(game, slot) == fam


def stack_base(game, player, number):
    """player 場上第一隻可疊放 number 的魔物;沒有時 None。"""
    return next((s for s in game.state.players[player].slots if can_stack_on(game, number, s)), None)


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


def add_spell_power(battle, side, source, amount, kind="spell_bonus"):
    """本場戰鬥中 side("attack" / "defense")所用戰術的魔力加減,連同來源卡記下(供魔力勝負明細)。
    kind:"spell_bonus"(待命或效果的加值)/ "defense_self"(戰術自身的防禦加值)。"""
    battle.data.setdefault(f"{side}_spell_power", []).append(
        {"kind": kind, "source": source, "amount": amount})


def coin_info(results) -> dict:
    """擲幣詢問的公開脈絡:目前各枚的結果(依擲出順序)。"""
    return {"results": ["heads" if r else "tails" for r in results]}


def schedule_standby(game, batch, *, kind, source, owner, data=None):
    sb = Standby(kind=kind, source=source, owner=owner,
                 created_turn=game.state.turn_no, data=data or {})
    game.state.standby.append(sb)
    # 待命指定的對象(S-098 選定的戰術)一併公開,供記錄顯示
    target = {k: sb.data[k] for k in ("card", "page") if k in sb.data}
    game.emit(batch, "standby_set", kind=kind, source=source, owner=owner, **target)
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


def turn_back_pages(game, batch, player, leaves, source) -> int:
    """效果造成的回翻,最多回到第一頁;回傳實際回翻的張數,沒有回翻時不發事件(P-019 依實際張數計)。"""
    ps = game.state.players[player]
    actual = min(leaves, max(0, (ps.pos - 2) // 2))
    if actual == 0:
        return 0
    ps.pos -= 2 * actual
    game.emit(batch, "pages_turned", player=player, count=-actual, pos=ps.pos, source=source)
    return actual


def reduce_mp(game, batch, player, amount, source) -> int:
    """減少 MP(不低於 0),回傳實際減少量。"""
    ps = game.state.players[player]
    actual = min(amount, ps.mp)
    if actual:
        ps.mp -= actual
        game.emit(batch, "mp_changed", player=player, delta=-actual, mp=ps.mp, reason=source)
    return actual


def mark_opp_mp_reduced(game, player):
    """記錄 player 本回合用了「減少對手 MP」的效果(不論實際減少多少),供 E-018 判定直前回合。"""
    st = game.state
    ps = st.players[player]
    ps.opp_mp_reduced_turns = {t for t in ps.opp_mp_reduced_turns if t >= st.turn_no - 1}
    ps.opp_mp_reduced_turns.add(st.turn_no)


def mp_guarded(game, player) -> bool:
    """player 的 MP 不會因對手的效果減少:本回合的 P-021,或戰鬥階段中場上的 P-020。"""
    st = game.state
    return (any(m.kind == "mp_guard" and m.target_player == player and m.active(st.turn_no)
                for m in st.modifiers)
            or battle_phase_mp_lock(game, player))


def battle_phase_mp_lock(game, player) -> bool:
    """戰鬥階段中,player 場上有 P-020(搭檔效果未被禁止)。「このカードが場にある→」也算使用效果,
    所以「パートナーの効果を使えない」時不生效。"""
    from ..engine import restricted
    from ..state import BATTLE, NO_PARTNER_EFFECTS
    st = game.state
    if st.phase != BATTLE or restricted(game, player, NO_PARTNER_EFFECTS):
        return False
    return any(s.partner in reg.BATTLE_PHASE_MP_LOCK for s in st.players[player].slots)


def reduce_opponent_mp(game, batch, player, amount, source) -> int:
    """player 的效果使對手 MP 減少(不低於 0),並記錄為「減少對手 MP」的效果。回傳實際減少量。
    對手受 P-021 保護時不減少(發出 mp_reduction_prevented),仍算使用了減少對手 MP 的效果。"""
    mark_opp_mp_reduced(game, player)
    if amount > 0 and mp_guarded(game, 1 - player):
        game.emit(batch, "mp_reduction_prevented", player=1 - player, source=source)
        return 0
    actual = reduce_mp(game, batch, 1 - player, amount, source)
    game.state.players[1 - player].mp_reduced_by_opponent += actual   # E-028 / E-035
    return actual


def heal_slot(game, batch, player, slot, source):
    if slot.injured:
        slot.injured = False
        game.emit(batch, "mamodo_healed", player=player, slot=slot.uid, card=slot.top, source=source)


# ---------------------------------------------------------------- 書內 / 墓地搜卡

def book_page_options(game, player, pred=None, exclude_last=False):
    """魔書中(尚未離開的)符合條件的頁位選項:[{'page': n, 'card': 卡號}]。"""
    ps = game.state.players[player]
    opts = []
    for page in range(1, BOOK_SIZE + 1):
        if page in ps.consumed_pages:
            continue
        if exclude_last and page == BOOK_SIZE:
            continue
        number = ps.card_at(page)
        if pred is None or pred(page, game.db[number]):
            opts.append(page_option(player, page, number))
    return opts


def take_from_book(game, batch, player, page) -> str:
    """卡片離開魔書(該頁標記空缺),回傳卡號;上場/棄置由呼叫端接續。"""
    ps = game.state.players[player]
    ps.consumed_pages.add(page)
    return ps.card_at(page)


def return_to_book(game, batch, player, number, page):
    """自墓地等處把卡放回魔書的空缺頁(M-025)。"""
    ps = game.state.players[player]
    assert page in ps.consumed_pages, "只能放回空缺頁"
    ps.book[page - 1] = number
    ps.consumed_pages.discard(page)
    game.emit(batch, "card_returned_to_book", player=player, card=number, page=page)


def play_mamodo_from_book(game, batch, player, page):
    """效果指示:自魔書任意頁放出魔物(受場上上限/同名上限約束,不合法時無效果)。"""
    from ..engine import MAX_FIELD_MAMODO, same_name_copies
    from ..state import MamodoSlot, place_slot
    ps = game.state.players[player]
    number = ps.card_at(page)
    card = game.db[number]
    if len(ps.slots) >= MAX_FIELD_MAMODO:
        return None
    if same_name_copies(game, player, card) >= reg.MAX_COPIES.get(number, 1):
        return None
    take_from_book(game, batch, player, page)
    slot = MamodoSlot(uid=game.state.next_uid(), stack=[number])
    place_slot(ps.slots, slot)
    game.emit(batch, "card_played", player=player, card=number, slot=slot.uid,
              zone="mamodo", from_book=True)
    run_on_play(game, batch, player, slot, number)
    return slot


def run_on_play(game, batch, player, slot, number):
    """卡片放上場(放出、疊放、自魔書放出或裝備)後:先執行專用規則(RULE_ON_PLAY,M-047 的定時離場),
    再執行「このカードが場に出たとき」的效果(ON_PLAY,放上場當下被「使えない」擋下時不執行、事後不補發)。
    所有放上場的路徑都經過這裡。"""
    if number in reg.RULE_ON_PLAY:
        reg.RULE_ON_PLAY[number](game, batch, player, slot)
    from ..engine import note_effect_blocked
    if number in reg.ON_PLAY and not note_effect_blocked(game, batch, player, slot, number, "play"):
        reg.ON_PLAY[number](game, batch, player, slot)


def attach_partner_from_book(game, batch, player, page, slot):
    """效果指示:自魔書任意頁取搭檔卡裝備到指定魔物(已有搭檔時無效果)。"""
    if slot.partner is not None:
        return False
    number = take_from_book(game, batch, player, page)
    slot.partner = number
    game.emit(batch, "card_played", player=player, card=number, slot=slot.uid,
              zone="partner", from_book=True)
    run_on_play(game, batch, player, slot, number)
    return True


def discard_from_book(game, batch, owner, page, source):
    """把魔書中某頁的卡棄掉(E-016/E-017 對對手書)。"""
    from ..engine import to_discard
    ps = game.state.players[owner]
    number = take_from_book(game, batch, owner, page)
    to_discard(ps, number)
    game.emit(batch, "card_discarded", player=owner, card=number, zone="book",
              page=page, reason=source)
    return number


def partner_discard_guarded(game, player, slot) -> bool:
    """player 的這隻魔物身上的搭檔不會被對手的效果棄掉(M-049;魔物的效果被禁止時不生效)。"""
    from ..engine import mamodo_effect_block
    return slot.top in reg.PARTNER_DISCARD_GUARD and not mamodo_effect_block(game, player, slot)


def discard_partner(game, batch, player, slot, source):
    """把場上魔物所裝的搭檔卡棄掉。"""
    from ..engine import to_discard
    if not slot.partner:
        return None
    number = slot.partner
    slot.partner = None
    to_discard(game.state.players[player], number)
    game.emit(batch, "card_discarded", player=player, card=number, zone="partner", reason=source,
              slot=slot.uid)
    return number


# ---------------------------------------------------------------- 「自分の魔本をめくる/もどす」効果(P-010/P-018 條款)

def own_book_turn_effect(game, batch, player, leaves, source) -> bool:
    """「翻自己魔書」的效果(leaves < 0 為回翻)。記錄本回合用過該方向的效果;本回合已受
    P-010 / P-018 的「合計1回」限制時不發生(限制卡本身已算 1 次),回傳是否有翻頁。"""
    ps = game.state.players[player]
    back = leaves < 0
    if ps.page_back_effect_limited if back else ps.page_effect_limited:
        game.emit(batch, "page_turn_restricted", player=player, count=leaves, source=source)
        return False
    if back:
        if not turn_back_pages(game, batch, player, -leaves, source):
            return False                  # 已在第一頁:沒有回翻,不算用過
        ps.page_back_effect_used = True
    else:
        ps.page_effect_used = True
        turn_pages(game, batch, player, leaves, source)
    return True


def own_page_turn_effect(game, batch, player, leaves, source):
    """P-010:翻自己的魔書,之後本回合的「翻自己魔書」效果合計只能 1 次。"""
    own_book_turn_effect(game, batch, player, leaves, source)
    game.state.players[player].page_effect_limited = True


def own_page_turnback_effect(game, batch, player, leaves, source):
    """P-018:回翻自己的魔書,之後本回合的「回翻自己魔書」效果合計只能 1 次。"""
    own_book_turn_effect(game, batch, player, -leaves, source)
    game.state.players[player].page_back_effect_limited = True


# ---------------------------------------------------------------- 選項的位置

# 目標為卡片的選項標示卡片所在位置(zone / player / 定位欄位),前端據此在畫面上的位置選擇;
# value 是決策指令的值,不受位置欄位影響。extra 為呼叫端的附加欄位(例如 slot_uid),不可覆寫位置欄位。

def slot_option(player, slot, card=None, **extra):
    """場上魔物槽;card 預設為魔物本身,目標是搭檔時傳 slot.partner。"""
    return {**extra, "value": slot.uid, "card": card or slot.top,
            "zone": "slot", "player": player, "slot": slot.uid}


def page_option(player, page, card=None, **extra):
    """魔書的頁;card 為 None 時(空頁)不帶卡號。"""
    opt = {**extra, "value": page, "page": page, "zone": "book", "player": player}
    if card is not None:
        opt["card"] = card
    return opt


def discard_option(player, index, card, **extra):
    """棄牌區第 index 張。"""
    return {**extra, "value": index, "card": card, "zone": "discard", "player": player, "index": index}


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

def _reflip_slot(game, player, coins):
    """player 場上可用的擲幣重擲魔物槽(coins:"self" 重擲自己擲的 / "opponent" 令對手重擲);沒有時 None。
    重擲是「魔物の効果」:每回合一次,受「魔物の効果」全體限制(E-025)與個別封鎖(E-024)。"""
    from ..engine import mamodo_effect_block
    ps = game.state.players[player]
    return next((s for s in ps.slots
                 if reg.COIN_REFLIP.get(s.top) == coins
                 and f"mamodo:{s.top}" not in ps.used_abilities
                 and not mamodo_effect_block(game, player, s)), None)


def _use_reflip(game, batch, player, slot):
    """記錄使用擲幣重擲(每回合一次)並發出使用事件。"""
    game.state.players[player].used_abilities.add(f"mamodo:{slot.top}")
    game.emit(batch, "ability_used", player=player, card=slot.top, slot=slot.uid, zone="mamodo")


def flip_coins(game, batch, player, count, source, callback, data=None):
    """由 player 擲 count 次硬幣;擲硬幣子階段結束後呼叫 CHOICE_RESOLVERS[callback](game, batch, results, data)。

    擲硬幣子階段(game-engine「擲硬幣子階段」):擲幣者先有機會使用影響硬幣結果的效果(M-012 重擲 1 枚、
    M-034 把 1 枚反面改成正面,決策 coin_confirm),之後輪到對手(M-019 令擲幣者重擲 1 枚,決策 opp_coin_redo),
    雙方輪替;使用效果後換另一方,雙方連續不使用時結束。沒有可用效果的一方自動不使用。
    這些效果不經行動流程(不改行動權),也不提供ジャマー的回應(官方規則書第 47 頁 Q&A)。

    擲幣者記在 data["flipper"]。呼叫端放進 data 的 "player" 會原樣保留(E-020 由對手擲幣,
    callback 需要的是效果擁有者);沒有放時才預設為擲幣者。"""
    results = []
    for _ in range(count):
        heads = game.rng.random() < 0.5
        results.append(heads)
        game.emit(batch, "coin_flipped", player=player,
                  result="heads" if heads else "tails", source=source)
    data = dict(data or {})
    data.setdefault("player", player)
    data.update({"results": results, "callback": callback, "flipper": player, "source": source,
                 "coin_turn": player, "coin_passes": 0})
    _coin_subphase(game, batch, data)


def _set_heads_slot(game, player):
    """player 場上可用的「把自己擲的硬幣改成正面」魔物槽(M-034;魔物の効果,受限制);沒有時 None。"""
    from ..engine import mamodo_effect_block
    return next((s for s in game.state.players[player].slots
                 if s.top in reg.COIN_SET_HEADS and not mamodo_effect_block(game, player, s)), None)


def _flipper_options(game, player, results):
    """擲幣者的機會:不使用;M-012 可用時每枚可重擲;M-034 可用時每枚反面可改成正面。沒有可用效果時 None。"""
    options = [{"value": None, "label": "keep"}]
    if _reflip_slot(game, player, "self") is not None:
        options += [{"value": i, "label": "reflip"} for i in range(len(results))]
    if _set_heads_slot(game, player) is not None:
        options += [{"value": f"heads:{i}", "label": "set_heads", "coin": i}
                    for i, r in enumerate(results) if not r]
    return options if len(options) > 1 else None


def _opponent_options(game, player, results):
    """擲幣者對手的機會:不使用;M-019 可用時每枚可令擲幣者重擲。沒有可用效果時 None。"""
    if _reflip_slot(game, player, "opponent") is None:
        return None
    return [{"value": None, "label": "keep"}] + [{"value": i, "label": "opp_reflip"}
                                                  for i in range(len(results))]


def _subphase_options(game, data):
    who = data["coin_turn"]
    if who == data["flipper"]:
        return "coin_confirm", _flipper_options(game, who, data["results"])
    return "opp_coin_redo", _opponent_options(game, who, data["results"])


def _coin_subphase(game, batch, data):
    """輪到的一方有可用效果時建立決策並停下;雙方連續不使用時結束並呼叫 callback。"""
    while data["coin_passes"] < 2:
        kind, options = _subphase_options(game, data)
        if options is not None:
            player = data["coin_turn"]
            game.state.pending = PendingChoice(
                kind=kind, player=player, source=data["source"], options=options,
                data=data, info=coin_info(data["results"]))
            game.emit(batch, "choice_required", kind=kind, player=player,
                      results=["heads" if r else "tails" for r in data["results"]])
            return
        _next_turn(data, used=False)
    reg.CHOICE_RESOLVERS[data["callback"]](game, batch, data["results"], data)


def _next_turn(data, used):
    data["coin_passes"] = 0 if used else data["coin_passes"] + 1
    data["coin_turn"] = 1 - data["coin_turn"]


def _reflip_one(game, batch, data, index):
    heads = game.rng.random() < 0.5
    data["results"][index] = heads
    game.emit(batch, "coin_flipped", player=data["flipper"],
              result="heads" if heads else "tails", source=data["source"], reflip=True)


def _check_subphase_choice(game, value, data):
    from ..engine import IllegalCommand
    _kind, options = _subphase_options(game, data)
    if value is None or value not in {o["value"] for o in (options or [])}:
        raise IllegalCommand("choose.invalid", "無效的擲幣選擇")


@reg.choice_resolver("opp_coin_redo")
def _opp_coin_redo(game, batch, value, data):
    """擲幣者對手的機會:不使用,或以 M-019 令擲幣者重擲選定的 1 枚。"""
    if value is not None:
        _check_subphase_choice(game, value, data)
        opp = data["coin_turn"]
        _use_reflip(game, batch, opp, _reflip_slot(game, opp, "opponent"))
        _reflip_one(game, batch, data, value)
    game.state.pending = None
    _next_turn(data, used=value is not None)
    _coin_subphase(game, batch, data)


@reg.choice_resolver("coin_confirm")
def _coin_confirm(game, batch, value, data):
    """擲幣者的機會:不使用,M-012 重擲選定的 1 枚,或 M-034 把選定的反面改成正面。"""
    from ..engine import _discard_slot
    player = data["flipper"]
    if value is not None:
        _check_subphase_choice(game, value, data)
        if isinstance(value, str):   # M-034:棄掉自己,把指定的反面硬幣改成正面
            index = int(value.split(":")[1])
            slot = _set_heads_slot(game, player)
            game.emit(batch, "ability_used", player=player, card=slot.top, slot=slot.uid, zone="mamodo")
            _discard_slot(game, batch, player, slot, reason="cost")
            data["results"][index] = True
            game.emit(batch, "coin_set", player=player, index=index, result="heads", card=slot.top,
                      source=data["source"])
        else:
            _use_reflip(game, batch, player, _reflip_slot(game, player, "self"))
            _reflip_one(game, batch, data, value)
    game.state.pending = None
    _next_turn(data, used=value is not None)
    _coin_subphase(game, batch, data)
