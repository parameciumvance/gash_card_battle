"""遊戲引擎:指令進 → 驗證 → 狀態轉移 → 事件列表出。

規則依據 ref/raw/rule3.md。所有非法指令拋出 IllegalCommand(code),狀態不變。
"""

from __future__ import annotations

import copy
import random

from .cards import EVENT, MAMODO, PARTNER, SPELL, CardDef, card_db
from .effects import registry as reg
from .effects.primitives import add_spell_power, page_option, slot_option
from .state import (
    BATTLE, BOOK_SIZE, DUR_BATTLE, DUR_NEXT_TURN, DUR_TURN, DUR_UNTIL_END_NEXT_TURN,
    GAME_OVER, MAMODO_LOCKED, MAX_FIELD_MAMODO, NO_ATTACK_SPELL, NO_DEFENSE,
    NO_MAMODO_EFFECTS, NO_PARTNER_EFFECTS, NO_PROTECT_BOOK,
    NO_SPELLS, SETUP, START, STEP_DEFENSE, STEP_EFFECTS,
    BattleState, Game, GameState, MamodoSlot, Modifier, PendingChoice, PlayerState, Standby,
)


class IllegalCommand(Exception):
    def __init__(self, code: str, message: str = ""):
        super().__init__(f"{code}{': ' + message if message else ''}")
        self.code = code


# ---------------------------------------------------------------- 建立對局

def new_game(deck_pages: list[str] | tuple[str, ...], seed: int | None = None,
             db: dict[str, CardDef] | None = None,
             decks: tuple[list[str], list[str]] | None = None) -> Game:
    """準備階段:雙方放出第 1 頁魔物、翻開第 2-3 頁(MP+2)、擲硬幣決定先攻。"""
    db = db or card_db()
    books = decks or (list(deck_pages), list(deck_pages))
    players = [PlayerState(book=list(b)) for b in books]
    game = Game(state=GameState(players=players), rng=random.Random(seed), db=db)
    batch: list[dict] = []
    game.emit(batch, "game_started")

    for p in (0, 1):
        ps = players[p]
        number = ps.card_at(1)
        slot = MamodoSlot(uid=game.state.next_uid(), stack=[number])
        ps.slots.append(slot)
        ps.consumed_pages.add(1)
        game.emit(batch, "card_played", player=p, card=number, slot=slot.uid, zone="mamodo")
        if number in reg.ON_PLAY:
            reg.ON_PLAY[number](game, batch, p, slot)
    for p in (0, 1):
        players[p].pos = 2
        players[p].mp = 2
        game.emit(batch, "pages_flipped", player=p, count=1, pos=2, mp_gained=2)

    first = game.rng.randint(0, 1)
    game.state.turn_player = first
    game.state.phase = START
    game.emit(batch, "coin_flipped", player=first, result="first_player", source="setup")
    game.emit(batch, "turn_started", turn=1, player=first)
    return game


# ---------------------------------------------------------------- 共用查詢

def slot_power(game: Game, player: int, slot: MamodoSlot) -> int:
    return power_breakdown(game, player, slot)[0]


def _item(kind: str, source: str | None, amount: int) -> dict:
    return {"kind": kind, "source": source, "amount": amount}


def power_breakdown(game: Game, player: int, slot: MamodoSlot) -> tuple[int, list[dict]]:
    """魔物魔力與逐項明細;各項 amount 加總恆等於魔力(「視為 0」「不低於 0」寫成調整項)。"""
    st = game.state
    items = [_item("mamodo", slot.top, game.db[slot.top].power_base or 0)]
    for number, fn in reg.STATIC_POWER.items():
        for s in st.players[player].slots:
            if s.top == number:
                amount = fn(game, player, slot)
                if amount:
                    items.append(_item("static", number, amount))
                break
    for m in st.modifiers:
        if (m.kind == "power" and m.active(st.turn_no)
                and m.target_player == player and m.target_slot == slot.uid):
            items.append(_item("modifier", m.source, m.amount))
        # E-023:所有裝有搭檔的魔物 +N
        if (m.kind == "power_partnered" and m.active(st.turn_no)
                and m.target_player == player and slot.partner):
            items.append(_item("partnered", m.source, m.amount))
    raw = sum(i["amount"] for i in items)
    # P-011:魔力視為 0(優先於一切加成)
    zero = next((m for m in st.modifiers
                 if m.kind == "power_zero" and m.active(st.turn_no)
                 and m.target_player == player and m.target_slot == slot.uid), None)
    if zero is not None:
        items.append(_item("power_zero", zero.source, -raw))
        return 0, items
    if raw < 0:  # S-033 等減值效果不使魔力低於 0
        items.append(_item("mamodo_floor", None, -raw))
    return max(0, raw), items


def restricted(game: Game, player: int, flag: str) -> bool:
    return any(
        m.kind == "restriction" and m.flag == flag and m.target_player == player
        and m.active(game.state.turn_no)
        for m in game.state.modifiers
    )


def slot_restricted(game: Game, player: int, flag: str, slot_uid: int) -> bool:
    """指定魔物槽的禁止旗標(E-024 mamodo_locked)。"""
    return any(
        m.kind == "restriction" and m.flag == flag and m.target_player == player
        and m.target_slot == slot_uid and m.active(game.state.turn_no)
        for m in game.state.modifiers
    )


def _full_immune(game: Game, player: int) -> bool:
    """S-037/038/041:自己魔書與所有魔物本回合不受傷害與負傷。"""
    return any(m.kind == "full_immune" and m.target_player == player
               and m.active(game.state.turn_no) for m in game.state.modifiers)


def spell_cost(game: Game, player: int, page: int, card: CardDef, slot: MamodoSlot | None = None,
               *, discount: bool = True) -> int:
    """戰術卡費用。「某魔物的戰術」類的費用效果(P-005 / M-008)以「使用戰術的魔物」判定,指令戰術由該魔物
    使用時也適用。slot 為使用的魔物;未指定時(畫面顯示、非戰鬥戰術)取自己場上可使用此戰術的魔物中最低的費用。
    discount=False 時不計可選的減費(M-008「1低いコストで使うことができる」選擇不使用時)。"""
    if slot is not None:
        return _spell_cost_by(game, player, page, card, game.db[slot.top].related_mamodo, discount)
    users = [s for s in game.state.players[player].slots
             if card.is_command_spell or _spell_usable_by(game, player, s, card)]
    if not users:
        return _spell_cost_by(game, player, page, card, None, discount)
    return min(_spell_cost_by(game, player, page, card, game.db[s.top].related_mamodo, discount)
               for s in users)


def _base_spell_cost_by(game: Game, player: int, page: int, card: CardDef, mamodo_name: str | None) -> int:
    """「本来のコスト」:印刷費用,經最後一頁(ADV)與 P-005「本来のコストを0にする」調整。"""
    ps = game.state.players[player]
    cost = card.cost or 0
    if page == BOOK_SIZE and ps.pos == BOOK_SIZE:
        cost = 0  # ADV:最後一頁的戰術本來費用為 0
    for m in game.state.modifiers:
        if (m.kind == "spell_cost_zero" and m.target_player == player
                and m.active(game.state.turn_no)
                and mamodo_name is not None and mamodo_name == m.data.get("mamodo")):
            cost = 0
    return cost


def _spell_bonus_standbys(game: Game, player: int, mamodo_name: str | None) -> list[Standby]:
    return [sb for sb in game.state.standby
            if sb.kind == "spell_bonus" and sb.owner == player
            and mamodo_name is not None and mamodo_name == sb.data.get("mamodo")]


def _spell_cost_by(game: Game, player: int, page: int, card: CardDef, mamodo_name: str | None,
                   discount: bool = True) -> int:
    cost = _base_spell_cost_by(game, player, page, card, mamodo_name)
    for sb in _spell_bonus_standbys(game, player, mamodo_name):
        if discount or not sb.data.get("optional"):
            cost += sb.data.get("cost_delta", 0)
    return max(0, cost)


def _optional_discount(game: Game, player: int, page: int, card: CardDef, slot: MamodoSlot) -> bool:
    """M-008:使用的魔物有可選的減費待命,且「本来のコスト」至少 1(本来為 0 時無法「1低いコスト」)。"""
    mamodo_name = game.db[slot.top].related_mamodo
    return (any(sb.data.get("optional") for sb in _spell_bonus_standbys(game, player, mamodo_name))
            and _base_spell_cost_by(game, player, page, card, mamodo_name) >= 1)


def pay_mp(game: Game, batch: list[dict], player: int, amount: int, reason: str) -> None:
    if amount == 0:
        return
    ps = game.state.players[player]
    ps.mp -= amount
    game.emit(batch, "mp_changed", player=player, delta=-amount, mp=ps.mp, reason=reason)


def gain_mp(game: Game, batch: list[dict], player: int, amount: int, reason: str) -> None:
    if amount == 0:
        return
    ps = game.state.players[player]
    ps.mp += amount
    game.emit(batch, "mp_changed", player=player, delta=amount, mp=ps.mp, reason=reason)


def flip_coin(game: Game, batch: list[dict], player: int, source: str) -> bool:
    result = game.rng.random() < 0.5
    game.emit(batch, "coin_flipped", player=player, result="heads" if result else "tails", source=source)
    return result


