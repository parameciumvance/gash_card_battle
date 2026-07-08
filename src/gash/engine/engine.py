"""遊戲引擎:指令進 → 驗證 → 狀態轉移 → 事件列表出。

規則依據 ref/raw/rule3.md。所有非法指令拋出 IllegalCommand(code),狀態不變。
"""

from __future__ import annotations

import random

from .cards import EVENT, MAMODO, PARTNER, SPELL, CardDef, card_db
from .effects import registry as reg
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
    # P-011:魔力視為 0(優先於一切加成)
    if any(m.kind == "power_zero" and m.active(game.state.turn_no)
           and m.target_player == player and m.target_slot == slot.uid
           for m in game.state.modifiers):
        return 0
    base = game.db[slot.top].power_base or 0
    total = base
    for number, fn in reg.STATIC_POWER.items():
        for s in game.state.players[player].slots:
            if s.top == number:
                total += fn(game, player, slot)
                break
    for m in game.state.modifiers:
        if (m.kind == "power" and m.active(game.state.turn_no)
                and m.target_player == player and m.target_slot == slot.uid):
            total += m.amount
        # E-023:所有裝有夥伴的魔物 +N
        if (m.kind == "power_partnered" and m.active(game.state.turn_no)
                and m.target_player == player and slot.partner):
            total += m.amount
    return max(0, total)  # S-033 等減值效果不使魔力低於 0


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
    """S-037/038/041:自己魔本與所有魔物本回合不受傷害與負傷。"""
    return any(m.kind == "full_immune" and m.target_player == player
               and m.active(game.state.turn_no) for m in game.state.modifiers)


def injure_or_discard(game: Game, batch: list[dict], player: int, slot: MamodoSlot,
                      reason: str) -> None:
    """效果直接負傷 1 隻魔物(已負傷則入墓);尊重 M-031 免疫。"""
    immunity = reg.DAMAGE_IMMUNITY.get(slot.top)
    if immunity and immunity(game, player, slot, {"source": reason}):
        game.emit(batch, "damage_prevented", player=player, slot=slot.uid, reason="immunity")
        return
    if _full_immune(game, player):
        game.emit(batch, "damage_prevented", player=player, slot=slot.uid, reason="immune")
        return
    if slot.injured:
        _discard_slot(game, batch, player, slot, reason=reason)
    else:
        slot.injured = True
        game.emit(batch, "mamodo_injured", player=player, slot=slot.uid, card=slot.top)


def spell_cost(game: Game, player: int, page: int, card: CardDef) -> int:
    ps = game.state.players[player]
    cost = card.cost or 0
    if page == BOOK_SIZE and ps.pos == BOOK_SIZE:
        cost = 0  # ADV:最後一頁的術本來費用為 0
    for m in game.state.modifiers:
        if (m.kind == "spell_cost_zero" and m.target_player == player
                and m.active(game.state.turn_no)
                and card.related_mamodo == m.data.get("mamodo")):
            cost = 0
    for sb in game.state.standby:
        if (sb.kind == "spell_bonus" and sb.owner == player
                and card.related_mamodo == sb.data.get("mamodo")):
            cost += sb.data.get("cost_delta", 0)
    return max(0, cost)


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
        if game.db[n].name_en == card.name_en
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
        raise IllegalCommand("flip.too_far", "不能翻超過魔本最後一頁")
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
    elif ctype == "use_book_card":
        _use_book_card(game, batch, player, command)
    elif ctype == "declare_attack":
        _declare_attack(game, batch, player, command)
    else:
        raise IllegalCommand("command.unknown", f"未知指令 {ctype}")


def _require_open_page(game: Game, player: int, page) -> str:
    ps = game.state.players[player]
    if not isinstance(page, int) or page not in ps.open_pages():
        raise IllegalCommand("page.not_open", "該頁未翻開或卡片已不在魔本中")
    return ps.card_at(page)