def mamodo_in_play_count(game: Game, player: int) -> int:
    return len(game.state.players[player].slots)


def same_name_copies(game: Game, player: int, card: CardDef) -> int:
    return sum(
        1
        for s in game.state.players[player].slots
        for n in ([s.top] if card.type == MAMODO else ([s.partner] if s.partner else []))
        if game.db[n].name_ja == card.name_ja
    )


def same_name_in_play(game: Game, player: int, card: CardDef) -> bool:
    return same_name_copies(game, player, card) > 0


def to_discard(ps: PlayerState, number: str) -> None:
    """入墓統一入口:同時記錄「本回合入墓」(E-022 等效果查詢)。"""
    ps.discard.append(number)
    ps.discarded_this_turn.append(number)


# ---------------------------------------------------------------- 指令入口

def submit(game: Game, command: dict) -> list[dict]:
    st = game.state
    if st.phase == GAME_OVER:
        raise IllegalCommand("game.over", "對局已結束")
    ctype = command.get("type")
    player = command.get("player")
    if player not in (0, 1):
        raise IllegalCommand("command.player", "指令須帶 player 欄位(0/1)")
    batch: list[dict] = []

    if st.pending is not None:
        if ctype != "choose" or player != st.pending.player:
            raise IllegalCommand("choice.required", "等待玩家決策中")
        _handle_choose(game, batch, command)
        _offer_jammer_if_ready(game, batch)
        return batch

    if ctype == "choose":
        raise IllegalCommand("choice.none", "目前沒有待決策事項")

    if st.phase == START:
        if ctype != "flip_pages":
            raise IllegalCommand("phase.start", "開始階段只能翻頁(flip_pages 0-3)")
        _flip_pages(game, batch, player, command)
        return batch

    if st.phase != BATTLE:
        raise IllegalCommand("phase.invalid", f"目前階段 {st.phase} 不可行動")

    # --- 戰鬥中 ---
    if st.battle is not None:
        _battle_command(game, batch, player, command)
        return batch

    # --- 戰鬥開始確認中:僅非回合玩家可回應 ---
    if st.battle_in is not None:
        _battle_in_response(game, batch, player, command)
        return batch

    # --- 非戰鬥中 ---
    if player != st.action_player:
        raise IllegalCommand("priority.other", "現在不是你的行動時機")
    if ctype == "pass":
        st.consecutive_passes += 1
        game.emit(batch, "passed", player=player)
        if st.consecutive_passes >= 2:
            _end_phase(game, batch)
        else:
            st.action_player = 1 - player
        return batch
    _do_action(game, batch, player, command)
    st.consecutive_passes = 0
    # 行動後優先權交替(宣告攻擊除外;pending 決策不影響輪替,決策期間指令本就被擋)
    if st.battle_in is None and st.battle is None:
        st.action_player = 1 - player
    return batch


# ---------------------------------------------------------------- 開始階段

def _flip_pages(game: Game, batch: list[dict], player: int, command: dict) -> None:
    st = game.state
    if player != st.turn_player:
        raise IllegalCommand("priority.turn", "只有回合玩家能在開始階段翻頁")
    count = command.get("count")
    if not isinstance(count, int) or not 0 <= count <= 3:
        raise IllegalCommand("flip.count", "開始階段最多翻 3 張")
    ps = st.players[player]
    if ps.pos + 2 * count > BOOK_SIZE:
        raise IllegalCommand("flip.too_far", "不能翻超過魔書最後一頁")
    if count:
        ps.pos += 2 * count
        gained = 2 * count
        ps.mp += gained
        game.emit(batch, "pages_flipped", player=player, count=count, pos=ps.pos, mp_gained=gained)
    # 開始階段效果解決(翻頁之後)
    for number, fn in list(reg.START_PHASE.items()):
        for slot in list(ps.slots):
            if slot.top == number:
                fn(game, batch, player, slot)
    for sb in [s for s in st.standby if s.kind == "start_phase" and s.created_turn < st.turn_no]:
        st.standby.remove(sb)
        reg.CHOICE_RESOLVERS[sb.data["callback"]](game, batch, None, sb.data)
    st.phase = BATTLE
    st.action_player = st.turn_player
    st.consecutive_passes = 0
    game.emit(batch, "phase_changed", phase=BATTLE, turn=st.turn_no)


# ---------------------------------------------------------------- 非戰鬥行動

def _do_action(game: Game, batch: list[dict], player: int, command: dict) -> None:
    ctype = command.get("type")
    if ctype == "play_card":
        _play_card(game, batch, player, command)
    elif ctype == "use_field_ability":
        _use_field_ability(game, batch, player, command, in_battle=False)
    elif ctype == "use_borrowed_effect":
        _use_borrowed_effect(game, batch, player, in_battle=False)
    elif ctype == "use_book_card":
        _use_book_card(game, batch, player, command)
    elif ctype == "declare_attack":
        _declare_attack(game, batch, player, command)
    else:
        raise IllegalCommand("command.unknown", f"未知指令 {ctype}")


def _require_open_page(game: Game, player: int, page) -> str:
    ps = game.state.players[player]
    if not isinstance(page, int) or page not in ps.open_pages():
        raise IllegalCommand("page.not_open", "該頁未翻開或卡片已不在魔書中")
    return ps.card_at(page)


def _play_card(game: Game, batch: list[dict], player: int, command: dict) -> None:
    st = game.state
    ps = st.players[player]
    number = _require_open_page(game, player, command.get("page"))
    card = game.db[number]
    if card.type == MAMODO:
        if number in reg.STACK_ON:
            if number in reg.SPELL_ONLY_STACK:
                raise IllegalCommand("play.spell_only", "此卡只能經由指定戰術卡疊放")
            base_slot = next(
                (s for s in ps.slots if s.top in reg.STACK_ON[number]), None)
            if base_slot is None:
                raise IllegalCommand("play.no_base", "場上沒有可疊放的變身前魔物")
            base_slot.stack.append(number)
            base_slot.injured = False  # 疊放登場回復健康(效果繼承)
            ps.consumed_pages.add(command["page"])
            game.emit(batch, "card_played", player=player, card=number, slot=base_slot.uid, zone="mamodo", stacked=True)
            if number in reg.ON_PLAY:
                reg.ON_PLAY[number](game, batch, player, base_slot)
            return
        if len(ps.slots) >= MAX_FIELD_MAMODO:
            raise IllegalCommand("play.field_full", "場上魔物已達 3 隻")
        if same_name_copies(game, player, card) >= reg.MAX_COPIES.get(number, 1):
            raise IllegalCommand("play.same_name", "同名魔物已達同場上限")
        slot = MamodoSlot(uid=st.next_uid(), stack=[number])
        ps.slots.append(slot)
        ps.consumed_pages.add(command["page"])
        game.emit(batch, "card_played", player=player, card=number, slot=slot.uid, zone="mamodo")
        if number in reg.ON_PLAY:
            reg.ON_PLAY[number](game, batch, player, slot)
    elif card.type == PARTNER:
        target = next(
            (s for s in ps.slots if game.db[s.top].related_mamodo == card.related_mamodo), None)
        if target is None:
            raise IllegalCommand("play.no_mamodo", "對應魔物不在自己場上")
        if target.partner is not None:
            raise IllegalCommand("play.partner_exists", "該魔物已裝有搭檔卡")
        if same_name_in_play(game, player, card):
            raise IllegalCommand("play.same_name", "同名搭檔已在場上")
        target.partner = number
        ps.consumed_pages.add(command["page"])
        game.emit(batch, "card_played", player=player, card=number, slot=target.uid, zone="partner")
        if number in reg.ON_PLAY:
            reg.ON_PLAY[number](game, batch, player, target)
    else:
        raise IllegalCommand("play.not_field_card", "只能放出魔物或搭檔卡")


def _use_field_ability(game: Game, batch: list[dict], player: int, command: dict, in_battle: bool) -> None:
    st = game.state
    zone = command.get("zone")
    slot = st.slot_by_uid(player, command.get("slot_uid", -1))
    if zone not in ("mamodo", "partner") or slot is None:
        raise IllegalCommand("ability.target", "找不到指定的場上卡片")
    number = slot.top if zone == "mamodo" else slot.partner
    if number is None:
        raise IllegalCommand("ability.target", "該魔物未裝搭檔卡")
    spec = reg.ACTIVATED.get(number)
    if spec is None:
        raise IllegalCommand("ability.none", f"{number} 沒有可啟動的效果")
    if zone == "partner" and restricted(game, player, NO_PARTNER_EFFECTS):
        raise IllegalCommand("ability.partner_restricted", "搭檔卡效果目前失效")
    if zone == "mamodo" and restricted(game, player, NO_MAMODO_EFFECTS):
        raise IllegalCommand("ability.mamodo_restricted", "魔物卡效果本回合失效")
    if zone == "mamodo" and slot_restricted(game, player, MAMODO_LOCKED, slot.uid):
        raise IllegalCommand("ability.mamodo_locked", "此魔物的效果本回合被封鎖")
    if spec.timing == "battle" and not in_battle:
        raise IllegalCommand("ability.timing", "此效果只能在戰鬥中使用")
    if spec.timing == "nonbattle" and in_battle:
        raise IllegalCommand("ability.timing", "此效果不能在戰鬥中使用")
    if spec.own_turn and player != st.turn_player:
        raise IllegalCommand("ability.timing", "此效果只能在自己的回合使用")
    # 以卡號為 key:棄掉後重新放出相同編號的卡,該回合仍不可使用其效果
    key = f"{zone}:{number}"
    if key in st.players[player].used_abilities:
        raise IllegalCommand("ability.used", "此效果本回合已使用過")
    if spec.per_game and number in st.players[player].used_per_game:
        raise IllegalCommand("ability.per_game", "此效果一場遊戲只能使用 1 次")
    if st.players[player].mp < spec.mp_cost:
        raise IllegalCommand("ability.mp", "MP 不足")
    if spec.condition and not spec.condition(game, player, slot):
        raise IllegalCommand("ability.condition", "不符合此效果的使用條件")
    st.players[player].used_abilities.add(key)
    if spec.per_game:
        st.players[player].used_per_game.add(number)
    pay_mp(game, batch, player, spec.mp_cost, f"ability:{number}")
    if spec.mode == "discard":
        if zone == "partner":
            slot.partner = None
            to_discard(st.players[player], number)
            game.emit(batch, "card_discarded", player=player, card=number, zone="partner", reason="cost")
        else:
            raise IllegalCommand("ability.mode", "此卡不能以棄掉方式啟動")
    game.emit(batch, "ability_used", player=player, card=number, slot=slot.uid, zone=zone)
    # ジャマー(M-026):對手可能在此效果結束後使其無效 → 先存效果解決前的快照(費用已付)
    snapshot = (copy.deepcopy(st) if zone == "mamodo" and _jammer_holder(game, 1 - player)
                else None)
    spec.handler(game, batch, player, slot)
    _check_victory(game, batch)
    if snapshot is not None:
        _queue_jammer(game, batch, 1 - player, number, snapshot)


def _use_borrowed_effect(game: Game, batch: list[dict], player: int, in_battle: bool) -> None:
    """E-010:使用本回合借用的對手搭檔卡效果(以卡號記錄,該搭檔離場仍可用)。
    使用者付費、不棄任何卡、不計入自己的 used_abilities;時機與搭檔效果失效限制依該搭檔效果。"""
    st = game.state
    borrows = [m for m in st.modifiers
               if m.kind == "borrow_partner" and m.owner == player and m.active(st.turn_no)]
    if not borrows:
        raise IllegalCommand("ability.none", "本回合沒有借用的搭檔效果")
    borrow = next((m for m in borrows if not m.data.get("used")), None)
    if borrow is None:
        raise IllegalCommand("ability.used", "借用的效果本回合已使用過")
    number = borrow.data["card"]
    spec = reg.ACTIVATED.get(number)
    if spec is None:
        raise IllegalCommand("ability.none", f"{number} 沒有可啟動的效果")
    if restricted(game, player, NO_PARTNER_EFFECTS):
        raise IllegalCommand("ability.partner_restricted", "搭檔卡效果目前失效")
    if spec.timing == "battle" and not in_battle:
        raise IllegalCommand("ability.timing", "此效果只能在戰鬥中使用")
    if spec.timing == "nonbattle" and in_battle:
        raise IllegalCommand("ability.timing", "此效果不能在戰鬥中使用")
    if spec.own_turn and player != st.turn_player:
        raise IllegalCommand("ability.timing", "此效果只能在自己的回合使用")
    if st.players[player].mp < spec.mp_cost:
        raise IllegalCommand("ability.mp", "MP 不足")
    if spec.condition and not spec.condition(game, player, None):
        raise IllegalCommand("ability.condition", "不符合此效果的使用條件")
    pay_mp(game, batch, player, spec.mp_cost, f"ability:{number}")
    borrow.data["used"] = True
    game.emit(batch, "ability_used", player=player, card=number, slot=None, zone="borrowed",
              via=borrow.source)
    spec.handler(game, batch, player, None)
    _check_victory(game, batch)


def _use_book_card(game: Game, batch: list[dict], player: int, command: dict) -> None:
    st = game.state
    page = command.get("page")
    number = _require_open_page(game, player, page)
    card = game.db[number]
    if card.type == EVENT:
        if st.players[player].used_event_this_turn:
            raise IllegalCommand("event.limit", "事件卡每回合只能使用 1 張")
        if card.ad == "A" and player != st.turn_player:
            raise IllegalCommand("event.timing", "此事件卡只能在自己的回合使用")
        if card.ad == "D" and player == st.turn_player:
            raise IllegalCommand("event.timing", "此事件卡只能在對手的回合使用")
        handler = reg.EVENT.get(number)
        if handler is None:
            raise IllegalCommand("event.not_implemented", f"{number} 尚未實作")
        condition = reg.EVENT_CONDITION.get(number)
        if condition and not condition(game, player):
            raise IllegalCommand("event.condition", "不符合此事件卡的使用條件")
        cost = card.cost or 0
        if st.players[player].mp < cost:
            raise IllegalCommand("event.mp", "MP 不足")
        st.players[player].used_event_this_turn = True
        pay_mp(game, batch, player, cost, f"event:{number}")
        game.emit(batch, "book_card_used", player=player, card=number, page=page)
        handler(game, batch, player, page)
        _check_victory(game, batch)
    elif card.type == SPELL:
        if card.effect_icon != "nonbattle":
            raise IllegalCommand("spell.not_nonbattle", "此戰術卡沒有非戰鬥圖示")
        if card.ad == "A" and player != st.turn_player:
            raise IllegalCommand("spell.timing", "此非戰鬥戰術只能在自己的回合使用")
        if card.ad == "D" and player == st.turn_player:
            raise IllegalCommand("spell.timing", "此非戰鬥戰術只能在對手的回合使用")
        if not card.is_command_spell and not any(
                _spell_usable_by(game, player, s, card) for s in st.players[player].slots):
            raise IllegalCommand("spell.no_mamodo", "對應此戰術的魔物不在自己場上")
        if number in st.players[player].used_nonbattle_spells:
            raise IllegalCommand("spell.used", "此非戰鬥戰術本回合已使用過")
        handler = reg.SPELL_NONBATTLE.get(number)
        if handler is None:
            raise IllegalCommand("spell.not_implemented", f"{number} 尚未實作")
        cost = spell_cost(game, player, page, card)
        if st.players[player].mp < cost:
            raise IllegalCommand("spell.mp", "MP 不足")
        st.players[player].used_nonbattle_spells.add(number)
        pay_mp(game, batch, player, cost, f"spell:{number}")
        game.emit(batch, "book_card_used", player=player, card=number, page=page)
        handler(game, batch, player)
        _check_victory(game, batch)
    else:
        raise IllegalCommand("book.not_usable", "此卡不能留在魔書中使用")


# ---------------------------------------------------------------- 戰鬥開始確認

def _spell_any_page_standby(game: Game, player: int, page) -> Standby | None:
    """P-015 類待命:允許自魔書任意頁使用指定名稱的戰術卡(每回合一次)。"""
    ps = game.state.players[player]
    if not isinstance(page, int) or not 1 <= page <= BOOK_SIZE or page in ps.consumed_pages:
        return None
    name = game.db[ps.card_at(page)].name_ja
    for sb in game.state.standby:
        if sb.kind == "spell_any_page" and sb.owner == player and sb.data.get("spell_name") == name:
            return sb
    return None


def spell_use_limit(game: Game, player: int, card: CardDef) -> int:
    """戰術卡每張每回合可用次數:預設 1;場上有登記 SPELL_USE_LIMIT 的卡時取其最大值(M-024 二身一体)。"""
    limit = 1
    for number, fn in reg.SPELL_USE_LIMIT.items():
        if any(s.top == number for s in game.state.players[player].slots):
            value = fn(game, player, card)
            if value is not None:
                limit = max(limit, value)
    return limit


def exhausted_spell_pages(game: Game, player: int) -> set[int]:
    """本回合已達可用次數、不能再用的戰術卡頁(依目前場面判斷)。"""
    ps = game.state.players[player]
    return {page for page, uses in ps.spell_page_uses.items()
            if uses >= spell_use_limit(game, player, game.db[ps.card_at(page)])}


def _record_spell_use(ps, page: int) -> None:
    ps.spell_page_uses[page] = ps.spell_page_uses.get(page, 0) + 1


def _spell_usable_by(game: Game, player: int, slot: MamodoSlot, card: CardDef) -> bool:
    """此戰術卡是否可由場上這隻魔物使用(家族相符或戰術相容性擴充,如 M-023/M-029)。"""
    if game.db[slot.top].related_mamodo == card.related_mamodo:
        return True
    compat = reg.SPELL_COMPAT.get(slot.top)
    return bool(compat and compat(game, player, slot, card))