def _play_card(game: Game, batch: list[dict], player: int, command: dict) -> None:
    st = game.state
    ps = st.players[player]
    number = _require_open_page(game, player, command.get("page"))
    card = game.db[number]
    if card.type == MAMODO:
        if number in reg.STACK_ON:
            if number in reg.SPELL_ONLY_STACK:
                raise IllegalCommand("play.spell_only", "此卡只能經由指定術卡疊放")
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
            raise IllegalCommand("play.partner_exists", "該魔物已裝有夥伴卡")
        if same_name_in_play(game, player, card):
            raise IllegalCommand("play.same_name", "同名夥伴已在場上")
        target.partner = number
        ps.consumed_pages.add(command["page"])
        game.emit(batch, "card_played", player=player, card=number, slot=target.uid, zone="partner")
        if number in reg.ON_PLAY:
            reg.ON_PLAY[number](game, batch, player, target)
    else:
        raise IllegalCommand("play.not_field_card", "只能放出魔物或夥伴卡")


def _use_field_ability(game: Game, batch: list[dict], player: int, command: dict, in_battle: bool) -> None:
    st = game.state
    zone = command.get("zone")
    slot = st.slot_by_uid(player, command.get("slot_uid", -1))
    borrow = None
    if slot is None and zone == "partner":
        # E-010:借用對手夥伴卡的效果(一回合一次、效果解決後不棄掉)
        opp_slot = st.slot_by_uid(1 - player, command.get("slot_uid", -1))
        if opp_slot is not None and opp_slot.partner:
            for m in st.modifiers:
                if (m.kind == "borrow_partner" and m.owner == player
                        and m.active(st.turn_no)
                        and m.data.get("slot_uid") == opp_slot.uid
                        and not m.data.get("used")):
                    borrow, slot = m, opp_slot
                    break
    if zone not in ("mamodo", "partner") or slot is None:
        raise IllegalCommand("ability.target", "找不到指定的場上卡片")
    number = slot.top if zone == "mamodo" else slot.partner
    if number is None:
        raise IllegalCommand("ability.target", "該魔物未裝夥伴卡")
    spec = reg.ACTIVATED.get(number)
    if spec is None:
        raise IllegalCommand("ability.none", f"{number} 沒有可啟動的效果")
    if zone == "partner" and restricted(game, player, NO_PARTNER_EFFECTS):
        raise IllegalCommand("ability.partner_restricted", "夥伴卡效果目前失效")
    if zone == "mamodo" and restricted(game, player, NO_MAMODO_EFFECTS):
        raise IllegalCommand("ability.mamodo_restricted", "魔物卡效果本回合失效")
    if zone == "mamodo" and slot_restricted(game, player, MAMODO_LOCKED, slot.uid):
        raise IllegalCommand("ability.mamodo_locked", "此魔物的效果本回合被封鎖")
    if spec.timing == "battle" and not in_battle:
        raise IllegalCommand("ability.timing", "此效果只能在戰鬥中使用")
    if spec.timing == "nonbattle" and in_battle:
        raise IllegalCommand("ability.timing", "此效果不能在戰鬥中使用")
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
    if borrow is not None:
        borrow.data["used"] = True
    if spec.mode == "discard" and borrow is None:
        if zone == "partner":
            slot.partner = None
            to_discard(st.players[player], number)
            game.emit(batch, "card_discarded", player=player, card=number, zone="partner", reason="cost")
        else:
            raise IllegalCommand("ability.mode", "此卡不能以棄掉方式啟動")
    game.emit(batch, "ability_used", player=player, card=number, slot=slot.uid, zone=zone)
    spec.handler(game, batch, player, slot)
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
        # 第一彈無「非戰鬥」術;保留擴充點
        raise IllegalCommand("spell.not_nonbattle", "此術卡沒有非戰鬥圖示")
    else:
        raise IllegalCommand("book.not_usable", "此卡不能留在魔本中使用")


# ---------------------------------------------------------------- 戰鬥開始確認