def _validate_spell_declaration(game: Game, player: int, page, slot_uid, *, attack: bool,
                                discount: bool = True) -> tuple[str, MamodoSlot]:
    st = game.state
    ps = st.players[player]
    if isinstance(page, int) and page not in ps.open_pages() and _spell_any_page_standby(game, player, page):
        number = ps.card_at(page)  # 待命允許的任意頁戰術卡
    else:
        number = _require_open_page(game, player, page)
    card = game.db[number]
    if card.type != SPELL:
        raise IllegalCommand("spell.not_spell", "指定的卡不是戰術卡")
    if attack and not card.can_attack():
        raise IllegalCommand("spell.no_attack_icon", "此戰術沒有攻擊圖示")
    if not attack and not card.can_defend():
        raise IllegalCommand("spell.no_defense_icon", "此戰術沒有防禦圖示")
    if st.players[player].spell_page_uses.get(page, 0) >= spell_use_limit(game, player, card):
        raise IllegalCommand("spell.used", "此戰術卡本回合已使用過")
    if restricted(game, player, NO_SPELLS):
        raise IllegalCommand("spell.restricted", "目前不能使用戰術卡")
    if attack and restricted(game, player, NO_ATTACK_SPELL):
        raise IllegalCommand("spell.attack_restricted", "本回合不能使用戰術卡攻擊")
    if card.is_command_spell:
        slot = st.slot_by_uid(player, slot_uid if slot_uid is not None else -1)
        if slot is None:
            if len(st.players[player].slots) == 1:
                slot = st.players[player].slots[0]
            else:
                raise IllegalCommand("spell.need_slot", "指令戰術須指定使用的魔物")
    else:
        explicit = st.slot_by_uid(player, slot_uid) if slot_uid is not None else None
        if explicit is not None and _spell_usable_by(game, player, explicit, card):
            slot = explicit
        else:
            slot = next((s for s in st.players[player].slots
                        if _spell_usable_by(game, player, s, card)), None)
        if slot is None:
            raise IllegalCommand("spell.no_mamodo", "對應此戰術的魔物不在自己場上")
    if slot_restricted(game, player, MAMODO_LOCKED, slot.uid):
        raise IllegalCommand("spell.mamodo_locked", "此魔物本回合不能使用戰術卡")
    cost = spell_cost(game, player, page, card, slot=slot, discount=discount)
    if st.players[player].mp < cost:
        raise IllegalCommand("spell.mp", "MP 不足")
    return number, slot


def _ask_spell_discount(game: Game, batch: list[dict], side: str, decl: dict) -> bool:
    """宣告戰術時,M-008 的減費可用且付得起原價 → 詢問是否使用(回傳 True,待決策後續行);
    只付得起減費後的費用時直接使用。決定記在 decl["discount"]。"""
    player = decl["player"]
    page, card = decl["page"], game.db[decl["spell"]]
    slot = game.state.slot_by_uid(player, decl["slot"])
    decl["discount"] = _optional_discount(game, player, page, card, slot)
    if not decl["discount"] or game.state.players[player].mp < spell_cost(
            game, player, page, card, slot=slot, discount=False):
        return False
    options = [{"value": True, "label": "spell_discount_use"}, {"value": None, "label": "skip"}]
    game.state.pending = PendingChoice(kind="spell_discount", player=player, options=options,
                                       data={"side": side, "decl": decl})
    game.emit(batch, "choice_required", kind="spell_discount", player=player, options=options)
    return True


def _spell_discount_resolver(game: Game, batch: list[dict], value, data) -> None:
    if value is not True and value is not None:
        raise IllegalCommand("choose.invalid", "須選擇是否使用")
    decl = data["decl"]
    decl["discount"] = value is True
    if data["side"] == "attack":
        _open_battle_in(game, batch, decl)
        game.state.action_player = decl["player"]
    else:
        _finish_defense_declaration(game, batch, decl)


reg.CHOICE_RESOLVERS["spell_discount"] = _spell_discount_resolver


def _validate_mamodo_attack(game: Game, player: int, slot_uid) -> tuple[MamodoSlot, dict]:
    """無戰術攻擊(M-027):驗證魔物已註冊直接攻擊效果且可支付費用。"""
    st = game.state
    slot = st.slot_by_uid(player, slot_uid if slot_uid is not None else -1)
    if slot is None:
        raise IllegalCommand("attack.no_slot", "找不到指定的場上魔物")
    spec = reg.MAMODO_ATTACK.get(slot.top)
    if spec is None:
        raise IllegalCommand("attack.no_mamodo_attack", "此魔物不能不用戰術卡直接攻擊")
    if restricted(game, player, NO_MAMODO_EFFECTS):
        raise IllegalCommand("attack.mamodo_restricted", "魔物卡效果本回合失效")
    if slot_restricted(game, player, MAMODO_LOCKED, slot.uid):
        raise IllegalCommand("attack.mamodo_locked", "此魔物的效果本回合被封鎖")
    if st.players[player].mp < spec["mp_cost"]:
        raise IllegalCommand("attack.mp", "MP 不足")
    return slot, spec


def _declare_attack(game: Game, batch: list[dict], player: int, command: dict) -> None:
    st = game.state
    if player != st.turn_player:
        raise IllegalCommand("attack.not_turn_player", "只有回合玩家能攻擊")
    if command.get("mode") == "mamodo":
        slot, _spec = _validate_mamodo_attack(game, player, command.get("slot_uid"))
        st.battle_in = {"attacker": player, "mamodo_attack": True, "slot": slot.uid}
        game.emit(batch, "battle_in_check", attacker=player, spell=None,
                  mamodo=slot.top, slot=slot.uid)
        return
    number, slot = _validate_spell_declaration(
        game, player, command.get("page"), command.get("slot_uid"), attack=True)
    decl = {"player": player, "page": command["page"], "spell": number, "slot": slot.uid}
    if not _ask_spell_discount(game, batch, "attack", decl):
        _open_battle_in(game, batch, decl)


def _open_battle_in(game: Game, batch: list[dict], decl: dict) -> None:
    st = game.state
    st.battle_in = {"attacker": decl["player"], "page": decl["page"], "spell": decl["spell"],
                    "slot": decl["slot"], "discount": decl["discount"]}
    game.emit(batch, "battle_in_check", attacker=decl["player"], spell=decl["spell"], slot=decl["slot"])


def _battle_in_response(game: Game, batch: list[dict], player: int, command: dict) -> None:
    st = game.state
    bi = st.battle_in
    if player != 1 - bi["attacker"]:
        raise IllegalCommand("battle_in.not_defender", "等待非回合玩家回應戰鬥開始確認")
    ctype = command.get("type")
    if ctype in ("battle_in_response", "pass"):
        st.battle_in = None
        _start_battle(game, batch, bi)
        return
    if ctype in ("play_card", "use_field_ability", "use_book_card"):
        st.battle_in = None
        game.emit(batch, "battle_in_voided", attacker=bi["attacker"])
        _do_action(game, batch, player, command)
        st.action_player = bi["attacker"]
        st.consecutive_passes = 0
        return
    raise IllegalCommand("battle_in.invalid", "只能迎戰(進入戰鬥)或插入 1 個行動")


# ---------------------------------------------------------------- 戰鬥

def _consume_standby(game: Game, kind: str, predicate) -> list[Standby]:
    hits = [s for s in game.state.standby if s.kind == kind and predicate(s)]
    for s in hits:
        game.state.standby.remove(s)
    return hits


def _arm_next_battle_standbys(game: Game) -> None:
    """「このターン中の次のバトル」的待命(P-001 / P-007 / M-008 / S-019 / S-026):戰鬥開始時綁定到
    這場戰鬥;條件不符沒有生效的,在戰鬥結束時與「このバトル中」的待命一起移除,不留到之後的戰鬥。"""
    for s in game.state.standby:
        if s.data.get("expires") == "next_battle":
            s.data["expires"] = "battle"


def _start_battle(game: Game, batch: list[dict], bi: dict) -> None:
    st = game.state
    if bi.get("mamodo_attack"):
        _start_mamodo_battle(game, batch, bi)
        return
    attacker, page, number, slot_uid = bi["attacker"], bi["page"], bi["spell"], bi["slot"]
    card = game.db[number]
    # 攻擊宣告:此時再驗證一次(插入行動可能已改變盤面)
    discount = bi.get("discount", False)
    _, using_slot = _validate_spell_declaration(game, attacker, page, slot_uid, attack=True,
                                                discount=discount)
    cost = spell_cost(game, attacker, page, card, slot=using_slot, discount=discount)
    if page not in st.players[attacker].open_pages():  # 經 P-015 類待命自任意頁使用
        for sb in _consume_standby(game, "spell_any_page",
                                   lambda s: s.owner == attacker
                                   and s.data.get("spell_name") == card.name_ja):
            game.emit(batch, "standby_resolved", card=sb.source, kind=sb.kind)
    _record_spell_use(st.players[attacker], page)
    pay_mp(game, batch, attacker, cost, f"spell:{number}")
    battle = BattleState(attacker=attacker, step=STEP_DEFENSE,
                         attack_page=page, attack_spell=number, attack_slot=slot_uid)
    st.battle = battle
    _arm_next_battle_standbys(game)
    game.emit(batch, "battle_started", attacker=attacker, spell=number, slot=slot_uid)

    slot = st.slot_by_uid(attacker, slot_uid)
    mamodo_name = game.db[slot.top].related_mamodo if slot else None
    # 待命:戰術卡加成(M-008 減費減魔力,選擇使用時才套用 / P-007 加魔力)
    for sb in _consume_standby(game, "spell_bonus",
                               lambda s: s.owner == attacker and (
                                   s.data.get("mamodo") in (None, mamodo_name))
                               and (discount or not s.data.get("optional"))):
        add_spell_power(battle, "attack", sb.source, sb.data.get("power_delta", 0))
        game.emit(batch, "standby_resolved", card=sb.source, kind=sb.kind)
    # 待命:攻擊不可被防禦(P-001 / S-019 / S-026)
    for sb in _consume_standby(game, "attack_undefendable",
                               lambda s: s.owner == attacker and (
                                   s.data.get("mamodo") in (None, mamodo_name))):
        battle.attack_undefendable = True
        game.emit(batch, "standby_resolved", card=sb.source, kind=sb.kind)
    # 待命:本場戰鬥不能保護魔書(E-013)
    for sb in _consume_standby(game, "no_protect_book", lambda s: s.owner == attacker):
        battle.data["no_protect_book"] = True
        game.emit(batch, "standby_resolved", card=sb.source, kind=sb.kind)
    # 待命:下一張攻擊戰術獲勝改為負傷對手魔物(S-057)
    for sb in _consume_standby(game, "injure_instead", lambda s: s.owner == attacker):
        battle.data["injure_instead"] = True
        game.emit(batch, "standby_resolved", card=sb.source, kind=sb.kind)
    # 宣告時效果(擲硬幣等於宣告時確定)
    rider = reg.SPELL_RIDERS.get(number)
    if rider and rider.on_declare:
        rider.on_declare(game, batch, attacker, "attack")


def _start_mamodo_battle(game: Game, batch: list[dict], bi: dict) -> None:
    """無戰術攻擊(M-027):合計魔力與傷害為卡片指定固定值,其餘戰鬥流程相同。"""
    st = game.state
    attacker, slot_uid = bi["attacker"], bi["slot"]
    slot, spec = _validate_mamodo_attack(game, attacker, slot_uid)  # 插入行動可能已改變盤面
    pay_mp(game, batch, attacker, spec["mp_cost"], f"mamodo_attack:{slot.top}")
    battle = BattleState(attacker=attacker, step=STEP_DEFENSE,
                         attack_page=None, attack_spell=None, attack_slot=slot_uid)
    battle.data["attack_fixed_power"] = spec["power"]
    battle.data["attack_fixed_source"] = slot.top
    battle.data["attack_fixed_damage"] = spec["damage"]
    st.battle = battle
    _arm_next_battle_standbys(game)
    game.emit(batch, "battle_started", attacker=attacker, spell=None,
              mamodo=slot.top, slot=slot_uid)
    # 待命:攻擊不可被防禦(S-019 / S-026;P-001 限「ガッシュ・ベル」の術で攻撃,無戰術攻擊不適用)
    for sb in _consume_standby(game, "attack_undefendable",
                               lambda s: s.owner == attacker and s.data.get("mamodo") is None):
        battle.attack_undefendable = True
        game.emit(batch, "standby_resolved", card=sb.source, kind=sb.kind)
    for sb in _consume_standby(game, "no_protect_book", lambda s: s.owner == attacker):
        battle.data["no_protect_book"] = True
        game.emit(batch, "standby_resolved", card=sb.source, kind=sb.kind)


def _battle_command(game: Game, batch: list[dict], player: int, command: dict) -> None:
    st = game.state
    battle = st.battle
    ctype = command.get("type")
    if battle.step == STEP_DEFENSE:
        if player != battle.defender:
            raise IllegalCommand("defense.not_defender", "等待防禦方宣告")
        if ctype == "no_defense" or (ctype == "pass"):
            battle.defense_declared = True
            game.emit(batch, "no_defense", player=player)
            _enter_effects_step(game, batch)
            return
        if ctype == "declare_defense":
            if battle.attack_undefendable:
                raise IllegalCommand("defense.undefendable", "此攻擊不可被防禦")
            if restricted(game, player, NO_DEFENSE):
                raise IllegalCommand("defense.restricted", "目前不能防禦")
            number, slot = _validate_spell_declaration(
                game, player, command.get("page"), command.get("slot_uid"), attack=False)
            decl = {"player": player, "page": command["page"], "spell": number, "slot": slot.uid}
            if not _ask_spell_discount(game, batch, "defense", decl):
                _finish_defense_declaration(game, batch, decl)
            return
        raise IllegalCommand("defense.invalid", "防禦方只能宣告防禦或不防禦")

    if battle.step == STEP_EFFECTS:
        if player != battle.data.get("effect_turn"):
            raise IllegalCommand("priority.other", "現在不是你使用戰鬥中效果的時機")
        if ctype == "pass":
            battle.effect_passes += 1
            game.emit(batch, "passed", player=player)
            if battle.effect_passes >= 2:
                _resolve_showdown(game, batch)
            else:
                battle.data["effect_turn"] = 1 - player
            return
        if ctype in ("use_field_ability", "use_borrowed_effect"):
            if ctype == "use_field_ability":
                _use_field_ability(game, batch, player, command, in_battle=True)
            else:
                _use_borrowed_effect(game, batch, player, in_battle=True)
            battle.effect_passes = 0
            if st.battle is not None:
                if st.pending is None:
                    battle.data["effect_turn"] = 1 - player
                else:
                    battle.data["pending_flip"] = player  # 決策解決後再輪替
            return
        raise IllegalCommand("battle.invalid", "戰鬥中只能使用帶戰鬥圖示的效果或 pass")
    raise IllegalCommand("battle.step", "戰鬥狀態異常")


def _finish_defense_declaration(game: Game, batch: list[dict], decl: dict) -> None:
    st = game.state
    battle = st.battle
    player, page, number, discount = decl["player"], decl["page"], decl["spell"], decl["discount"]
    slot = st.slot_by_uid(player, decl["slot"])
    card = game.db[number]
    cost = spell_cost(game, player, page, card, slot=slot, discount=discount)
    if page not in st.players[player].open_pages():
        for sb in _consume_standby(game, "spell_any_page",
                                   lambda s: s.owner == player
                                   and s.data.get("spell_name") == card.name_ja):
            game.emit(batch, "standby_resolved", card=sb.source, kind=sb.kind)
    _record_spell_use(st.players[player], page)
    pay_mp(game, batch, player, cost, f"spell:{number}")
    battle.defense_page = page
    battle.defense_spell = number
    battle.defense_slot = slot.uid
    battle.defense_declared = True
    game.emit(batch, "defense_declared", player=player, spell=number, slot=slot.uid)
    mamodo_name = game.db[slot.top].related_mamodo
    for sb in _consume_standby(game, "spell_bonus",
                               lambda s: s.owner == player and (
                                   s.data.get("mamodo") in (None, mamodo_name))
                               and (discount or not s.data.get("optional"))):
        add_spell_power(battle, "defense", sb.source, sb.data.get("power_delta", 0))
        game.emit(batch, "standby_resolved", card=sb.source, kind=sb.kind)
    rider = reg.SPELL_RIDERS.get(number)
    if rider and rider.on_declare:
        rider.on_declare(game, batch, player, "defense")
    _enter_effects_step(game, batch)


def _enter_effects_step(game: Game, batch: list[dict]) -> None:
    battle = game.state.battle
    battle.step = STEP_EFFECTS
    battle.effect_passes = 0
    battle.data["effect_turn"] = battle.attacker  # 攻方先使用效果
    game.emit(batch, "battle_effects_step", attacker=battle.attacker)


def _side_total(game: Game, battle: BattleState, side: str) -> int:
    return side_breakdown(game, battle, side)[0]


def side_breakdown(game: Game, battle: BattleState, side: str) -> tuple[int, list[dict]]:
    """一方(attack / defense)的合計魔力與逐項明細;各項 amount 加總恆等於合計。
    不防禦時明細為空、合計 0;被無效化時以「無效化」調整項把合計歸 0。"""
    if side == "attack":
        negated, negated_by = battle.attack_negated, battle.data.get("attack_negated_by")
        if battle.attack_spell is None:  # 無戰術攻擊:固定合計魔力
            total = battle.data.get("attack_fixed_power", 0)
            items = [_item("fixed", battle.data.get("attack_fixed_source"), total)]
            return _negate(total, items, negated, negated_by)
        player, slot_uid, spell = battle.attacker, battle.attack_slot, battle.attack_spell
    else:
        if not battle.defense_spell:
            return 0, []
        negated, negated_by = battle.defense_negated, battle.data.get("defense_negated_by")
        player, slot_uid, spell = battle.defender, battle.defense_slot, battle.defense_spell
    card = game.db[spell]
    slot = game.state.slot_by_uid(player, slot_uid)
    mamodo, items = power_breakdown(game, player, slot) if slot else (0, [])
    # 戰術的魔力(特殊為 0),加上戰術自身的加值與待命 / 效果的加成(S-016 / S-017 / S-040 / M-008 / P-007)
    spell_items = [_item("spell", spell, 0 if card.power_special else (card.power_bonus or 0))]
    spell_items += [dict(i) for i in battle.data.get(f"{side}_spell_power", [])]
    spell_pw = sum(i["amount"] for i in spell_items)
    if spell_pw < 0:  # 戰術的魔力加減不低於 0(M-008「0より小さくはならない」)
        spell_items.append(_item("spell_floor", None, -spell_pw))
    return _negate(mamodo + max(0, spell_pw), items + spell_items, negated, negated_by)


def _negate(total: int, items: list[dict], negated: bool, source: str | None) -> tuple[int, list[dict]]:
    if not negated:
        return total, items
    return 0, items + [_item("negated", source, -total)]