def _spell_any_page_standby(game: Game, player: int, page) -> Standby | None:
    """P-015 類待命:允許自魔本任意頁使用指定名稱的術卡(每回合一次)。"""
    ps = game.state.players[player]
    if not isinstance(page, int) or not 1 <= page <= BOOK_SIZE or page in ps.consumed_pages:
        return None
    name = game.db[ps.card_at(page)].name_en
    for sb in game.state.standby:
        if sb.kind == "spell_any_page" and sb.owner == player and sb.data.get("spell_name") == name:
            return sb
    return None


def _validate_spell_declaration(game: Game, player: int, page, slot_uid, *, attack: bool) -> tuple[str, MamodoSlot]:
    st = game.state
    ps = st.players[player]
    if isinstance(page, int) and page not in ps.open_pages() and _spell_any_page_standby(game, player, page):
        number = ps.card_at(page)  # 待命允許的任意頁術卡
    else:
        number = _require_open_page(game, player, page)
    card = game.db[number]
    if card.type != SPELL:
        raise IllegalCommand("spell.not_spell", "指定的卡不是術卡")
    if attack and not card.can_attack():
        raise IllegalCommand("spell.no_attack_icon", "此術沒有攻擊圖示")
    if not attack and not card.can_defend():
        raise IllegalCommand("spell.no_defense_icon", "此術沒有防禦圖示")
    if page in st.players[player].used_spell_pages:
        raise IllegalCommand("spell.used", "此術卡本回合已使用過")
    if restricted(game, player, NO_SPELLS):
        raise IllegalCommand("spell.restricted", "目前不能使用術卡")
    if attack and restricted(game, player, NO_ATTACK_SPELL):
        raise IllegalCommand("spell.attack_restricted", "本回合不能使用術卡攻擊")
    if card.is_command_spell:
        slot = st.slot_by_uid(player, slot_uid if slot_uid is not None else -1)
        if slot is None:
            if len(st.players[player].slots) == 1:
                slot = st.players[player].slots[0]
            else:
                raise IllegalCommand("spell.need_slot", "指示術須指定使用的魔物")
    else:
        def usable_by(s: MamodoSlot) -> bool:
            if game.db[s.top].related_mamodo == card.related_mamodo:
                return True
            compat = reg.SPELL_COMPAT.get(s.top)  # M-023/M-029 術相容性擴充
            return bool(compat and compat(game, player, s, card))
        explicit = st.slot_by_uid(player, slot_uid) if slot_uid is not None else None
        if explicit is not None and usable_by(explicit):
            slot = explicit
        else:
            slot = next((s for s in st.players[player].slots if usable_by(s)), None)
        if slot is None:
            raise IllegalCommand("spell.no_mamodo", "對應此術的魔物不在自己場上")
    if slot_restricted(game, player, MAMODO_LOCKED, slot.uid):
        raise IllegalCommand("spell.mamodo_locked", "此魔物本回合不能使用術卡")
    cost = spell_cost(game, player, page, card)
    if st.players[player].mp < cost:
        raise IllegalCommand("spell.mp", "MP 不足")
    return number, slot


def _validate_mamodo_attack(game: Game, player: int, slot_uid) -> tuple[MamodoSlot, dict]:
    """無術攻擊(M-027):驗證魔物已註冊直接攻擊效果且可支付費用。"""
    st = game.state
    slot = st.slot_by_uid(player, slot_uid if slot_uid is not None else -1)
    if slot is None:
        raise IllegalCommand("attack.no_slot", "找不到指定的場上魔物")
    spec = reg.MAMODO_ATTACK.get(slot.top)
    if spec is None:
        raise IllegalCommand("attack.no_mamodo_attack", "此魔物不能不用術卡直接攻擊")
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
    st.battle_in = {"attacker": player, "page": command["page"], "spell": number, "slot": slot.uid}
    game.emit(batch, "battle_in_check", attacker=player, spell=number, slot=slot.uid)


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
    raise IllegalCommand("battle_in.invalid", "只能讓過(進入戰鬥)或插入 1 個行動")