def _attack_damage_amount(game: Game, battle: BattleState) -> int:
    if battle.attack_spell is None:  # 無戰術攻擊:固定傷害
        base = battle.data.get("attack_fixed_damage", 0)
    else:
        base = game.db[battle.attack_spell].damage or 0
    delta = battle.data.get("attack_damage_delta", 0)
    doubled = battle.data.get("attack_damage_double", False)
    for m in game.state.modifiers:
        if not m.active(game.state.turn_no) or m.target_player != battle.attacker:
            continue
        if m.target_slot not in (None, battle.attack_slot):
            continue
        if m.kind == "damage_delta":
            delta += m.amount
        elif m.kind == "damage_double":
            doubled = True
    total = base + delta
    if doubled:
        total *= 2
    total += battle.data.get("defense_damage_delta", 0)  # S-027 減傷
    rider = reg.SPELL_RIDERS.get(battle.attack_spell) if battle.attack_spell else None
    if rider and rider.damage_bonus is not None:  # 依合計魔力調整傷害(S-042)
        total += rider.damage_bonus(game, battle)
    if rider and rider.damage_cap is not None:  # 傷害上限(S-032/S-034)
        total = min(total, rider.damage_cap)
    return max(0, total)


def _resolve_showdown(game: Game, batch: list[dict]) -> None:
    st = game.state
    battle = st.battle
    att, att_items = side_breakdown(game, battle, "attack")
    deff, def_items = side_breakdown(game, battle, "defense")
    battle.data["attack_total"] = att  # 供傷害免疫等查詢型 hook 使用(M-031)
    attacker_wins = (not battle.attack_negated) and att > deff
    game.emit(batch, "showdown", attacker=battle.attacker, attacker_total=att, defender_total=deff,
              winner="attacker" if attacker_wins else "defender",
              attack_negated=battle.attack_negated,
              attacker_breakdown=att_items, defender_breakdown=def_items)
    rider = reg.SPELL_RIDERS.get(battle.attack_spell) if battle.attack_spell else None
    if attacker_wins:
        if rider and rider.on_win:
            rider.on_win(game, batch, battle.attacker)
        if st.phase == GAME_OVER:
            return
        if rider and rider.on_win_owns_damage:
            return
        # 獲勝時負傷代替魔書傷害(S-058 / S-057 待命旗標)
        if (rider and rider.injure_instead) or battle.data.get("injure_instead"):
            _injure_instead_of_damage(game, batch)
            return
        amount = 0 if (rider and rider.no_book_damage) else _attack_damage_amount(game, battle)
        if amount > 0:
            _start_damage(game, batch,
                          [{"kind": "book", "player": battle.defender, "amount": amount}],
                          {"cause": "battle_attack", "source": battle.attack_spell,
                           "source_player": battle.attacker, "amount": amount})
            return
        _finish_battle_damage(game, batch, {"cause": "battle_attack", "dealt": False,
                                            "source": battle.attack_spell,
                                            "source_player": battle.attacker})
        return
    # 防方獲勝(或攻擊無效):攻方效果無效;僅【反擊】解決
    d_rider = reg.SPELL_RIDERS.get(battle.defense_spell) if battle.defense_spell else None
    if d_rider and d_rider.counter and not battle.defense_negated:
        amount = game.db[battle.defense_spell].damage or 0
        if amount > 0:
            _start_damage(game, batch,
                          [{"kind": "book", "player": battle.attacker, "amount": amount}],
                          {"cause": "battle_counter", "source": battle.defense_spell,
                           "source_player": battle.defender})
            return
    _end_battle(game, batch)


def _injure_instead_of_damage(game: Game, batch: list[dict]) -> None:
    """獲勝時使對手 1 隻魔物負傷代替魔書傷害;攻方選擇目標,無目標則無效果。"""
    st = game.state
    battle = st.battle
    targets = st.players[battle.defender].slots
    ctx = {"cause": "battle_attack", "source": battle.attack_spell,
           "source_player": battle.attacker}
    if not targets:
        _finish_battle_damage(game, batch, {**ctx, "dealt": False})
        return
    if len(targets) == 1:
        _start_damage(game, batch,
                      [{"kind": "slot", "player": battle.defender,
                        "slot_uid": targets[0].uid, "amount": 1}], ctx)
        return
    st.pending = PendingChoice(
        kind="injure_instead_target", player=battle.attacker, source=battle.attack_spell,
        options=[slot_option(battle.defender, s) for s in targets], data={"ctx": ctx})
    game.emit(batch, "choice_required", kind="injure_instead_target", player=battle.attacker)


def _damage_order_option(index: int, item: dict) -> dict:
    """受傷順序的選項:魔物項標示所在的魔物槽;魔書項維持按鈕。"""
    opt = {"index": index, "item": item}
    if item["kind"] == "slot":
        opt.update(zone="slot", player=item["player"], slot=item["slot_uid"])
    return opt


def _injure_instead_resolver(game: Game, batch: list[dict], value, data) -> None:
    st = game.state
    battle = st.battle
    slot = st.slot_by_uid(battle.defender, value) if battle else None
    if slot is None:
        raise IllegalCommand("choose.invalid", "無效的負傷對象")
    st.pending = None
    _start_damage(game, batch,
                  [{"kind": "slot", "player": battle.defender,
                    "slot_uid": slot.uid, "amount": 1}], data["ctx"])


reg.CHOICE_RESOLVERS["injure_instead_target"] = _injure_instead_resolver


# ---------------------------------------------------------------- ジャマー(M-026《裏切り者》)
# 對手用完「魔物的效果」(啟動型)後,持有可用ジャマー的一方立即被詢問是否使其無效。
# 無效 = 把效果造成的變化還原到效果解決前(對手支付的費用與「本回合已使用」照算);
# 輪到誰行動、pass 次數、戰鬥中的效果輪替等流程狀態維持目前的值。

def _jammer_holder(game: Game, player: int):
    """player 場上可用的ジャマー:(卡號, slot, spec);沒有則 None。"""
    ps = game.state.players[player]
    for slot in ps.slots:
        spec = reg.JAMMER.get(slot.top)
        if spec is None:
            continue
        if (f"mamodo:{slot.top}" in ps.used_abilities or ps.mp < spec["mp_cost"]
                or restricted(game, player, NO_MAMODO_EFFECTS)
                or slot_restricted(game, player, MAMODO_LOCKED, slot.uid)):
            continue
        return slot.top, slot, spec
    return None


def _queue_jammer(game: Game, batch: list[dict], player: int, negated: str, snapshot) -> None:
    st = game.state
    if st.phase == GAME_OVER or (snapshot.battle is None) != (st.battle is None):
        return  # 遊戲結束,或效果使戰鬥開始 / 結束:不提供無效化(避免復活已結束的戰鬥)
    game.jammer = {"player": player, "negated": negated, "snapshot": snapshot}
    _offer_jammer_if_ready(game, batch)


def _offer_jammer_if_ready(game: Game, batch: list[dict]) -> None:
    """待決事項都解決(對手效果的選擇完成)後,才詢問ジャマー。"""
    st = game.state
    if game.jammer is None or st.pending is not None:
        return
    if st.phase == GAME_OVER or _jammer_holder(game, game.jammer["player"]) is None:
        game.jammer = None
        return
    player, negated = game.jammer["player"], game.jammer["negated"]
    number, _slot, _spec = _jammer_holder(game, player)
    options = [{"value": None, "label": "skip"},
               {"value": True, "label": "jammer_use", "card": negated}]
    st.pending = PendingChoice(kind="jammer_negate", player=player, source=number,
                               options=options, data={"negated": negated})
    game.emit(batch, "choice_required", kind="jammer_negate", player=player, options=options)


def _restore_effect_state(st: GameState, snap: GameState) -> None:
    """把遊戲內容還原到 snap,流程狀態(行動權、pass 次數、戰鬥輪替)維持目前的值。"""
    st.players = snap.players
    st.modifiers = snap.modifiers
    st.standby = snap.standby
    if snap.battle is not None and st.battle is not None:
        b, cur = snap.battle, st.battle
        b.step = cur.step
        b.effect_passes = cur.effect_passes
        for key in ("effect_turn", "pending_flip"):
            if key in cur.data:
                b.data[key] = cur.data[key]
            else:
                b.data.pop(key, None)
        st.battle = b
    st._uid_seq = max(st._uid_seq, snap._uid_seq)


def _jammer_resolver(game: Game, batch: list[dict], value, data) -> None:
    if value is not True and value is not None:
        raise IllegalCommand("choose.invalid", "須選擇是否使用")
    offer = game.jammer
    if value is None or offer is None:
        game.jammer = None
        return
    player = offer["player"]
    holder = _jammer_holder(game, player)
    if holder is None:
        raise IllegalCommand("choose.invalid", "目前無法使用此效果")
    number, slot, spec = holder
    st = game.state
    # 連鎖:對手可再以自己的ジャマー使這次無效化失效 → 以「已支付本次費用、尚未還原」的狀態當快照
    chain = None
    if _jammer_holder(game, 1 - player) is not None:
        chain = copy.deepcopy(st)
        chain.players[player].mp -= spec["mp_cost"]
        chain.players[player].used_abilities.add(f"mamodo:{number}")
    slot_uid = slot.uid
    _restore_effect_state(st, offer["snapshot"])
    game.jammer = None
    st.players[player].used_abilities.add(f"mamodo:{number}")
    pay_mp(game, batch, player, spec["mp_cost"], f"ability:{number}")
    game.emit(batch, "ability_used", player=player, card=number, slot=slot_uid, zone="mamodo")
    game.emit(batch, "effect_negated", player=player, source=number, negated=offer["negated"])
    if chain is not None:
        game.jammer = {"player": 1 - player, "negated": number, "snapshot": chain}