# ---------------------------------------------------------------- 戰鬥

def _consume_standby(game: Game, kind: str, predicate) -> list[Standby]:
    hits = [s for s in game.state.standby if s.kind == kind and predicate(s)]
    for s in hits:
        game.state.standby.remove(s)
    return hits


def _start_battle(game: Game, batch: list[dict], bi: dict) -> None:
    st = game.state
    if bi.get("mamodo_attack"):
        _start_mamodo_battle(game, batch, bi)
        return
    attacker, page, number, slot_uid = bi["attacker"], bi["page"], bi["spell"], bi["slot"]
    card = game.db[number]
    # 攻擊宣告:此時再驗證一次(插入行動可能已改變盤面)
    _validate_spell_declaration(game, attacker, page, slot_uid, attack=True)
    cost = spell_cost(game, attacker, page, card)
    if page not in st.players[attacker].open_pages():  # 經 P-015 類待命自任意頁使用
        for sb in _consume_standby(game, "spell_any_page",
                                   lambda s: s.owner == attacker
                                   and s.data.get("spell_name") == card.name_en):
            game.emit(batch, "standby_resolved", card=sb.source, kind=sb.kind)
    st.players[attacker].used_spell_pages.add(page)
    pay_mp(game, batch, attacker, cost, f"spell:{number}")
    battle = BattleState(attacker=attacker, step=STEP_DEFENSE,
                         attack_page=page, attack_spell=number, attack_slot=slot_uid)
    st.battle = battle
    game.emit(batch, "battle_started", attacker=attacker, spell=number, slot=slot_uid)

    slot = st.slot_by_uid(attacker, slot_uid)
    mamodo_name = game.db[slot.top].related_mamodo if slot else None
    # 待命:術卡加成(M-008 減費減魔力 / P-007 加魔力)
    for sb in _consume_standby(game, "spell_bonus",
                               lambda s: s.owner == attacker and (
                                   s.data.get("mamodo") in (None, card.related_mamodo, mamodo_name))):
        battle.data["attack_spell_bonus"] = battle.data.get("attack_spell_bonus", 0) + sb.data.get("power_delta", 0)
        game.emit(batch, "standby_resolved", card=sb.source, kind=sb.kind)
    # 待命:攻擊不可被防禦(P-001 / S-019 / S-026)
    for sb in _consume_standby(game, "attack_undefendable",
                               lambda s: s.owner == attacker and (
                                   s.data.get("mamodo") in (None, mamodo_name))):
        battle.attack_undefendable = True
        game.emit(batch, "standby_resolved", card=sb.source, kind=sb.kind)
    # 待命:本場戰鬥不能庇護魔本(E-013)
    for sb in _consume_standby(game, "no_protect_book", lambda s: s.owner == attacker):
        battle.data["no_protect_book"] = True
        game.emit(batch, "standby_resolved", card=sb.source, kind=sb.kind)
    # 待命:下一張攻擊術獲勝改為負傷對手魔物(S-057)
    for sb in _consume_standby(game, "injure_instead", lambda s: s.owner == attacker):
        battle.data["injure_instead"] = True
        game.emit(batch, "standby_resolved", card=sb.source, kind=sb.kind)
    # 宣告時效果(擲硬幣等於宣告時確定)
    rider = reg.SPELL_RIDERS.get(number)
    if rider and rider.on_declare:
        rider.on_declare(game, batch, attacker, "attack")


def _start_mamodo_battle(game: Game, batch: list[dict], bi: dict) -> None:
    """無術攻擊(M-027):合計魔力與傷害為卡片指定固定值,其餘戰鬥流程相同。"""
    st = game.state
    attacker, slot_uid = bi["attacker"], bi["slot"]
    slot, spec = _validate_mamodo_attack(game, attacker, slot_uid)  # 插入行動可能已改變盤面
    pay_mp(game, batch, attacker, spec["mp_cost"], f"mamodo_attack:{slot.top}")
    battle = BattleState(attacker=attacker, step=STEP_DEFENSE,
                         attack_page=None, attack_spell=None, attack_slot=slot_uid)
    battle.data["attack_fixed_power"] = spec["power"]
    battle.data["attack_fixed_damage"] = spec["damage"]
    st.battle = battle
    game.emit(batch, "battle_started", attacker=attacker, spell=None,
              mamodo=slot.top, slot=slot_uid)
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
            page = command["page"]
            card = game.db[number]
            cost = spell_cost(game, player, page, card)
            if page not in st.players[player].open_pages():
                for sb in _consume_standby(game, "spell_any_page",
                                           lambda s: s.owner == player
                                           and s.data.get("spell_name") == card.name_en):
                    game.emit(batch, "standby_resolved", card=sb.source, kind=sb.kind)
            st.players[player].used_spell_pages.add(page)
            pay_mp(game, batch, player, cost, f"spell:{number}")
            battle.defense_page = page
            battle.defense_spell = number
            battle.defense_slot = slot.uid
            battle.defense_declared = True
            game.emit(batch, "defense_declared", player=player, spell=number, slot=slot.uid)
            mamodo_name = game.db[slot.top].related_mamodo
            for sb in _consume_standby(game, "spell_bonus",
                                       lambda s: s.owner == player and (
                                           s.data.get("mamodo") in (None, card.related_mamodo, mamodo_name))):
                battle.data["defense_spell_bonus"] = battle.data.get("defense_spell_bonus", 0) + sb.data.get("power_delta", 0)
                game.emit(batch, "standby_resolved", card=sb.source, kind=sb.kind)
            rider = reg.SPELL_RIDERS.get(number)
            if rider and rider.on_declare:
                rider.on_declare(game, batch, player, "defense")
            _enter_effects_step(game, batch)
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
        if ctype == "use_field_ability":
            _use_field_ability(game, batch, player, command, in_battle=True)
            battle.effect_passes = 0
            if st.battle is not None:
                if st.pending is None:
                    battle.data["effect_turn"] = 1 - player
                else:
                    battle.data["pending_flip"] = player  # 決策解決後再輪替
            return
        raise IllegalCommand("battle.invalid", "戰鬥中只能使用帶戰鬥圖示的效果或 pass")
    raise IllegalCommand("battle.step", "戰鬥狀態異常")


def _enter_effects_step(game: Game, batch: list[dict]) -> None:
    battle = game.state.battle
    battle.step = STEP_EFFECTS
    battle.effect_passes = 0
    battle.data["effect_turn"] = battle.attacker  # 攻方先使用效果
    game.emit(batch, "battle_effects_step", attacker=battle.attacker)


def _side_total(game: Game, battle: BattleState, side: str) -> int:
    if side == "attack":
        if battle.attack_negated:
            return 0
        if battle.attack_spell is None:  # 無術攻擊:固定合計魔力
            return battle.data.get("attack_fixed_power", 0)
        player, slot_uid, spell = battle.attacker, battle.attack_slot, battle.attack_spell
        bonus = battle.data.get("attack_spell_bonus", 0)
    else:
        if not battle.defense_spell or battle.defense_negated:
            return 0
        player, slot_uid, spell = battle.defender, battle.defense_slot, battle.defense_spell
        bonus = battle.data.get("defense_spell_bonus", 0)
    card = game.db[spell]
    slot = game.state.slot_by_uid(player, slot_uid)
    mamodo = slot_power(game, player, slot) if slot else 0
    spell_pw = 0 if card.power_special else (card.power_bonus or 0)
    # 術自身的防禦加值(S-016/S-017)
    if side == "defense":
        spell_pw += battle.data.get("defense_self_bonus", 0)
    return mamodo + spell_pw + bonus