reg.CHOICE_RESOLVERS["jammer_negate"] = _jammer_resolver


def _end_battle(game: Game, batch: list[dict]) -> None:
    st = game.state
    st.modifiers = [m for m in st.modifiers if m.duration != DUR_BATTLE]
    st.standby = [s for s in st.standby if s.data.get("expires") != "battle"]   # 「このバトル中」的待命(P-006)
    st.battle = None
    game.emit(batch, "battle_ended")
    if st.phase == GAME_OVER:
        return
    st.action_player = st.turn_player
    st.consecutive_passes = 0


# ---------------------------------------------------------------- 傷害系統

def _eligible_protectors(game: Game, item: dict) -> list[MamodoSlot]:
    """可保護此項傷害的魔物。魔書傷害:任何自己魔物;魔物傷害:其他魔物。"""
    st = game.state
    player = item["player"]
    if item["kind"] == "book":
        battle = st.battle
        if battle is not None and battle.data.get("no_protect_book") and player == battle.defender:
            return []
        return list(st.players[player].slots)
    return [s for s in st.players[player].slots if s.uid != item.get("slot_uid")]


def _start_damage(game: Game, batch: list[dict], items: list[dict], ctx: dict) -> None:
    ctx.setdefault("dealt", False)
    ctx["items"] = items
    _process_damage(game, batch, ctx)


def _process_damage(game: Game, batch: list[dict], ctx: dict) -> None:
    st = game.state
    while ctx["items"]:
        if st.phase == GAME_OVER:
            return
        # 目標魔物在處理前已消失(如被其他項目的保護頂替致入墓):此份傷害作廢,不詢問保護
        kept, stale = [], []
        for it in ctx["items"]:
            if it["kind"] == "slot" and st.slot_by_uid(it["player"], it["slot_uid"]) is None:
                stale.append(it)
            else:
                kept.append(it)
        if stale:
            ctx["items"] = kept
            for it in stale:
                game.emit(batch, "damage_prevented", player=it["player"],
                          slot=it["slot_uid"], reason="no_target")
            continue
        if len(ctx["items"]) > 1:
            # 多項傷害:受方決定順序(第一彈僅保護鏈會出現,仍保留通用機制)
            receiver = ctx["items"][0]["player"]
            st.pending = PendingChoice(
                kind="damage_order", player=receiver, source=ctx.get("source"),
                options=[_damage_order_option(i, it) for i, it in enumerate(ctx["items"])],
                data={"ctx": ctx})
            game.emit(batch, "choice_required", kind="damage_order", player=receiver)
            return
        item = ctx["items"][0]
        protectors = _eligible_protectors(game, item)
        if protectors and not item.get("no_protect"):
            receiver = item["player"]
            st.pending = PendingChoice(
                kind="protect", player=receiver, source=ctx.get("source"),
                options=[{"value": None, "label": "no_protect"}]
                + [slot_option(receiver, s) for s in protectors],
                data={"ctx": ctx})
            game.emit(batch, "choice_required", kind="protect", player=receiver,
                      item=dict(item))
            return
        ctx["items"].pop(0)
        _apply_damage_item(game, batch, item, ctx)
    _finish_damage(game, batch, ctx)


def _apply_damage_item(game: Game, batch: list[dict], item: dict, ctx: dict) -> None:
    st = game.state
    player = item["player"]
    if _full_immune(game, player):  # S-037/038/041:自己魔書與所有魔物不受傷害/負傷
        game.emit(batch, "damage_prevented", player=player,
                  slot=item.get("slot_uid"), reason="immune")
        return
    if item["kind"] == "book":
        ps = st.players[player]
        ps.pos += 2 * item["amount"]
        ctx["dealt"] = True
        game.emit(batch, "damage_dealt", target="book", player=player,
                  amount=item["amount"], pos=min(ps.pos, BOOK_SIZE + 2))
        if ps.book_exhausted():
            _game_over(game, batch, winner=1 - player, reason="book_out")
        return
    slot = st.slot_by_uid(player, item["slot_uid"])
    if slot is None:
        return
    # 查詢型免疫(M-031:不受合計魔力 6000 以下戰術卡的傷害與負傷)
    immunity = reg.DAMAGE_IMMUNITY.get(slot.top)
    if immunity and immunity(game, player, slot, ctx):
        game.emit(batch, "damage_prevented", player=player, slot=slot.uid, reason="immunity")
        return
    # 待命:無效 1 次傷害(P-006)
    negates = _consume_standby(
        game, "negate_damage",
        lambda s: s.owner == player and s.data.get("slot_uid") == slot.uid)
    if negates:
        sb = negates[0]
        game.emit(batch, "damage_negated", player=player, slot=slot.uid, card=sb.source)
        resolver = reg.CHOICE_RESOLVERS.get(sb.data.get("after", ""))
        if resolver:
            resolver(game, batch, None, sb.data)
        return
    # 戰鬥中不受傷害(M-013/M-015)
    if any(m.kind == "no_damage" and m.target_player == player and m.target_slot == slot.uid
           and m.active(st.turn_no) for m in st.modifiers):
        game.emit(batch, "damage_prevented", player=player, slot=slot.uid)
        return
    ctx["dealt"] = True
    battle = st.battle
    # S-031 バオウ:因此戰術負傷的魔物直接入墓
    injure_to_discard = (battle is not None and battle.data.get("injure_to_discard")
                         and ctx.get("cause") in ("battle_attack",))
    if slot.injured or injure_to_discard:
        _discard_slot(game, batch, player, slot, reason="damage")
    else:
        slot.injured = True
        game.emit(batch, "mamodo_injured", player=player, slot=slot.uid, card=slot.top)


def _discard_slot(game: Game, batch: list[dict], player: int, slot: MamodoSlot, reason: str) -> None:
    st = game.state
    ps = st.players[player]
    if slot not in ps.slots:
        return
    # 疊放頂層單獨入墓、下層保留(M-027 裝甲):發出分離事件供 M-028 觸發器使用
    if len(slot.stack) > 1 and slot.top in reg.DETACH_KEEP_UNDER:
        top = slot.stack.pop()
        to_discard(ps, top)
        game.emit(batch, "card_discarded", player=player, card=top, zone="mamodo", reason=reason)
        game.emit(batch, "stack_detached", player=player, slot=slot.uid,
                  detached=top, remaining=slot.top)
        if top in reg.ON_DISCARD:
            reg.ON_DISCARD[top](game, batch, player, slot)
        return
    ps.slots.remove(slot)
    for number in reversed(slot.stack):
        to_discard(ps, number)
    if slot.partner:
        to_discard(ps, slot.partner)
        game.emit(batch, "card_discarded", player=player, card=slot.partner, zone="partner", reason="attached")
    game.emit(batch, "mamodo_discarded", player=player, slot=slot.uid,
              cards=list(slot.stack), reason=reason)
    for number in slot.stack:
        if number in reg.ON_DISCARD:
            reg.ON_DISCARD[number](game, batch, player, slot)


def _finish_damage(game: Game, batch: list[dict], ctx: dict) -> None:
    st = game.state
    if st.phase == GAME_OVER:
        return
    if ctx.get("cause") in ("battle_attack", "battle_counter"):
        _finish_battle_damage(game, batch, ctx)
        return
    resolver = reg.CHOICE_RESOLVERS.get(ctx.get("after", ""))
    if resolver:
        resolver(game, batch, None, ctx)


def _finish_battle_damage(game: Game, batch: list[dict], ctx: dict) -> None:
    battle = game.state.battle
    if ctx["cause"] == "battle_attack" and ctx.get("dealt"):
        rider = reg.SPELL_RIDERS.get(ctx["source"]) if ctx.get("source") else None
        if rider and rider.on_damage:
            rider.on_damage(game, batch, ctx["source_player"])
        # 防禦方以帶 on_defense_damaged 的戰術防禦卻仍被造成傷害(S-056)
        if battle is not None and battle.defense_spell and not battle.defense_negated:
            d_rider = reg.SPELL_RIDERS.get(battle.defense_spell)
            if d_rider and d_rider.on_defense_damaged:
                d_rider.on_defense_damaged(game, batch, battle.defender,
                                           ctx.get("amount", 0))
    if game.state.phase != GAME_OVER and battle is not None:
        _end_battle(game, batch)


# ---------------------------------------------------------------- 決策處理