def _attack_damage_amount(game: Game, battle: BattleState) -> int:
    if battle.attack_spell is None:  # 無術攻擊:固定傷害
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
    if rider and rider.damage_cap is not None:  # 傷害上限(S-032/S-034)
        total = min(total, rider.damage_cap)
    return max(0, total)


def _resolve_showdown(game: Game, batch: list[dict]) -> None:
    st = game.state
    battle = st.battle
    att = _side_total(game, battle, "attack")
    deff = _side_total(game, battle, "defense")
    battle.data["attack_total"] = att  # 供傷害免疫等查詢型 hook 使用(M-031)
    attacker_wins = (not battle.attack_negated) and att > deff
    game.emit(batch, "showdown", attacker_total=att, defender_total=deff,
              winner="attacker" if attacker_wins else "defender",
              attack_negated=battle.attack_negated)
    rider = reg.SPELL_RIDERS.get(battle.attack_spell) if battle.attack_spell else None
    if attacker_wins:
        if rider and rider.on_win:
            rider.on_win(game, batch, battle.attacker)
        if st.phase == GAME_OVER:
            return
        # 獲勝時負傷代替魔本傷害(S-058 / S-057 待命旗標)
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
    """獲勝時使對手 1 隻魔物負傷代替魔本傷害;攻方選擇目標,無目標則無效果。"""
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
        options=[{"value": s.uid, "card": s.top} for s in targets], data={"ctx": ctx})
    game.emit(batch, "choice_required", kind="injure_instead_target", player=battle.attacker)


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


def _end_battle(game: Game, batch: list[dict]) -> None:
    st = game.state
    st.modifiers = [m for m in st.modifiers if m.duration != DUR_BATTLE]
    st.battle = None
    game.emit(batch, "battle_ended")
    if st.phase == GAME_OVER:
        return
    st.action_player = st.turn_player
    st.consecutive_passes = 0


# ---------------------------------------------------------------- 傷害系統

def _eligible_protectors(game: Game, item: dict) -> list[MamodoSlot]:
    """可庇護此項傷害的魔物。魔本傷害:任何自己魔物;魔物傷害:其他魔物。"""
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
        if len(ctx["items"]) > 1:
            # 多項傷害:受方決定順序(第一彈僅庇護鏈會出現,仍保留通用機制)
            receiver = ctx["items"][0]["player"]
            st.pending = PendingChoice(
                kind="damage_order", player=receiver, source=ctx.get("source"),
                options=[{"index": i, "item": it} for i, it in enumerate(ctx["items"])],
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
                + [{"value": s.uid, "card": s.top} for s in protectors],
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
    if _full_immune(game, player):  # S-037/038/041:自己魔本與所有魔物不受傷害/負傷
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
    # 查詢型免疫(M-031:不受合計魔力 6000 以下術卡的傷害與負傷)
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
    # S-031 バオウ:因此術負傷的魔物直接入墓
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
        # 防禦方以帶 on_defense_damaged 的術防禦卻仍被造成傷害(S-056)
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
    """P-012 雪莉:對自己布拉哥攻擊傷害進行庇護的魔物,承受後直接入墓。"""
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
            raise IllegalCommand("choose.invalid", "無效的庇護對象")
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
                + [{"value": s.uid, "card": s.top} for s in protectors],
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
    # M-030 ヨポポ待命:本回合結束不翻魔本頁直接結束
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
                  if not (s.data.get("expires", "turn") == "turn" and s.created_turn == st.turn_no)
                  and not (s.created_turn < st.turn_no)]
    for p in st.players:
        p.used_spell_pages.clear()
        p.used_abilities.clear()
        p.used_event_this_turn = False
        p.discarded_this_turn.clear()
        p.page_effect_used = False
        p.page_back_effect_used = False
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
    """ADV:結束階段場上無魔物 → 從魔本強制放出。回傳 True 表示已完成(未中斷)。"""
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
                options=[{"page": p, "card": ps.card_at(p)} for p in candidates],
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