def _maybe_discard_protector(game: Game, batch: list[dict], player: int,
                             slot: MamodoSlot, ctx: dict) -> None:
    """P-012 雪莉:對自己布拉葛攻擊傷害進行保護的魔物,承受後直接入墓。"""
    st = game.state
    battle = st.battle
    if battle is None or ctx.get("cause") != "battle_attack":
        return
    atk_slot = st.slot_by_uid(battle.attacker, battle.attack_slot)
    atk_name = game.db[atk_slot.top].related_mamodo if atk_slot else None
    for m in st.modifiers:
        if (m.kind == "protect_discard" and m.owner == battle.attacker
                and m.active(st.turn_no) and m.data.get("mamodo") == atk_name):
            if slot in st.players[player].slots:
                _discard_slot(game, batch, player, slot, reason="protect_discard")
            return


def _handle_choose(game: Game, batch: list[dict], command: dict) -> None:
    st = game.state
    pending = st.pending
    value = command.get("value")
    if pending.kind == "protect":
        ctx = pending.data["ctx"]
        item = ctx["items"][0]
        if value is None:
            st.pending = None
            ctx["items"].pop(0)
            item["no_protect"] = True
            _apply_damage_item(game, batch, item, ctx)
            _process_damage(game, batch, ctx)
            return
        slot = st.slot_by_uid(pending.player, value)
        if slot is None or slot.uid == item.get("slot_uid"):
            raise IllegalCommand("choose.invalid", "無效的保護對象")
        st.pending = None
        ctx["items"].pop(0)
        game.emit(batch, "protected", player=pending.player, slot=slot.uid, card=slot.top)
        _apply_damage_item(game, batch,
                           {"kind": "slot", "player": pending.player,
                            "slot_uid": slot.uid, "amount": 1}, ctx)
        _maybe_discard_protector(game, batch, pending.player, slot, ctx)
        _process_damage(game, batch, ctx)
        return
    if pending.kind == "damage_order":
        ctx = pending.data["ctx"]
        if not isinstance(value, int) or not 0 <= value < len(ctx["items"]):
            raise IllegalCommand("choose.invalid", "無效的順序選擇")
        st.pending = None
        item = ctx["items"].pop(value)
        ctx["items"].insert(0, item)
        # 僅排序;實際套用回到傷害流程(單項時直接處理)
        first = ctx["items"][0]
        protectors = _eligible_protectors(game, first)
        if protectors and not first.get("no_protect"):
            st.pending = PendingChoice(
                kind="protect", player=first["player"], source=ctx.get("source"),
                options=[{"value": None, "label": "no_protect"}]
                + [slot_option(first["player"], s) for s in protectors],
                data={"ctx": ctx})
            game.emit(batch, "choice_required", kind="protect", player=first["player"], item=dict(first))
            return
        ctx["items"].pop(0)
        _apply_damage_item(game, batch, first, ctx)
        _process_damage(game, batch, ctx)
        return
    if pending.kind == "deploy_page":
        options = {o["page"] for o in pending.options}
        if value not in options:
            raise IllegalCommand("choose.invalid", "無效的頁面選擇")
        st.pending = None
        _deploy_mamodo_from_page(game, batch, pending.player, value)
        _continue_end_phase(game, batch, pending.data["stage"])
        return
    # 卡片效果的自訂決策:resolver 驗證失敗(拋出)時保留 pending,可重新選擇
    from .effects.tree import CHOICE_KEY, resume as resume_effect_tree
    if CHOICE_KEY in pending.data:  # 效果樹 Choose 建立的 pending(僅此標記才交給樹;擲幣確認仍走原 resolver)
        resume_effect_tree(game, batch, value, pending.data)
    else:
        resolver = reg.CHOICE_RESOLVERS.get(pending.kind)
        if resolver is None:
            raise IllegalCommand("choose.unknown", f"未知的決策類型 {pending.kind}")
        resolver(game, batch, value, pending.data)
    if st.pending is pending:
        st.pending = None
    _check_victory(game, batch)
    if (st.pending is None and st.battle is not None
            and "pending_flip" in st.battle.data):
        p = st.battle.data.pop("pending_flip")
        st.battle.data["effect_turn"] = 1 - p


# ---------------------------------------------------------------- 結束階段

def _end_phase(game: Game, batch: list[dict]) -> None:
    st = game.state
    game.emit(batch, "phase_changed", phase="end", turn=st.turn_no)
    _continue_end_phase(game, batch, stage=0)


def _continue_end_phase(game: Game, batch: list[dict], stage: int) -> None:
    """結束階段可能被魔物消失處理的選擇中斷,以 stage 續行(0=回合玩家, 1=非回合玩家, 2=收尾)。"""
    st = game.state
    order = [st.turn_player, 1 - st.turn_player]
    for i in range(stage, 2):
        player = order[i]
        if st.phase == GAME_OVER:
            return
        if not st.players[player].slots:
            if not _mamodo_gone_processing(game, batch, player, next_stage=i + 1):
                return  # 等待玩家選擇頁面,或已判負
    if st.phase == GAME_OVER:
        return
    # M-030 ヨポポ待命:本回合結束不翻魔書頁直接結束
    skip = _consume_standby(game, "skip_end_flip", lambda s: s.owner == st.turn_player)
    if skip:
        game.emit(batch, "standby_resolved", card=skip[0].source, kind="skip_end_flip")
    else:
        # 強制翻頁 +2 MP
        ps = st.players[st.turn_player]
        if ps.pos + 2 > BOOK_SIZE + 2:
            _game_over(game, batch, winner=1 - st.turn_player, reason="book_out")
            return
        ps.pos += 2
        ps.mp += 2
        game.emit(batch, "pages_flipped", player=st.turn_player, count=1, pos=ps.pos, mp_gained=2, forced=True)
        if ps.book_exhausted():
            _game_over(game, batch, winner=1 - st.turn_player, reason="book_out")
            return
    # 時效到期與回合收尾
    st.modifiers = [m for m in st.modifiers if not _expires_now(m, st.turn_no)]
    st.standby = [s for s in st.standby
                  if not (s.data.get("expires", "turn") in ("turn", "next_battle")
                          and s.created_turn == st.turn_no)
                  and not (s.created_turn < st.turn_no)]
    for p in st.players:
        p.spell_page_uses.clear()
        p.used_abilities.clear()
        p.used_nonbattle_spells.clear()
        p.used_event_this_turn = False
        p.discarded_this_turn.clear()
        p.page_effect_used = False
        p.page_back_effect_used = False
        p.page_effect_limited = False
        p.page_back_effect_limited = False
    game.emit(batch, "turn_ended", turn=st.turn_no)
    st.turn_no += 1
    st.turn_player = 1 - st.turn_player
    st.phase = START
    st.action_player = None
    st.consecutive_passes = 0
    game.emit(batch, "turn_started", turn=st.turn_no, player=st.turn_player)


def _expires_now(m: Modifier, turn_no: int) -> bool:
    if m.duration == DUR_TURN:
        return True  # 每回合結束時,本回合時效到期(建立回合結束即移除)
    if m.duration == DUR_UNTIL_END_NEXT_TURN:
        return turn_no >= m.created_turn + 1
    if m.duration == DUR_NEXT_TURN:
        return turn_no >= m.created_turn + 1
    return False


def _mamodo_gone_processing(game: Game, batch: list[dict], player: int, next_stage: int) -> bool:
    """ADV:結束階段場上無魔物 → 從魔書強制放出。回傳 True 表示已完成(未中斷)。"""
    st = game.state
    ps = st.players[player]
    while True:
        candidates = [p for p in ps.open_pages()
                      if game.db[ps.card_at(p)].type == MAMODO
                      and ps.card_at(p) not in reg.STACK_ON]
        if len(candidates) == 1:
            _deploy_mamodo_from_page(game, batch, player, candidates[0])
            return True
        if len(candidates) > 1:
            st.pending = PendingChoice(
                kind="deploy_page", player=player,
                options=[page_option(player, p, ps.card_at(p)) for p in candidates],
                data={"stage": next_stage})
            game.emit(batch, "choice_required", kind="deploy_page", player=player)
            return False
        # 翻頁尋找魔物(不獲得 MP)
        if ps.pos + 2 > BOOK_SIZE:
            _game_over(game, batch, winner=1 - player, reason="no_mamodo")
            return False
        ps.pos += 2
        game.emit(batch, "pages_flipped", player=player, count=1, pos=ps.pos, mp_gained=0, forced=True)


def _deploy_mamodo_from_page(game: Game, batch: list[dict], player: int, page: int) -> None:
    st = game.state
    ps = st.players[player]
    number = ps.card_at(page)
    slot = MamodoSlot(uid=st.next_uid(), stack=[number])
    ps.slots.append(slot)
    ps.consumed_pages.add(page)
    game.emit(batch, "card_played", player=player, card=number, slot=slot.uid, zone="mamodo", forced=True)
    if number in reg.ON_PLAY:
        reg.ON_PLAY[number](game, batch, player, slot)


# ---------------------------------------------------------------- 勝敗

def _game_over(game: Game, batch: list[dict], winner: int, reason: str) -> None:
    st = game.state
    if st.phase == GAME_OVER:
        return
    st.phase = GAME_OVER
    st.winner = winner
    st.end_reason = reason
    st.pending = None
    st.battle = None
    st.battle_in = None
    game.emit(batch, "game_ended", winner=winner, reason=reason)


def _check_victory(game: Game, batch: list[dict]) -> None:
    for p in (0, 1):
        if game.state.players[p].book_exhausted():
            _game_over(game, batch, winner=1 - p, reason="book_out")
            return
