"""遊戲引擎:指令進 → 驗證 → 狀態轉移 → 事件列表出。

規則依據 ref/raw/rule3.md。所有非法指令拋出 IllegalCommand(code),狀態不變。
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
import random

from .cards import EVENT, MAMODO, PARTNER, SPELL, CardDef, card_db
from .effects import registry as reg
from .effects.primitives import (
    add_spell_power, can_stack_on, family, mamodo_name, page_option, run_on_play, slot_option, stack_base,
)
from .state import (
    BATTLE, BOOK_SIZE, DUR_BATTLE, DUR_NEXT_TURN, DUR_TURN, DUR_UNTIL_END_NEXT_TURN,
    DUR_UNTIL_END_OWN_NEXT_TURN, GAME_OVER, MAMODO_LOCKED, MAX_FIELD_MAMODO, NO_ATTACK_SPELL, NO_DEFENSE,
    NO_ATTACK, NO_DEFENSE_SPELL_SLOT, NO_EFFECTS_AND_SPELLS, NO_EVENTS, NO_MAMODO_EFFECTS, NO_NAMED_SPELLS,
    NO_PARTNER_EFFECTS, NO_PROTECT_BOOK, NO_PROTECT_SLOT, NO_SPELLS, ONLY_MAMODO, PROTECT_ONLY, SETUP, START, STEP_DEFENSE, STEP_EFFECTS,
    BattleState, Game, GameState, MamodoSlot, Modifier, PendingChoice, PlayerState, Standby,
    place_slot,
)


class IllegalCommand(Exception):
    def __init__(self, code: str, message: str = ""):
        super().__init__(f"{code}{': ' + message if message else ''}")
        self.code = code


# ---------------------------------------------------------------- 建立對局

def new_game(deck_pages: list[str] | tuple[str, ...], seed: int | None = None,
             db: dict[str, CardDef] | None = None,
             decks: tuple[list[str], list[str]] | None = None, first_player: int | None = None) -> Game:
    """準備階段:雙方放出第 1 頁魔物、翻開第 2-3 頁(MP+2)、擲硬幣決定先攻。
    first_player 指定時不擲硬幣(自由調查時間固定玩家 1 先攻)。"""
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
        place_slot(ps.slots, slot)
        ps.consumed_pages.add(1)
        game.emit(batch, "card_played", player=p, card=number, slot=slot.uid, zone="mamodo")
        run_on_play(game, batch, p, slot, number)
    for p in (0, 1):
        players[p].pos = 2
        players[p].mp = 2
        game.emit(batch, "pages_flipped", player=p, count=1, pos=2, mp_gained=2)

    if first_player is None:
        first = game.rng.randint(0, 1)
        game.emit(batch, "coin_flipped", player=first, result="first_player", source="setup")
    else:
        first = first_player
        game.emit(batch, "first_player_set", player=first, reason="local")
    game.state.turn_player = first
    game.state.phase = START
    game.emit(batch, "turn_started", turn=1, player=first)
    return game


# ---------------------------------------------------------------- 共用查詢

def slot_power(game: Game, player: int, slot: MamodoSlot) -> int:
    return power_breakdown(game, player, slot)[0]


def _item(kind: str, source: str | None, amount: int) -> dict:
    return {"kind": kind, "source": source, "amount": amount}


def power_breakdown(game: Game, player: int, slot: MamodoSlot, _visited: frozenset = frozenset(),
                    _raw: bool = False) -> tuple[int, list[dict]]:
    """魔物魔力與逐項明細;各項 amount 加總恆等於魔力(「設為 X」「不低於 0」寫成調整項)。
    「魔力を X にする」(P-011 / M-035,modifier kind="power_set"):最後發動的仍有效者勝出,完全不計加減;
    M-035 的 X 隨時取對象當下的魔力,複製關係繞回已走過的魔物時取那隻不計設定的魔力。"""
    st = game.state
    items = [_item("mamodo", slot.top, game.db[slot.top].power_base or 0)]
    for number, fn in reg.STATIC_POWER.items():
        for s in st.players[player].slots:
            # 同卡號多張在場(同名上限有例外時)各自生效;被「使えない」擋下的那張不計
            if s.top == number and not card_effect_blocked(game, player, s, number):
                amount = fn(game, player, slot)
                if amount:
                    items.append(_item("static", number, amount))
    for m in st.modifiers:
        if (m.kind == "power" and m.active(st.turn_no)
                and m.target_player == player and m.target_slot == slot.uid
                and (m.data.get("when") != "attacking" or _attacking_with(game, player, slot))):
            items.append(_item("modifier", m.source, m.amount))
        # E-023:所有裝有搭檔的魔物 +N
        if (m.kind == "power_partnered" and m.active(st.turn_no)
                and m.target_player == player and slot.partner):
            items.append(_item("partnered", m.source, m.amount))
        # E-048:所有魔物 +N × 當下自己場上的魔物數(每次查詢重算)
        if m.kind == "power_per_own_mamodo" and m.active(st.turn_no) and m.target_player == player:
            items.append(_item("per_mamodo", m.source, m.amount * len(st.players[player].slots)))
    raw = sum(i["amount"] for i in items)
    if not _raw:
        visited = _visited | {(player, slot.uid)}
        sets = [m for m in st.modifiers
                if m.kind == "power_set" and m.active(st.turn_no)
                and m.target_player == player and m.target_slot == slot.uid]
        for m in reversed(sets):
            value = _power_set_value(game, m, visited)
            if value is None:
                continue   # M-035 的對象已離場:這個設定失效
            items.append(_item("power_set", m.source, value - raw))
            return value, items
    if raw < 0:  # S-033 等減值效果不使魔力低於 0
        items.append(_item("mamodo_floor", None, -raw))
    return max(0, raw), items


def _power_set_value(game: Game, m: Modifier, visited: frozenset) -> int | None:
    """「設為 X」的 X:固定值(P-011),或對象魔物當下的魔力(M-035;對象離場時 None)。"""
    if "copy_slot" not in m.data:
        return m.data.get("value", 0)
    owner, uid = m.data["copy_player"], m.data["copy_slot"]
    target = game.state.slot_by_uid(owner, uid)
    if target is None:
        return None
    if (owner, uid) in visited:   # 繞回已走過的魔物:取那隻不計設定的魔力
        return power_breakdown(game, owner, target, _raw=True)[0]
    return power_breakdown(game, owner, target, visited)[0]


def _attacking_with(game: Game, player: int, slot: MamodoSlot) -> bool:
    """目前戰鬥是 player 以這隻魔物攻擊(M-052「この魔物で攻撃するバトル中」)。"""
    b = game.state.battle
    return b is not None and b.attacker == player and b.attack_slot == slot.uid


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


# ---------------------------------------------------------------- 限制的分類(card-effects「限制效果的分類」)

# restriction 旗標 → 分類;無視與移除(M-038、M-042 / E-031、P-034、E-036)都依這張表
RESTRICTION_CATEGORIES = {
    NO_SPELLS: {"spells"},
    NO_ATTACK_SPELL: {"spells"},
    NO_MAMODO_EFFECTS: {"mamodo_effects"},
    MAMODO_LOCKED: {"spells", "mamodo_effects"},
    NO_EFFECTS_AND_SPELLS: {"spells", "mamodo_effects"},
    ONLY_MAMODO: {"spells", "mamodo_effects", "protect"},
    PROTECT_ONLY: {"protect"},
    NO_DEFENSE_SPELL_SLOT: {"spells"},
    NO_NAMED_SPELLS: {"spells"},
    NO_PROTECT_SLOT: {"protect"},
}
# 待命種類 → 分類(作用於待命擁有者的對手);待命也可在 data["restricts"] 自帶分類(S-074)
STANDBY_CATEGORIES = {"no_protect_book": {"protect"}}


def _restrictions(game: Game, player: int):
    st = game.state
    return [m for m in st.modifiers
            if m.kind == "restriction" and m.target_player == player and m.active(st.turn_no)]


def spell_block(game: Game, player: int, slot: MamodoSlot | None, *, attack: bool = False,
                card: CardDef | None = None, defense: bool = False) -> str | None:
    """「術を使えない」:player 以 slot 使用戰術被擋時回傳錯誤碼,否則 None。
    由 M-038 等(reg.IGNORE_SPELL_BLOCK)使用的戰術不受限。card 指定時另看限定家族的封鎖(PR-009),
    defense 時另看限定魔物的防禦戰術封鎖(P-043)。"""
    if slot is not None and slot.top in reg.IGNORE_SPELL_BLOCK:
        return None
    for m in _restrictions(game, player):
        if m.flag == NO_EFFECTS_AND_SPELLS or (m.flag == NO_SPELLS and (
                m.target_slot is None or (slot is not None and m.target_slot == slot.uid))):   # E-047:只限選定魔物
            return "spell.restricted"
        if m.flag == NO_NAMED_SPELLS and card is not None and card.related_mamodo == m.data.get("mamodo"):
            return "spell.restricted"
        if m.flag == NO_DEFENSE_SPELL_SLOT and defense and slot is not None and m.target_slot == slot.uid:
            return "spell.restricted"
        if m.flag == NO_ATTACK_SPELL and attack and (m.target_slot is None
                                                      or (slot is not None and m.target_slot == slot.uid)):
            return "spell.attack_restricted"   # P-033:target_slot 指定時只限那隻魔物
        if slot is not None and ((m.flag == MAMODO_LOCKED and m.target_slot == slot.uid)
                                 or (m.flag == ONLY_MAMODO and m.target_slot != slot.uid)):
            return "spell.mamodo_locked"
    return None


def _mamodo_effect_blocks(game: Game, player: int, slot: MamodoSlot) -> list[tuple[str, str]]:
    """擋下這隻魔物「魔物の効果」的所有(錯誤碼, 來源卡號):P-031 家族禁止、全體限制、只限這隻 / 選定以外的限制。"""
    fam = family(game, slot)
    out = [("mamodo_restricted", number) for number, (blocked, _) in _opponent_family_blocks(game, player)
           if blocked == fam]   # P-031:常駐效果,不是限制,不能被移除
    for m in _restrictions(game, player):
        if m.flag in (NO_MAMODO_EFFECTS, NO_EFFECTS_AND_SPELLS):
            out.append(("mamodo_restricted", m.source))
        elif (m.flag == MAMODO_LOCKED and m.target_slot == slot.uid) or (m.flag == ONLY_MAMODO
                                                                          and m.target_slot != slot.uid):
            out.append(("mamodo_locked", m.source))
    return out


def mamodo_effect_block(game: Game, player: int, slot: MamodoSlot) -> str | None:
    """「魔物の効果を使えない」:被擋時回傳 "mamodo_restricted"(全體或家族)/ "mamodo_locked"(這隻),否則 None。"""
    blocks = _mamodo_effect_blocks(game, player, slot)
    return blocks[0][0] if blocks else None


def effect_block_sources(game: Game, player: int, slot: MamodoSlot, number: str) -> list[str]:
    """「このカードが場にある→」的效果被「使えない」擋下時,造成限制的來源卡號(依限制的建立順序、去重);
    沒被擋時為空。number 是 slot 的搭檔時看「パートナーの効果を使えない」,否則看這隻魔物的「魔物の効果を使えない」。"""
    if number == slot.partner:
        sources = [m.source for m in _restrictions(game, player) if m.flag == NO_PARTNER_EFFECTS]
    else:
        sources = [source for _, source in _mamodo_effect_blocks(game, player, slot)]
    return list(dict.fromkeys(sources))


def note_effect_blocked(game: Game, batch: list[dict], player: int, slot: MamodoSlot, number: str, when: str) -> bool:
    """一次性時點(出場、入墓、開始階段、傷害免疫)的常駐效果被「使えない」擋下時發出 effect_blocked,回傳是否被擋。"""
    sources = effect_block_sources(game, player, slot, number)
    if sources:
        game.emit(batch, "effect_blocked", player=player, card=number, slot=slot.uid, by=sources, when=when)
    return bool(sources)


def card_effect_blocked(game: Game, player: int, slot: MamodoSlot, number: str) -> bool:
    """「このカードが場にある→」的效果被「使えない」擋下(官方規則書第 42 頁)。專用規則不經過這裡。"""
    return bool(effect_block_sources(game, player, slot, number))


def _opponent_family_blocks(game: Game, player: int) -> list[tuple[str, tuple[str, str]]]:
    """對手場上(搭檔或魔物)有 P-031 類卡、且其效果沒被禁止時:[(該卡號, (被禁止的家族, 事件卡名))]。"""
    opp = 1 - player
    out = []
    for s in game.state.players[opp].slots:
        if s.partner in reg.BLOCK_OPPONENT_FAMILY and not restricted(game, opp, NO_PARTNER_EFFECTS):
            out.append((s.partner, reg.BLOCK_OPPONENT_FAMILY[s.partner]))
    return out


def _opponent_event_locks(game: Game, player: int) -> list[str]:
    """對手的戰鬥階段中,對手場上使 player 不能使用事件卡的搭檔(P-038;常駐效果,被「使えない」擋下時不算)。"""
    st = game.state
    opp = 1 - player
    if st.phase != BATTLE or st.turn_player != opp:
        return []
    return [s.partner for s in st.players[opp].slots
            if s.partner in reg.OPPONENT_EVENT_LOCK and not card_effect_blocked(game, opp, s, s.partner)]


def attack_undefendable(game: Game, battle: BattleState) -> bool:
    """此攻擊不能被防禦:旗標(S-019 / P-001 等),或 M-048 的待命且攻擊的合計魔力達門檻(宣告時確定)。"""
    if battle.attack_undefendable:
        return True
    return any(sb.kind == "undefendable_at_total" and sb.owner == battle.attacker
               and sb.data.get("slot_uid") == battle.attack_slot
               and _side_total(game, battle, "attack") >= sb.data.get("min_total", 0)
               for sb in game.state.standby)


def _protect_anyway(game: Game, player: int, slot: MamodoSlot) -> bool:
    """M-042 / E-031:「かばうことができない」時仍可以這隻魔物保護。"""
    st = game.state
    return any(m.kind == "protect_anyway" and m.target_player == player and m.active(st.turn_no)
               and m.target_slot in (None, slot.uid) for m in st.modifiers)


def remove_restrictions(game: Game, batch: list[dict], player: int, categories: set, whose: str) -> list[str]:
    """移除持續或待命中、屬於 categories 的限制(整個效果移除)。whose:"self"=只移除作用於 player 的,
    "both"=雙方。回傳被移除效果的來源卡(P-034 / E-036)。"""
    st = game.state
    targets = {player} if whose == "self" else {0, 1}
    removed = [m for m in st.modifiers
               if m.kind == "restriction" and m.target_player in targets
               and RESTRICTION_CATEGORIES.get(m.flag, set()) & categories]
    standbys = [sb for sb in st.standby
                if 1 - sb.owner in targets
                and (STANDBY_CATEGORIES.get(sb.kind, set()) | set(sb.data.get("restricts", ()))) & categories]
    st.modifiers = [m for m in st.modifiers if m not in removed]
    st.standby = [sb for sb in st.standby if sb not in standbys]
    sources = [m.source for m in removed] + [sb.source for sb in standbys]
    game.emit(batch, "restrictions_removed", player=player, sources=sources)
    return sources


def event_limit(game: Game, player: int) -> int:
    """本回合可使用的事件卡張數:1,或效果提高後的張數(E-029:含自己 3 張)。"""
    st = game.state
    return max([1] + [m.amount for m in st.modifiers
                      if m.kind == "event_limit" and m.target_player == player and m.active(st.turn_no)])


def event_cost_breakdown(game: Game, player: int, card: CardDef) -> tuple[int, list[dict]]:
    """事件卡的費用與逐項明細:卡面費用 + 對手場上 M-040 等的加成(效果被禁的不算)。"""
    items = [_item("card", card.number, card.cost or 0)]
    for s in game.state.players[1 - player].slots:
        amount = reg.OPPONENT_EVENT_COST.get(s.top, 0)
        if amount and not card_effect_blocked(game, 1 - player, s, s.top):
            items.append(_item("opponent_event", s.top, amount))
    return sum(i["amount"] for i in items), items


def event_cost(game: Game, player: int, card: CardDef) -> int:
    """事件卡的費用:卡面費用 + 對手場上 M-040 等的加成。"""
    return event_cost_breakdown(game, player, card)[0]


def reveals_open_pages(game: Game, viewer, player: int) -> bool:
    """viewer 看得到 player 翻開的頁(P-024 在 viewer 場上)。"""
    if viewer not in (0, 1) or viewer == player:
        return False
    return any(number in reg.REVEAL_OPPONENT_PAGES and not card_effect_blocked(game, viewer, s, number)
               for s in game.state.players[viewer].slots for number in (s.top, s.partner) if number)


def _full_immune(game: Game, player: int) -> str | None:
    """S-037/038/041:自己魔書與所有魔物本回合不受傷害與負傷;生效時回傳來源卡號,否則 None。"""
    return next((m.source for m in game.state.modifiers if m.kind == "full_immune" and m.target_player == player
                 and m.active(game.state.turn_no)), None)


def _named_immune(game: Game, item: dict) -> str | None:
    """PR-009:受傷害的是持有者的魔書(data["book"])或指定家族的魔物時,回傳來源卡號,否則 None。"""
    st = game.state
    player = item["player"]
    slot = st.slot_by_uid(player, item["slot_uid"]) if item["kind"] == "slot" else None
    for m in st.modifiers:
        if m.kind == "named_immune" and m.target_player == player and m.active(st.turn_no):
            if (m.data.get("book") and item["kind"] == "book") or (
                    slot is not None and mamodo_name(game, slot) == m.data.get("mamodo")):
                return m.source
    return None


def spell_cost(game: Game, player: int, page: int, card: CardDef, slot: MamodoSlot | None = None,
               *, discount: bool = True) -> int:
    """戰術卡費用。「某魔物的戰術」類的費用效果(P-005 / M-008)以「使用戰術的魔物」判定,指令戰術由該魔物
    使用時也適用。slot 為使用的魔物;未指定時(畫面顯示、非戰鬥戰術)取自己場上可使用此戰術的魔物中最低的費用。
    discount=False 時不計可選的減費(M-008「1低いコストで使うことができる」選擇不使用時)。"""
    return spell_cost_breakdown(game, player, page, card, slot, discount=discount)[0]


def spell_cost_breakdown(game: Game, player: int, page: int, card: CardDef, slot: MamodoSlot | None = None,
                         *, discount: bool = True) -> tuple[int, list[dict]]:
    """戰術卡費用與逐項明細(各項加總等於費用);使用魔物的取法同 spell_cost,未指定時取費用最低的那隻。"""
    if slot is not None:
        return _spell_cost_items(game, player, page, card, family(game, slot), discount)
    users = [s for s in game.state.players[player].slots
             if card.is_command_spell or _spell_usable_by(game, player, s, card)]
    free = [s for s in users if not spell_block(game, player, s, card=card)]
    users = free or users   # 被封鎖的魔物不能使用;全被封鎖時只作顯示
    if not users:
        return _spell_cost_items(game, player, page, card, None, discount)
    return min((_spell_cost_items(game, player, page, card, family(game, s), discount) for s in users),
               key=lambda r: r[0])


def _base_spell_cost_items(game: Game, player: int, page: int, card: CardDef,
                           mamodo_name: str | None) -> list[dict]:
    """「本来のコスト」的明細:印刷費用,經最後一頁(ADV)與 S-088 / P-005 / Ex-007 類「本来のコストを0にする」調整
    (有多個時以最後一個寫成一項調整),再加上本來費用的增減(PR-010 / Ex-035,不低於 0)。"""
    ps = game.state.players[player]
    printed = card.cost or 0
    zero = None   # (kind, source)
    if page == BOOK_SIZE and ps.pos == BOOK_SIZE:
        zero = ("last_page", None)  # ADV:最後一頁的戰術本來費用為 0
    for sb in game.state.standby:
        if sb.kind == "spell_base_cost_zero" and sb.owner == player:
            zero = ("base_zero", sb.source)  # S-088:本回合下一場戰鬥自己的戰術本来のコスト為 0
    for m in game.state.modifiers:
        if (m.kind == "spell_cost_zero" and m.target_player == player
                and m.active(game.state.turn_no)
                and mamodo_name is not None and mamodo_name == m.data.get("mamodo")):
            zero = ("base_zero", m.source)
    deltas = []
    for sb in _spell_bonus_standbys(game, player, mamodo_name):   # Ex-007 類:下一場戰鬥中該家族的戰術 1 張
        if sb.data.get("base_zero"):
            zero = ("base_zero", sb.source)
        elif sb.data.get("base_delta"):
            deltas.append(_item("base_delta", sb.source, sb.data["base_delta"]))
    deltas += [_item("base_delta", m.source, m.data["cost"])
               for m in _spell_named_modifiers(game, player, card) if m.data.get("cost")]
    items = [_item("card", card.number, printed)]
    if zero and printed:
        items.append(_item(zero[0], zero[1], -printed))
    base = sum(i["amount"] for i in items)
    for d in deltas:
        if base + d["amount"] < 0:   # 本来のコストは 0 より小さくはならない
            d = dict(d, amount=-base)
        if d["amount"]:
            items.append(d)
            base += d["amount"]
    return items


def _base_spell_cost_by(game: Game, player: int, page: int, card: CardDef, mamodo_name: str | None) -> int:
    """「本来のコスト」:印刷費用,經最後一頁(ADV)與 P-005「本来のコストを0にする」調整。"""
    return sum(i["amount"] for i in _base_spell_cost_items(game, player, page, card, mamodo_name))


def _spell_bonus_standbys(game: Game, player: int, mamodo_name: str | None) -> list[Standby]:
    return [sb for sb in game.state.standby
            if sb.kind == "spell_bonus" and sb.owner == player
            and mamodo_name is not None and mamodo_name == sb.data.get("mamodo")]


def _spell_cost_items(game: Game, player: int, page: int, card: CardDef, mamodo_name: str | None,
                      discount: bool = True) -> tuple[int, list[dict]]:
    items = _base_spell_cost_items(game, player, page, card, mamodo_name)
    for sb in _spell_bonus_standbys(game, player, mamodo_name):
        delta = sb.data.get("cost_delta", 0)
        if delta and (discount or not sb.data.get("optional")):
            items.append(_item("cost_bonus", sb.source, delta))
    cost = sum(i["amount"] for i in items)
    if cost < 0:  # 費用不低於 0
        items.append(_item("cost_floor", None, -cost))
    return max(0, cost), items


def _spell_cost_by(game: Game, player: int, page: int, card: CardDef, mamodo_name: str | None,
                   discount: bool = True) -> int:
    return _spell_cost_items(game, player, page, card, mamodo_name, discount)[0]


def _optional_discount(game: Game, player: int, page: int, card: CardDef, slot: MamodoSlot) -> bool:
    """M-008:使用的魔物有可選的減費待命,且「本来のコスト」至少 1(本来為 0 時無法「1低いコスト」)。"""
    mamodo_name = family(game, slot)
    return (any(sb.data.get("optional") for sb in _spell_bonus_standbys(game, player, mamodo_name))
            and _base_spell_cost_by(game, player, page, card, mamodo_name) >= 1)


def pay_mp(game: Game, batch: list[dict], player: int, amount: int, reason: str) -> None:
    if amount == 0:
        return
    ps = game.state.players[player]
    ps.mp -= amount
    game.emit(batch, "mp_changed", player=player, delta=-amount, mp=ps.mp, reason=reason)


def gain_mp(game: Game, batch: list[dict], player: int, amount: int, reason: str, by: int | None = None) -> None:
    """player 的 MP 增加。by 為造成增加的效果擁有者(None = 非效果);戰鬥階段中自己的效果
    不能使有 P-020 的玩家 MP 增加。"""
    if amount == 0:
        return
    from .effects.primitives import battle_phase_mp_lock
    if by == player and amount > 0 and battle_phase_mp_lock(game, player):
        game.emit(batch, "mp_gain_prevented", player=player, source=reason)
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
    """場上與 card 同名的魔物(視為另一魔物的卡依其視為的名稱,M-047)或搭檔數。"""
    slots = game.state.players[player].slots
    if card.type == MAMODO:
        return sum(1 for s in slots if mamodo_name(game, s) == card.name_ja)
    return sum(1 for s in slots if s.partner and game.db[s.partner].name_ja == card.name_ja)


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
    st.battle_phase_acted = True   # PR-005:行動成功執行後(單純 pass 不算)
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
        ps.start_phase_mp_gain = gained   # P-035
        game.emit(batch, "pages_flipped", player=player, count=count, pos=ps.pos, mp_gained=gained)
    # 開始階段效果解決(翻頁之後)
    for number, fn in list(reg.START_PHASE.items()):
        for slot in list(ps.slots):
            if slot.top == number and not note_effect_blocked(game, batch, player, slot, number, "start_phase"):
                fn(game, batch, player, slot)
    for sb in [s for s in st.standby if s.kind == "start_phase" and s.created_turn < st.turn_no
               and (not s.data.get("own_start") or s.owner == player)]:   # M-067:擁有者的開始階段
        st.standby.remove(sb)
        reg.CHOICE_RESOLVERS[sb.data["callback"]](game, batch, None, sb.data)
    st.phase = BATTLE
    st.action_player = st.turn_player
    st.consecutive_passes = 0
    st.battle_phase_acted = False
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
    elif ctype == "use_action_effect":
        _use_action_effect(game, batch, player, command)
    else:
        raise IllegalCommand("command.unknown", f"未知指令 {ctype}")


def _use_action_effect(game: Game, batch: list[dict], player: int, command: dict) -> None:
    """「1アクションを使って…捨て札にできる」(M-046 / P-020):戰鬥階段的非戰鬥中以 1 個行動棄掉自己的卡
    (規則頁「1アクションを使って」)。不是「使用效果」,不受效果限制、不觸發ジャマー。"""
    st = game.state
    zone = command.get("zone")
    slot = st.slot_by_uid(player, command.get("slot_uid", -1))
    if zone not in ("mamodo", "partner") or slot is None:
        raise IllegalCommand("action_effect.target", "找不到指定的場上卡片")
    number = slot.top if zone == "mamodo" else slot.partner
    what = reg.ACTION_DISCARD.get(number) if number else None
    if what is None or (what == "top") != (zone == "mamodo") or (what == "top" and len(slot.stack) < 2):
        raise IllegalCommand("action_effect.none", "這張卡沒有以 1 個行動使用的效果")
    game.emit(batch, "action_effect_used", player=player, card=number, slot=slot.uid, zone=zone)
    if what == "top":
        _detach_top(game, batch, player, slot, reason="action")
    else:
        slot.partner = None
        to_discard(st.players[player], number)
        game.emit(batch, "card_discarded", player=player, card=number, zone="partner", reason="action",
                  slot=slot.uid)


def _require_open_page(game: Game, player: int, page) -> str:
    ps = game.state.players[player]
    if not isinstance(page, int) or page not in ps.open_pages():
        raise IllegalCommand("page.not_open", "該頁未翻開或卡片已不在魔書中")
    return ps.card_at(page)


PLAY_BLOCK_MESSAGES = {
    "spell_only": "此卡只能經由指定戰術卡疊放",
    "no_base": "場上沒有可疊放的變身前魔物",
    "field_full": "場上魔物已達 3 隻",
    "same_name": "同名的卡已達同場上限",
    "no_mamodo": "對應魔物不在自己場上",
    "partner_exists": "該魔物已裝有搭檔卡",
    "not_field_card": "只能放出魔物或搭檔卡",
}


def partner_targets(game: Game, player: int, card) -> list[MamodoSlot]:
    """搭檔卡可裝備的魔物:對應(家族依視為的名稱,M-047)且尚未裝搭檔。"""
    return [s for s in game.state.players[player].slots
            if family(game, s) == card.related_mamodo and s.partner is None]


def play_block(game: Game, player: int, number: str) -> str | None:
    """放出 number 被擋時回傳錯誤碼(不含 "play." 前綴),否則 None。只看卡片與場面,不含時機;
    play_card 指令與快照共用(battle-api「魔書中卡片的放出可否」)。"""
    ps = game.state.players[player]
    card = game.db[number]
    if card.type == MAMODO:
        if number in reg.STACK_ON:
            if number in reg.SPELL_ONLY_STACK:
                return "spell_only"
            return None if stack_base(game, player, number) is not None else "no_base"
        if len(ps.slots) >= MAX_FIELD_MAMODO:
            return "field_full"
        if same_name_copies(game, player, card) >= reg.MAX_COPIES.get(number, 1):
            return "same_name"
        return None
    if card.type == PARTNER:
        if not any(family(game, s) == card.related_mamodo for s in ps.slots):
            return "no_mamodo"
        if not partner_targets(game, player, card):
            return "partner_exists"
        if same_name_in_play(game, player, card):
            return "same_name"
        return None
    return "not_field_card"


def _play_card(game: Game, batch: list[dict], player: int, command: dict) -> None:
    st = game.state
    ps = st.players[player]
    number = _require_open_page(game, player, command.get("page"))
    card = game.db[number]
    target = None
    if card.type == PARTNER and command.get("slot_uid") is not None:   # 指定的裝備對象先驗證(兩隻對應魔物時由玩家選)
        target = next((s for s in ps.slots if s.uid == command["slot_uid"]
                       and family(game, s) == card.related_mamodo), None)
        if target is None:
            raise IllegalCommand("play.no_mamodo", PLAY_BLOCK_MESSAGES["no_mamodo"])
        if target.partner is not None:
            raise IllegalCommand("play.partner_exists", PLAY_BLOCK_MESSAGES["partner_exists"])
    block = play_block(game, player, number)
    if block:
        raise IllegalCommand(f"play.{block}", PLAY_BLOCK_MESSAGES[block])
    if card.type == MAMODO:
        if number in reg.STACK_ON:
            base_slot = stack_base(game, player, number)
            base_slot.stack.append(number)   # 疊放繼承前身的搭檔、效果與負傷狀態
            ps.consumed_pages.add(command["page"])
            game.emit(batch, "card_played", player=player, card=number, slot=base_slot.uid, zone="mamodo", stacked=True)
            run_on_play(game, batch, player, base_slot, number)
            return
        slot = MamodoSlot(uid=st.next_uid(), stack=[number])
        place_slot(ps.slots, slot)
        ps.consumed_pages.add(command["page"])
        game.emit(batch, "card_played", player=player, card=number, slot=slot.uid, zone="mamodo")
        run_on_play(game, batch, player, slot, number)
    elif card.type == PARTNER:
        target = target or partner_targets(game, player, card)[0]   # 未指定取第一隻可裝備的
        target.partner = number
        ps.consumed_pages.add(command["page"])
        game.emit(batch, "card_played", player=player, card=number, slot=target.uid, zone="partner")
        run_on_play(game, batch, player, target, number)


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
    block = mamodo_effect_block(game, player, slot) if zone == "mamodo" else None
    if block:
        raise IllegalCommand(f"ability.{block}", "此魔物的效果目前不能使用")
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
            game.emit(batch, "card_discarded", player=player, card=number, zone="partner", reason="cost",
                      slot=slot.uid)
        else:   # 魔物卡「このカードを捨て札にする」:此魔物(連同疊放與搭檔)入墓(M-033)
            _discard_slot(game, batch, player, slot, reason="cost")
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
    any_page = (isinstance(page, int) and page not in st.players[player].open_pages()
                and _spell_any_page_standby(game, player, page) is not None
                and game.db[st.players[player].card_at(page)].type == SPELL)
    number = st.players[player].card_at(page) if any_page else _require_open_page(game, player, page)
    card = game.db[number]
    if card.type == EVENT:
        if st.players[player].events_used_this_turn >= event_limit(game, player):
            raise IllegalCommand("event.limit", "本回合已達事件卡的使用上限")
        if card.ad == "A" and player != st.turn_player:
            raise IllegalCommand("event.timing", "此事件卡只能在自己的回合使用")
        if card.ad == "D" and player == st.turn_player:
            raise IllegalCommand("event.timing", "此事件卡只能在對手的回合使用")
        if any(card.name_ja == name for _, (_, name) in _opponent_family_blocks(game, player)):
            raise IllegalCommand("event.restricted", "對手的效果使你不能使用此事件卡")
        if restricted(game, player, NO_EVENTS) or _opponent_event_locks(game, player):
            raise IllegalCommand("event.restricted", "對手的效果使你不能使用事件卡")
        handler = reg.EVENT.get(number)
        if handler is None:
            raise IllegalCommand("event.not_implemented", f"{number} 尚未實作")
        condition = reg.EVENT_CONDITION.get(number)
        if condition and not condition(game, player):
            raise IllegalCommand("event.condition", "不符合此事件卡的使用條件")
        cost = event_cost(game, player, card)
        if st.players[player].mp < cost:
            raise IllegalCommand("event.mp", "MP 不足")
        st.players[player].events_used_this_turn += 1
        pay_mp(game, batch, player, cost, f"event:{number}")
        game.emit(batch, "book_card_used", player=player, card=number, page=page)
        # ジャマー(M-032):對手可能在此事件卡結束後使其無效 → 先存解決前的快照(費用與使用次數已記)
        snapshot = copy.deepcopy(st) if _jammer_holder(game, 1 - player, "event") else None
        handler(game, batch, player, page)
        _check_victory(game, batch)
        if snapshot is not None:
            _queue_jammer(game, batch, 1 - player, number, snapshot, on="event")
    elif card.type == SPELL:
        if card.effect_icon != "nonbattle":
            raise IllegalCommand("spell.not_nonbattle", "此戰術卡沒有非戰鬥圖示")
        if card.ad == "A" and player != st.turn_player:
            raise IllegalCommand("spell.timing", "此非戰鬥戰術只能在自己的回合使用")
        if card.ad == "D" and player == st.turn_player:
            raise IllegalCommand("spell.timing", "此非戰鬥戰術只能在對手的回合使用")
        user = _nonbattle_spell_user(game, player, page, card, command.get("slot_uid"))
        reuse = page in st.players[player].used_nonbattle_pages
        if reuse and _reuse_standby(game, player, page) is None:
            raise IllegalCommand("spell.used", "此非戰鬥戰術本回合已使用過")
        handler = reg.SPELL_NONBATTLE.get(number)
        if handler is None:
            raise IllegalCommand("spell.not_implemented", f"{number} 尚未實作")
        condition = reg.SPELL_NONBATTLE_CONDITION.get(number)
        if condition and not condition(game, player):
            raise IllegalCommand("spell.condition", "不符合此戰術的使用條件(沒有可選的對象)")
        cost = 0 if reuse else spell_cost(game, player, page, card, slot=user)
        if st.players[player].mp < cost:
            raise IllegalCommand("spell.mp", "MP 不足")
        if reuse:
            _consume_reuse(game, batch, player, page)   # S-098:費用 0 再用一次
        if any_page:
            _consume_any_page(game, batch, player, page)   # P-025:從任意頁使用
        st.players[player].used_nonbattle_pages.add(page)
        _record_spell_attr(game, player, card)
        pay_mp(game, batch, player, cost, f"spell:{number}")
        game.emit(batch, "book_card_used", player=player, card=number, page=page, mamodo=user.top)
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
    card = game.db[ps.card_at(page)]
    for sb in game.state.standby:
        if sb.kind != "spell_any_page" or sb.owner != player:
            continue
        if sb.data.get("spell_name") == card.name_ja:
            return sb
        # M-037:指定家族的戰術、指定頁範圍內
        if (sb.data.get("mamodo") and card.type == SPELL and card.related_mamodo == sb.data["mamodo"]
                and page in sb.data.get("pages", ())):
            return sb
    return None


def _consume_any_page(game: Game, batch: list[dict], player: int, page: int) -> None:
    sb = _spell_any_page_standby(game, player, page)
    if sb is not None:
        game.state.standby.remove(sb)
        game.emit(batch, "standby_resolved", card=sb.source, kind=sb.kind)


def _reuse_standby(game: Game, player: int, page: int) -> Standby | None:
    """S-098 的重用待命:使用時選定的那一頁可再用一次(費用 0)。"""
    return next((sb for sb in game.state.standby
                 if sb.kind == "spell_reuse" and sb.owner == player and sb.data.get("page") == page), None)


def _consume_reuse(game: Game, batch: list[dict], player: int, page: int) -> bool:
    sb = _reuse_standby(game, player, page)
    if sb is None:
        return False
    game.state.standby.remove(sb)
    game.emit(batch, "standby_resolved", card=sb.source, kind=sb.kind)
    return True


def spell_use_limit(game: Game, player: int, card: CardDef) -> int:
    """戰術卡每張每回合可用次數:預設 1;場上有登記 SPELL_USE_LIMIT 的卡時取其最大值(M-024 二身一体)。"""
    limit = 1
    for number, fn in reg.SPELL_USE_LIMIT.items():
        if any(s.top == number and not card_effect_blocked(game, player, s, number)
               for s in game.state.players[player].slots):
            value = fn(game, player, card)
            if value is not None:
                limit = max(limit, value)
    return limit


def exhausted_spell_pages(game: Game, player: int) -> set[int]:
    """本回合已達可用次數、不能再用的戰術卡頁(依目前場面判斷)。"""
    ps = game.state.players[player]
    return {page for page, uses in ps.spell_page_uses.items()
            if uses >= spell_use_limit(game, player, game.db[ps.card_at(page)])
            and _reuse_standby(game, player, page) is None}


def _record_spell_use(game: Game, player: int, page: int) -> None:
    st = game.state
    ps = st.players[player]
    ps.spell_page_uses[page] = ps.spell_page_uses.get(page, 0) + 1
    _record_spell_attr(game, player, game.db[ps.card_at(page)])


def _record_spell_attr(game: Game, player: int, card: CardDef) -> None:
    """記錄本回合宣告過的戰術屬性(Ex-043);以宣告為準,之後被無效也算。只保留本回合與前一回合。"""
    st = game.state
    ps = st.players[player]
    ps.spell_attrs_by_turn = {t: a for t, a in ps.spell_attrs_by_turn.items() if t >= st.turn_no - 1}
    if card.attr_name:
        ps.spell_attrs_by_turn.setdefault(st.turn_no, set()).add(card.attr_name)


def _spell_usable_by(game: Game, player: int, slot: MamodoSlot, card: CardDef) -> bool:
    """此戰術卡是否可由場上這隻魔物使用(家族相符或戰術相容性擴充,如 M-023/M-029)。"""
    if family(game, slot) == card.related_mamodo:
        return True
    rule = reg.RULE_SPELL_COMPAT.get(slot.top)   # 專用規則(M-029)
    if rule and rule(game, player, slot, card):
        return True
    compat = reg.SPELL_COMPAT.get(slot.top)
    if compat and not card_effect_blocked(game, player, slot, slot.top) and compat(game, player, slot, card):
        return True
    st = game.state
    fam = family(game, slot)
    return any(m.kind == "spell_compat_attr" and m.target_player == player and m.active(st.turn_no)
               and m.data.get("mamodo") == fam and card.attr_name == m.data.get("attr")
               for m in st.modifiers)


def _nonbattle_spell_user(game: Game, player: int, page: int, card: CardDef, slot_uid) -> MamodoSlot:
    """非戰鬥戰術的使用魔物:指定時須能使用且未被 E-024 封鎖;未指定時取未被封鎖者中費用最低的第一隻。
    E-024「その魔物の…術を使えない」不分戰鬥與非戰鬥。"""
    st = game.state
    usable = [s for s in st.players[player].slots
              if card.is_command_spell or _spell_usable_by(game, player, s, card)]
    if slot_uid is not None:
        slot = st.slot_by_uid(player, slot_uid)
        if slot is None or slot not in usable:
            raise IllegalCommand("spell.no_mamodo", "指定的魔物不能使用此戰術")
        block = spell_block(game, player, slot, card=card)
        if block:
            raise IllegalCommand(block, "目前不能使用此戰術")
        return slot
    if not usable:
        raise IllegalCommand("spell.no_mamodo", "對應此戰術的魔物不在自己場上")
    free = [s for s in usable if not spell_block(game, player, s, card=card)]
    if not free:
        raise IllegalCommand(spell_block(game, player, usable[0], card=card), "目前不能使用此戰術")
    # 未指定:未被封鎖者中費用最低的第一隻(依場上順序),記在使用事件中
    return min(free, key=lambda s: spell_cost(game, player, page, card, slot=s))


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
    if (st.players[player].spell_page_uses.get(page, 0) >= spell_use_limit(game, player, card)
            and _reuse_standby(game, player, page) is None):
        raise IllegalCommand("spell.used", "此戰術卡本回合已使用過")
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
        else:   # 未指定:可使用的魔物中優先不受限制者(M-038 在「術を使えない」時仍可使用)
            usable = [s for s in st.players[player].slots if _spell_usable_by(game, player, s, card)]
            slot = next((s for s in usable
                         if not spell_block(game, player, s, attack=attack, card=card, defense=not attack)),
                        usable[0] if usable else None)
        if slot is None:
            raise IllegalCommand("spell.no_mamodo", "對應此戰術的魔物不在自己場上")
    block = spell_block(game, player, slot, attack=attack, card=card, defense=not attack)
    if block:
        raise IllegalCommand(block, "目前不能使用此戰術")
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
    _proceed_declaration(game, batch, data["side"], decl)
    if data["side"] == "attack":
        game.state.action_player = decl["player"]


reg.CHOICE_RESOLVERS["spell_discount"] = _spell_discount_resolver


def _proceed_declaration(game: Game, batch: list[dict], side: str, decl: dict) -> None:
    """減費之後:追加費用(S-067 / S-097)的詢問,之後開始迎戰確認(攻擊)或完成防禦宣告。"""
    if "extra" not in decl and _ask_extra_cost(game, batch, side, decl):
        return
    if side == "attack":
        _open_battle_in(game, batch, decl)
    else:
        _finish_defense_declaration(game, batch, decl)


def _extra_cost_options(game: Game, player: int, card: CardDef, cost: int) -> list[int]:
    rider = reg.SPELL_RIDERS.get(card.number)
    if not rider or not rider.extra_cost:
        return [0]
    step, most = rider.extra_cost[0], rider.extra_cost[1]
    mp = game.state.players[player].mp
    return [v for v in range(0, most + 1, step) if cost + v <= mp]


def _ask_extra_cost(game: Game, batch: list[dict], side: str, decl: dict) -> bool:
    """宣告時詢問追加費用;只列付得起的量,只有 0 時不詢問。"""
    player, card = decl["player"], game.db[decl["spell"]]
    slot = game.state.slot_by_uid(player, decl["slot"])
    cost = spell_cost(game, player, decl["page"], card, slot=slot, discount=decl.get("discount", False))
    values = _extra_cost_options(game, player, card, cost)
    if len(values) <= 1:
        decl["extra"] = 0
        return False
    step, _, power, damage = reg.SPELL_RIDERS[card.number].extra_cost
    options = [{"value": v, "label": "extra_cost", "amount": v, "power": power * v // step,
                "damage": damage * v // step} for v in values]
    game.state.pending = PendingChoice(kind="spell_extra_cost", player=player, source=card.number,
                                       options=options, data={"side": side, "decl": decl})
    game.emit(batch, "choice_required", kind="spell_extra_cost", player=player)
    return True


def _spell_extra_cost_resolver(game: Game, batch: list[dict], value, data) -> None:
    if value not in {o["value"] for o in game.state.pending.options}:
        raise IllegalCommand("choose.invalid", "無效的追加費用")
    decl = data["decl"]
    decl["extra"] = value
    game.state.pending = None
    _proceed_declaration(game, batch, data["side"], decl)
    if data["side"] == "attack":
        game.state.action_player = decl["player"]


reg.CHOICE_RESOLVERS["spell_extra_cost"] = _spell_extra_cost_resolver


def _affordable_extra(game: Game, player: int, cost: int, extra: int, card: CardDef) -> int:
    """實際支付時的追加費用:宣告後 MP 可能已改變,取付得起的最大量。"""
    if not extra:
        return 0
    return max(v for v in _extra_cost_options(game, player, card, cost) if v <= extra)


def _extra_cost_data(side: str, number: str, extra: int) -> dict:
    """追加費用的加成寫進 battle.data:戰術魔力明細與攻擊傷害加值。"""
    rider = reg.SPELL_RIDERS.get(number)
    if not extra or not rider or not rider.extra_cost:
        return {}
    step, _, power, damage = rider.extra_cost
    data = {f"{side}_spell_power": [{"kind": "spell_bonus", "source": number, "amount": power * extra // step}]}
    if side == "attack" and damage:
        data["attack_damage_delta"] = damage * extra // step
    return data


def uses_this_turn(ps, key: str) -> int:
    """本回合已使用的次數:第 1 次記為 key,之後記為 key#2、key#3…(used_abilities 是集合)。"""
    return sum(1 for k in ps.used_abilities if k == key or k.startswith(key + "#"))


def _mark_used(ps, key: str) -> None:
    n = uses_this_turn(ps, key)
    ps.used_abilities.add(key if n == 0 else f"{key}#{n + 1}")


def _validate_mamodo_attack(game: Game, player: int, slot_uid) -> tuple[MamodoSlot, dict]:
    """魔物效果攻擊(M-027):驗證魔物已註冊魔物效果攻擊且可支付費用。"""
    st = game.state
    slot = st.slot_by_uid(player, slot_uid if slot_uid is not None else -1)
    if slot is None:
        raise IllegalCommand("attack.no_slot", "找不到指定的場上魔物")
    spec = reg.MAMODO_ATTACK.get(slot.top)
    if spec is None:
        raise IllegalCommand("attack.no_mamodo_attack", "此魔物不能以魔物效果攻擊")
    block = mamodo_effect_block(game, player, slot)
    if block:
        raise IllegalCommand(f"attack.{block}", "此魔物的效果目前不能使用")
    if uses_this_turn(st.players[player], f"mamodo_attack:{slot.top}") >= spec["per_turn"]:
        raise IllegalCommand("attack.used", "此效果本回合已使用過")   # 「１つの効果は、１ターンに１回だけ」(M-068 為 2 次)
    if st.players[player].mp < spec["mp_cost"]:
        raise IllegalCommand("attack.mp", "MP 不足")
    return slot, spec


def _declare_attack(game: Game, batch: list[dict], player: int, command: dict) -> None:
    st = game.state
    if player != st.turn_player:
        raise IllegalCommand("attack.not_turn_player", "只有回合玩家能攻擊")
    if restricted(game, player, NO_ATTACK):
        raise IllegalCommand("attack.restricted", "本回合不能攻擊")
    if command.get("mode") == "mamodo":
        slot, _spec = _validate_mamodo_attack(game, player, command.get("slot_uid"))
        st.interrupted_attack = None
        st.battle_in = {"attacker": player, "mamodo_attack": True, "slot": slot.uid}
        game.emit(batch, "battle_in_check", attacker=player, spell=None,
                  mamodo=slot.top, slot=slot.uid)
        return
    number, slot = _validate_spell_declaration(
        game, player, command.get("page"), command.get("slot_uid"), attack=True)
    st.interrupted_attack = None
    decl = {"player": player, "page": command["page"], "spell": number, "slot": slot.uid}
    if not _ask_spell_discount(game, batch, "attack", decl):
        _proceed_declaration(game, batch, "attack", decl)


def _open_battle_in(game: Game, batch: list[dict], decl: dict) -> None:
    st = game.state
    st.battle_in = {"attacker": decl["player"], "page": decl["page"], "spell": decl["spell"],
                    "slot": decl["slot"], "discount": decl["discount"], "extra": decl.get("extra", 0)}
    game.emit(batch, "battle_in_check", attacker=decl["player"], spell=decl["spell"], slot=decl["slot"])


def interrupted_attack(game: Game, player: int) -> dict | None:
    """player 被插入行動打斷、仍可重新宣告的攻擊:同一回合,且戰術頁仍是 player 翻開的頁。"""
    rec = game.state.interrupted_attack
    if rec is None or rec["attacker"] != player or rec["turn_no"] != game.state.turn_no:
        return None
    if not rec["mamodo_attack"] and rec["page"] not in game.state.players[player].open_pages():
        return None
    return rec


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
    if ctype in ("play_card", "use_field_ability", "use_book_card", "use_action_effect"):
        st.battle_in = None
        st.interrupted_attack = {"attacker": bi["attacker"], "page": bi.get("page"),
                                 "mamodo_attack": bool(bi.get("mamodo_attack")), "slot": bi["slot"],
                                 "turn_no": st.turn_no}
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


@dataclass
class AttackStart:
    """攻擊來源準備好的戰鬥初始內容(戰術攻擊 / 魔物效果攻擊),交給共用的戰鬥開始流程。"""
    battle: dict                      # BattleState 的初始參數(attack_page / attack_spell / attack_slot)
    data: dict                        # battle.data 的初始內容
    started: dict                     # battle_started 事件的欄位
    is_spell: bool                    # 以戰術攻擊(「術」相關的待命只適用於戰術)
    mamodo_name: str | None           # 使用魔物的家族(限定魔物的待命以此判定)
    discount: bool = False            # 選擇使用 M-008 的可選減費
    slot_uid: int | None = None       # 攻擊的魔物(M-054「この魔物の術で攻撃」)
    family: str | None = None         # 攻擊的魔物的家族,魔物效果攻擊也有(P-042「『ダニー』の術や『魔物の効果』」)


def _prepare_spell_attack(game: Game, batch: list[dict], bi: dict) -> AttackStart:
    """戰術攻擊:再驗證(插入行動可能已改變盤面)、P-015 類任意頁待命、記錄頁、依使用魔物付費。"""
    st = game.state
    attacker, page, number, slot_uid = bi["attacker"], bi["page"], bi["spell"], bi["slot"]
    card = game.db[number]
    discount = bi.get("discount", False)
    _, using_slot = _validate_spell_declaration(game, attacker, page, slot_uid, attack=True,
                                                discount=discount)
    cost = spell_cost(game, attacker, page, card, slot=using_slot, discount=discount)
    if (st.players[attacker].spell_page_uses.get(page, 0) >= spell_use_limit(game, attacker, card)
            and _consume_reuse(game, batch, attacker, page)):
        cost = 0                                         # S-098:已用過的戰術費用 0 再用一次
    if page not in st.players[attacker].open_pages():  # 經 P-015 類待命自任意頁使用
        _consume_any_page(game, batch, attacker, page)
    extra = _affordable_extra(game, attacker, cost, bi.get("extra", 0), card)
    _record_spell_use(game, attacker, page)
    pay_mp(game, batch, attacker, cost + extra, f"spell:{number}")
    slot = st.slot_by_uid(attacker, slot_uid)
    return AttackStart(
        battle={"attack_page": page, "attack_spell": number, "attack_slot": slot_uid},
        data=_extra_cost_data("attack", number, extra), started={"spell": number, "slot": slot_uid}, is_spell=True,
        mamodo_name=family(game, slot) if slot else None, discount=discount,
        slot_uid=slot_uid, family=family(game, slot) if slot else None)


def _prepare_mamodo_attack(game: Game, batch: list[dict], bi: dict) -> AttackStart:
    """魔物效果攻擊(M-027):合計魔力與傷害為卡片指定固定值,費用為固定 MP。"""
    attacker, slot_uid = bi["attacker"], bi["slot"]
    slot, spec = _validate_mamodo_attack(game, attacker, slot_uid)  # 插入行動可能已改變盤面
    _mark_used(game.state.players[attacker], f"mamodo_attack:{slot.top}")
    pay_mp(game, batch, attacker, spec["mp_cost"], f"mamodo_attack:{slot.top}")
    return AttackStart(
        battle={"attack_page": None, "attack_spell": None, "attack_slot": slot_uid},
        data={"attack_fixed_power": spec["power"], "attack_fixed_source": slot.top,
              "attack_fixed_damage": spec["damage"]},
        started={"spell": None, "mamodo": slot.top, "slot": slot_uid}, is_spell=False, mamodo_name=None,
        slot_uid=slot_uid, family=family(game, slot))


def _apply_spell_bonus(game, battle, sb):
    add_spell_power(battle, "attack", sb.source, sb.data.get("power_delta", 0))


def _apply_undefendable(game, battle, sb):
    battle.attack_undefendable = True


def _apply_no_protect_book(game, battle, sb):
    battle.data["no_protect_book"] = True


def _apply_injure_instead(game, battle, sb):
    battle.data["injure_instead"] = True


def _apply_redirect_damage(game, battle, sb):
    battle.data["injure_instead"] = True
    battle.data["injure_target"] = sb.data["slot_uid"]


def _apply_battle_lock(game, battle, sb):
    from .effects.primitives import add_restriction
    for flag in sb.data.get("flags", ()):
        add_restriction(game, [], source=sb.source, owner=sb.owner, target_player=1 - sb.owner,
                        flag=flag, duration=DUR_BATTLE)


# 戰鬥開始時消耗的「下一場戰鬥」待命:(種類, 適用條件(待命, 攻擊), 套用)。依此順序消耗。
# 「術」相關的待命(效果文寫「術」)只適用於戰術攻擊;限定魔物的待命要該家族的戰術。
# 新增作用於下一場戰鬥的待命時在此加一列(見 game-engine/design.md「戰鬥開始與待命表」)。
BATTLE_START_STANDBYS = (
    # M-008 減費減魔力(選擇使用時才套用)/ P-007 加魔力
    ("spell_bonus",
     lambda sb, a: a.is_spell and sb.data.get("mamodo") in (None, a.mamodo_name)
     and (a.discount or not sb.data.get("optional")),
     _apply_spell_bonus),
    # 攻擊不可被防禦:S-019 / S-026 不限定;P-001 限「ガッシュ・ベル」の術で攻撃;M-054 限這隻魔物的戰術
    ("attack_undefendable",
     lambda sb, a: ((sb.data.get("mamodo") is None or (a.is_spell and sb.data.get("mamodo") == a.mamodo_name))
                    and (sb.data.get("slot_uid") is None or (a.is_spell and sb.data["slot_uid"] == a.slot_uid))),
     _apply_undefendable),
    # P-042:以指定家族的戰術或魔物效果攻擊時,本場戰鬥對手的限制
    ("battle_lock", lambda sb, a: sb.data.get("mamodo") == a.family, _apply_battle_lock),
    # E-013:本場戰鬥不能保護魔書
    ("no_protect_book", lambda sb, a: True, _apply_no_protect_book),
    # S-057:下一張攻擊戰術獲勝改為負傷對手魔物
    ("injure_instead", lambda sb, a: a.is_spell, _apply_injure_instead),
    # P-022:以指定家族的戰術攻擊時,傷害改給指定的對手魔物
    ("redirect_damage", lambda sb, a: a.is_spell and sb.data.get("mamodo") == a.mamodo_name,
     _apply_redirect_damage),
)


def _start_battle(game: Game, batch: list[dict], bi: dict) -> None:
    """戰鬥開始:準備攻擊來源(戰術 / 魔物效果攻擊),之後共用建立戰鬥、啟用待命、發出事件與消耗待命。"""
    st = game.state
    attacker = bi["attacker"]
    prepare = _prepare_mamodo_attack if bi.get("mamodo_attack") else _prepare_spell_attack
    a = prepare(game, batch, bi)
    battle = BattleState(attacker=attacker, step=STEP_DEFENSE, **a.battle)
    battle.data.update(a.data)
    st.battle = battle
    _arm_next_battle_standbys(game)
    game.emit(batch, "battle_started", attacker=attacker, **a.started)
    for kind, applies, apply in BATTLE_START_STANDBYS:
        for sb in _consume_standby(game, kind, lambda s, applies=applies: s.owner == attacker and applies(s, a)):
            apply(game, battle, sb)
            game.emit(batch, "standby_resolved", card=sb.source, kind=sb.kind)
    # 攻擊時解決的待命(M-055 / P-043):條件在戰鬥開始時判斷,成立者在宣告時效果之前依序執行
    for sb in game.state.standby:
        if sb.kind == "on_attack" and sb.owner == attacker and reg.ON_ATTACK[sb.source][1](game, sb, a):
            sb.data["armed"] = True
    # 魔物效果攻擊是「魔物の効果」:防方的ジャマー(M-026)可使攻擊無效,詢問結束後才續行宣告時效果
    if bi.get("mamodo_attack") and _offer_battle_jammer(game, batch, "attack", 1 - attacker, a.started["mamodo"]):
        return
    _attack_declare_continue(game, batch)


def _attack_declare_continue(game: Game, batch: list[dict]) -> None:
    # 攻擊時的待命(M-055 / P-043)先執行(可建立決策;效果樹最後以 ContinueAttackDeclaration 回到這裡),
    # 之後宣告時確定:改為傷害對手魔物的攻擊先選對象,再來是宣告時效果(擲硬幣等)
    if _run_next_on_attack(game, batch):
        return
    if _ask_injure_target(game, batch):
        return
    _attack_declare_effects(game, batch)


def _run_next_on_attack(game: Game, batch: list[dict]) -> bool:
    """執行下一個攻擊時的待命(戰鬥開始時記下的);有執行時回傳 True(效果樹結束時會再呼叫
    _attack_declare_continue)。攻擊已被無效時不再執行(M-055 反面)。"""
    from .effects.tree import run_effect
    st = game.state
    battle = st.battle
    sb = next((s for s in st.standby if s.kind == "on_attack" and s.data.get("armed")), None)
    if sb is None or battle.attack_negated:
        return False
    st.standby.remove(sb)
    game.emit(batch, "standby_resolved", card=sb.source, kind=sb.kind)
    run_effect(game, batch, reg.ON_ATTACK[sb.source][0],
               {"player": sb.owner, "source": sb.source, "self_slot": sb.data.get("slot_uid"),
                "target": sb.data.get("target")})
    return True


def _attack_declare_effects(game: Game, batch: list[dict]) -> None:
    battle = game.state.battle
    if _ask_attack_power_from(game, batch):
        return
    rider = reg.SPELL_RIDERS.get(battle.attack_spell) if battle.attack_spell else None
    if rider and rider.on_declare:
        rider.on_declare(game, batch, battle.attacker, "attack")


def _ask_attack_power_from(game: Game, batch: list[dict]) -> bool:
    """S-089 的待命:攻擊宣告時由攻擊方選擇自己場上攻擊魔物以外的 1 隻魔物,存入
    battle.data["attack_power_from"];魔力勝負時加上它當下的魔力。只有 1 隻時自動,沒有時不生效。
    建立決策時回傳 True,選擇後續行宣告時效果。"""
    st = game.state
    battle = st.battle
    if "attack_power_from" in battle.data:
        return False
    sb = next((s for s in st.standby if s.kind == "attack_power_from_mamodo" and s.owner == battle.attacker), None)
    if sb is None:
        return False
    others = [s for s in st.players[battle.attacker].slots if s.uid != battle.attack_slot]
    battle.data["attack_power_from"] = {"source": sb.source, "slot": others[0].uid if len(others) == 1 else None}
    if len(others) <= 1:
        return False
    st.pending = PendingChoice(kind="attack_power_from", player=battle.attacker, source=sb.source,
                               options=[slot_option(battle.attacker, s) for s in others])
    game.emit(batch, "choice_required", kind="attack_power_from", player=battle.attacker)
    return True


def _attack_power_from_resolver(game: Game, batch: list[dict], value, data) -> None:
    st = game.state
    battle = st.battle
    if value not in {o["value"] for o in st.pending.options}:
        raise IllegalCommand("choose.invalid", "須選擇攻擊魔物以外的自己魔物")
    st.pending = None
    battle.data["attack_power_from"]["slot"] = value
    _attack_declare_effects(game, batch)


reg.CHOICE_RESOLVERS["attack_power_from"] = _attack_power_from_resolver


def _ask_injure_target(game: Game, batch: list[dict]) -> bool:
    """S-058 / S-057 待命:攻擊宣告時由攻擊方選擇對手的魔物,存入 battle.data["injure_target"]
    (game-engine「戰鬥流程五步驟」:對象於宣告時選擇)。建立決策時回傳 True,選擇後續行宣告時效果。"""
    st = game.state
    battle = st.battle
    rider = reg.SPELL_RIDERS.get(battle.attack_spell) if battle.attack_spell else None
    if not ((rider and rider.injure_instead) or battle.data.get("injure_instead")):
        return False
    if "injure_target" in battle.data:   # P-022 已指定對象:仍在場就不詢問,已離場則照常打魔書
        if st.slot_by_uid(battle.defender, battle.data["injure_target"]) is None:
            battle.data.pop("injure_target")
            battle.data.pop("injure_instead", None)
        return False
    targets = st.players[battle.defender].slots
    if len(targets) <= 1:
        battle.data["injure_target"] = targets[0].uid if targets else None
        return False
    st.pending = PendingChoice(
        kind="injure_instead_target", player=battle.attacker, source=battle.attack_spell,
        options=[slot_option(battle.defender, s) for s in targets], data={"declare": True})
    game.emit(batch, "choice_required", kind="injure_instead_target", player=battle.attacker)
    return True


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
            if attack_undefendable(game, battle):
                raise IllegalCommand("defense.undefendable", "此攻擊不可被防禦")
            if restricted(game, player, NO_DEFENSE):
                raise IllegalCommand("defense.restricted", "目前不能防禦")
            if command.get("mode") == "mamodo":
                _declare_mamodo_defense(game, batch, player, command.get("slot_uid"))
                return
            number, slot = _validate_spell_declaration(
                game, player, command.get("page"), command.get("slot_uid"), attack=False)
            decl = {"player": player, "page": command["page"], "spell": number, "slot": slot.uid}
            if not _ask_spell_discount(game, batch, "defense", decl):
                _proceed_declaration(game, batch, "defense", decl)
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


def _declare_mamodo_defense(game: Game, batch: list[dict], player: int, slot_uid) -> None:
    """魔物效果防禦(M-039):支付固定 MP,以卡片指定的合計魔力防禦(不加魔物魔力、不吃戰術加成)。"""
    st = game.state
    battle = st.battle
    slot = st.slot_by_uid(player, slot_uid if slot_uid is not None else -1)
    if slot is None:
        raise IllegalCommand("defense.no_slot", "找不到指定的場上魔物")
    spec = reg.MAMODO_DEFENSE.get(slot.top)
    if spec is None:
        raise IllegalCommand("defense.no_mamodo_defense", "此魔物不能以魔物效果防禦")
    block = mamodo_effect_block(game, player, slot)
    if block:
        raise IllegalCommand(f"defense.{block}", "此魔物的效果目前不能使用")
    if f"mamodo_defense:{slot.top}" in st.players[player].used_abilities:
        raise IllegalCommand("defense.used", "此效果本回合已使用過")
    if st.players[player].mp < spec["mp_cost"]:
        raise IllegalCommand("defense.mp", "MP 不足")
    st.players[player].used_abilities.add(f"mamodo_defense:{slot.top}")
    pay_mp(game, batch, player, spec["mp_cost"], f"mamodo_defense:{slot.top}")
    battle.defense_slot = slot.uid
    battle.defense_declared = True
    battle.data["defense_fixed_power"] = spec["power"]
    battle.data["defense_fixed_source"] = slot.top
    game.emit(batch, "defense_declared", player=player, spell=None, mamodo=slot.top, slot=slot.uid)
    # 魔物效果防禦是「魔物の効果」:攻方的ジャマー(M-026)可使防禦無效
    if _offer_battle_jammer(game, batch, "defense", battle.attacker, slot.top):
        return
    _enter_effects_step(game, batch)


def _defended(battle: BattleState) -> bool:
    """防方有宣告防禦(戰術或魔物效果)。"""
    return bool(battle.defense_spell) or "defense_fixed_power" in battle.data


def _finish_defense_declaration(game: Game, batch: list[dict], decl: dict) -> None:
    st = game.state
    battle = st.battle
    player, page, number, discount = decl["player"], decl["page"], decl["spell"], decl["discount"]
    slot = st.slot_by_uid(player, decl["slot"])
    card = game.db[number]
    cost = spell_cost(game, player, page, card, slot=slot, discount=discount)
    if (st.players[player].spell_page_uses.get(page, 0) >= spell_use_limit(game, player, card)
            and _consume_reuse(game, batch, player, page)):
        cost = 0                                         # S-098
    if page not in st.players[player].open_pages():
        _consume_any_page(game, batch, player, page)
    extra = _affordable_extra(game, player, cost, decl.get("extra", 0), card)
    _record_spell_use(game, player, page)
    pay_mp(game, batch, player, cost + extra, f"spell:{number}")
    for k, v in _extra_cost_data("defense", number, extra).items():
        battle.data.setdefault(k, [] if isinstance(v, list) else 0)
        battle.data[k] = battle.data[k] + v
    battle.defense_page = page
    battle.defense_spell = number
    battle.defense_slot = slot.uid
    battle.defense_declared = True
    game.emit(batch, "defense_declared", player=player, spell=number, slot=slot.uid)
    mamodo_name = family(game, slot)
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
        if battle.attack_spell is None:  # 魔物效果攻擊:固定合計魔力
            total = battle.data.get("attack_fixed_power", 0)
            items = [_item("fixed", battle.data.get("attack_fixed_source"), total)]
            total, items = _static_total(game, battle.attacker, battle.attack_slot, total, items)
            total, items = _attack_power_from(game, battle, total, items)
            return _negate(total, items, negated, negated_by)
        player, slot_uid, spell = battle.attacker, battle.attack_slot, battle.attack_spell
    else:
        if not _defended(battle):
            return 0, []
        negated, negated_by = battle.defense_negated, battle.data.get("defense_negated_by")
        if not battle.defense_spell:  # 魔物效果防禦:固定合計魔力
            total = battle.data["defense_fixed_power"]
            total, items = _static_total(game, battle.defender, battle.defense_slot, total,
                                         [_item("fixed", battle.data.get("defense_fixed_source"), total)])
            return _negate(total, items, negated, negated_by)
        player, slot_uid, spell = battle.defender, battle.defense_slot, battle.defense_spell
    card = game.db[spell]
    rider = reg.SPELL_RIDERS.get(spell)
    if rider and rider.fixed_total and side in rider.fixed_total:   # S-087:合計魔力固定,不加其他加成
        total = rider.fixed_total[side]
        return _negate(total, [_item("fixed", spell, total)], negated, negated_by)
    slot = game.state.slot_by_uid(player, slot_uid)
    mamodo, items = power_breakdown(game, player, slot) if slot else (0, [])
    # 戰術的魔力(特殊為 0),加上戰術自身的加值與待命 / 效果的加成(S-016 / S-017 / S-040 / M-008 / P-007)
    spell_items = [_item("spell", spell, 0 if card.power_special else (card.power_bonus or 0))]
    spell_items += [dict(i) for i in battle.data.get(f"{side}_spell_power", [])]
    st = game.state
    spell_items += [_item("attr_power", m.source, m.amount) for m in st.modifiers   # S-062:雙方的屬性加成
                    if m.kind == "attr_power" and m.active(st.turn_no) and m.data.get("attr") == card.attr_name]
    spell_items += [_item("static_spell", number, amount)                             # PR-004:常駐的戰術加成
                    for number, s in _field_cards(game, player, reg.STATIC_SPELL_POWER)
                    if (amount := reg.STATIC_SPELL_POWER[number](game, player, card))]
    spell_items += [_item("spell_named", m.source, m.data.get("power", 0))           # PR-010:依戰術名稱的加成
                    for m in _spell_named_modifiers(game, player, card) if m.data.get("power")]
    spell_pw = sum(i["amount"] for i in spell_items)
    if spell_pw < 0:  # 戰術的魔力加減不低於 0(M-008「0より小さくはならない」)
        spell_items.append(_item("spell_floor", None, -spell_pw))
    total, items = mamodo + max(0, spell_pw), items + spell_items
    total, items = _static_total(game, player, slot_uid, total, items)
    if side == "attack":
        total, items = _attack_power_from(game, battle, total, items)
    return _negate(total, items, negated, negated_by)


def _field_cards(game: Game, player: int, table: dict) -> list[tuple[str, MamodoSlot]]:
    """player 場上(魔物頂層與搭檔)登記在 table 的常駐效果卡:[(卡號, 所在 slot)];同卡號多張各列一次,
    被「使えない」擋下的不列。"""
    out = []
    for s in game.state.players[player].slots:
        for number in (s.top, s.partner):
            if number in table and not card_effect_blocked(game, player, s, number):
                out.append((number, s))
    return out


def _static_total(game: Game, player: int, slot_uid, total: int, items: list[dict]) -> tuple[int, list[dict]]:
    """Ex-036:場上效果對合計魔力的加成(戰術、魔物效果攻擊與防禦都適用)。"""
    slot = game.state.slot_by_uid(player, slot_uid) if slot_uid is not None else None
    if slot is None:
        return total, items
    for number, _s in _field_cards(game, player, reg.STATIC_TOTAL_POWER):
        amount = reg.STATIC_TOTAL_POWER[number](game, player, slot)
        if amount:
            total, items = total + amount, items + [_item("static_total", number, amount)]
    return total, items


def _spell_named_modifiers(game: Game, player: int, card: CardDef) -> list[Modifier]:
    """PR-010:本回合作用於某魔物名稱完全相符之戰術的持續效果。"""
    st = game.state
    return [m for m in st.modifiers
            if m.kind == "spell_named" and m.active(st.turn_no) and m.target_player == player
            and card.related_mamodo == m.data.get("mamodo") and card.name_ja == m.data.get("name")]


def _attack_power_from(game: Game, battle: BattleState, total: int, items: list[dict]) -> tuple[int, list[dict]]:
    """S-089:攻擊的合計魔力加上宣告時選定的自己魔物當下的魔力(已離場則沒有)。"""
    info = battle.data.get("attack_power_from")
    slot = game.state.slot_by_uid(battle.attacker, info["slot"]) if info and info.get("slot") is not None else None
    if slot is None:
        return total, items
    amount = slot_power(game, battle.attacker, slot)
    return total + amount, items + [_item("mamodo_bonus", info["source"], amount)]


def _negate(total: int, items: list[dict], negated: bool, source: str | None) -> tuple[int, list[dict]]:
    if not negated:
        return total, items
    return 0, items + [_item("negated", source, -total)]


def _attack_damage_amount(game: Game, battle: BattleState) -> int:
    if battle.attack_spell is None:  # 魔物效果攻擊:固定傷害
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
    total += own_damage_bonus(game, battle.attacker)        # M-033:自己使用的魔物效果與戰術
    total += battle.data.get("defense_damage_delta", 0)  # S-027 減傷
    rider = reg.SPELL_RIDERS.get(battle.attack_spell) if battle.attack_spell else None
    if rider and rider.damage_bonus is not None:  # 依合計魔力調整傷害(S-042)
        total += rider.damage_bonus(game, battle)
    if rider and rider.damage_cap is not None:  # 傷害上限(S-032/S-034)
        total = min(total, rider.damage_cap)
    return max(0, total)


def own_damage_bonus(game: Game, player: int) -> int:
    """player 本回合使用的「魔物の効果」與戰術的傷害加值(M-033)。"""
    st = game.state
    return sum(m.amount for m in st.modifiers
               if m.kind == "own_damage_bonus" and m.target_player == player and m.active(st.turn_no))


def _resolve_showdown(game: Game, batch: list[dict]) -> None:
    st = game.state
    battle = st.battle
    # S-021「このバトルの『効果の使用』の最後に、相手の攻撃を無効にする」:雙方 pass 之後、魔力勝負前;
    # 防禦已被無效時一起失效
    late = battle.data.pop("negate_at_effects_end", None)
    if late and not battle.defense_negated and not battle.attack_negated:
        battle.attack_negated = True
        battle.data["attack_negated_by"] = late["source"]
        game.emit(batch, "attack_negated", source=late["source"], player=late["player"])
    # S-095「魔力勝負の勝敗にかかわらず…このターン中、自分の『キャンチョメ』はダメージを受けない」:
    # 宣告時擲幣正面時,魔力勝負時(防禦沒被無効)起生效
    no_damage = battle.data.get("defender_no_damage_family")
    if no_damage and battle.defense_spell and not battle.defense_negated:
        from .effects.primitives import add_modifier
        for s in st.players[battle.defender].slots:
            if family(game, s) == no_damage:
                add_modifier(game, batch, kind="no_damage", source=battle.defense_spell, owner=battle.defender,
                             duration=DUR_TURN, target_player=battle.defender, target_slot=s.uid)
    att, att_items = side_breakdown(game, battle, "attack")
    deff, def_items = side_breakdown(game, battle, "defense")
    battle.data["attack_total"] = att  # 供傷害免疫等查詢型 hook 使用(M-031)
    attacker_wins = (not battle.attack_negated) and att > deff
    a_slot = st.slot_by_uid(battle.attacker, battle.attack_slot)
    d_slot = st.slot_by_uid(battle.defender, battle.defense_slot) if _defended(battle) else None
    game.emit(batch, "showdown", attacker=battle.attacker, attacker_total=att, defender_total=deff,
              winner="attacker" if attacker_wins else "defender",
              attack_negated=battle.attack_negated,
              attacker_breakdown=att_items, defender_breakdown=def_items,
              # 對峙的卡(宣告時已公開):魔物取最上面的卡;不防禦時防禦方為空
              attack_mamodo=a_slot.top if a_slot else None, attack_spell=battle.attack_spell,
              defense_mamodo=d_slot.top if d_slot else None,
              defense_spell=battle.defense_spell or None)
    rider = reg.SPELL_RIDERS.get(battle.attack_spell) if battle.attack_spell else None
    # S-100「魔力勝負の勝敗にかかわらず」:防方獲勝也照攻擊方獲勝解決(攻擊被無效時除外);勝負事件照實際結果
    if attacker_wins or (rider and rider.damage_regardless and not battle.attack_negated):
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
        if rider and rider.no_book_damage:
            finish_attack_without_damage(game, batch)
        else:
            attack_book_damage(game, batch)
        return
    # 防方獲勝(或攻擊無效):攻方效果無效;僅【反擊】解決
    d_rider = reg.SPELL_RIDERS.get(battle.defense_spell) if battle.defense_spell else None
    if d_rider and d_rider.counter and not battle.defense_negated:
        if d_rider.on_counter:                   # S-109:獲勝時才擲幣,由效果決定是否造成傷害
            d_rider.on_counter(game, batch, battle.defender)
            return
        counter_book_damage(game, batch)
        return
    _end_battle(game, batch)


def end_battle(game: Game, batch: list[dict]) -> None:
    _end_battle(game, batch)


def counter_book_damage(game: Game, batch: list[dict]) -> None:
    """【反擊】的結算:防方以魔力勝負獲勝時,以防禦戰術的傷害對攻方魔書造成傷害(0 時直接結束戰鬥)。"""
    battle = game.state.battle
    d_rider = reg.SPELL_RIDERS.get(battle.defense_spell)
    amount = game.db[battle.defense_spell].damage or 0
    if d_rider and d_rider.counter_damage_from_attack:   # S-061:等於對手攻擊的傷害
        amount = _attack_damage_amount(game, battle)
    if amount > 0:
        amount += own_damage_bonus(game, battle.defender)
    if amount > 0:
        _start_damage(game, batch,
                      [{"kind": "book", "player": battle.attacker, "amount": amount}],
                      {"cause": "battle_counter", "source": battle.defense_spell,
                       "source_player": battle.defender})
        return
    _end_battle(game, batch)


def attack_book_damage(game: Game, batch: list[dict]) -> None:
    """攻擊方獲勝的預設結算:以攻擊的傷害對防方魔書造成傷害(0 時直接結束);S-069 / S-070 的效果也用。"""
    battle = game.state.battle
    amount = _attack_damage_amount(game, battle)
    if amount > 0:
        _start_damage(game, batch,
                      [{"kind": "book", "player": battle.defender, "amount": amount}],
                      {"cause": "battle_attack", "source": battle.attack_spell,
                       "source_player": battle.attacker, "amount": amount})
        return
    finish_attack_without_damage(game, batch)


def finish_attack_without_damage(game: Game, batch: list[dict]) -> None:
    """攻擊方獲勝但沒有造成傷害:直接結束戰鬥。"""
    battle = game.state.battle
    _finish_battle_damage(game, batch, {"cause": "battle_attack", "dealt": False,
                                        "source": battle.attack_spell,
                                        "source_player": battle.attacker})


def _injure_instead_of_damage(game: Game, batch: list[dict]) -> None:
    """獲勝時對宣告時選定的對手魔物(battle.data["injure_target"])造成傷害代替魔書傷害;
    沒有對象或對象已離場時沒有這份傷害。"""
    st = game.state
    battle = st.battle
    ctx = {"cause": "battle_attack", "source": battle.attack_spell,
           "source_player": battle.attacker}
    target = st.slot_by_uid(battle.defender, battle.data.get("injure_target", -1)) \
        if battle.data.get("injure_target") is not None else None
    if target is None:
        _finish_battle_damage(game, batch, {**ctx, "dealt": False})
        return
    _start_damage(game, batch,
                  [{"kind": "slot", "player": battle.defender,
                    "slot_uid": target.uid, "amount": 1}], ctx)


def _damage_order_option(index: int, item: dict) -> dict:
    """受傷順序的選項:魔物項標示所在的魔物槽;魔書項維持按鈕。"""
    opt = {"index": index, "item": item}
    if item["kind"] == "slot":
        opt.update(zone="slot", player=item["player"], slot=item["slot_uid"])
    return opt


def _injure_instead_resolver(game: Game, batch: list[dict], value, data) -> None:
    """攻擊宣告時選擇的對手魔物:記下後續行宣告時效果。"""
    st = game.state
    battle = st.battle
    slot = st.slot_by_uid(battle.defender, value) if battle else None
    if slot is None:
        raise IllegalCommand("choose.invalid", "無效的負傷對象")
    st.pending = None
    battle.data["injure_target"] = slot.uid
    _attack_declare_effects(game, batch)


reg.CHOICE_RESOLVERS["injure_instead_target"] = _injure_instead_resolver


# ---------------------------------------------------------------- ジャマー(M-026《裏切り者》)
# 對手用完「魔物的效果」(啟動型)後,持有可用ジャマー的一方立即被詢問是否使其無效。
# 無效 = 把效果造成的變化還原到效果解決前(對手支付的費用與「本回合已使用」照算);
# 輪到誰行動、pass 次數、戰鬥中的效果輪替等流程狀態維持目前的值。

def _jammer_holder(game: Game, player: int, on: str = "mamodo_effect"):
    """player 場上可用、回應 on 動作(mamodo_effect / event)的ジャマー:(卡號, slot, spec);沒有則 None。"""
    ps = game.state.players[player]
    for slot in ps.slots:
        spec = reg.JAMMER.get(slot.top)
        if spec is None or spec["on"] != on:
            continue
        if (f"mamodo:{slot.top}" in ps.used_abilities or ps.mp < spec["mp_cost"]
                or mamodo_effect_block(game, player, slot)):
            continue
        return slot.top, slot, spec
    return None


def _queue_jammer(game: Game, batch: list[dict], player: int, negated: str, snapshot,
                  on: str = "mamodo_effect") -> None:
    st = game.state
    if st.phase == GAME_OVER or (snapshot.battle is None) != (st.battle is None):
        return  # 遊戲結束,或效果使戰鬥開始 / 結束:不提供無效化(避免復活已結束的戰鬥)
    game.jammer = {"player": player, "negated": negated, "snapshot": snapshot, "on": on}
    _offer_jammer_if_ready(game, batch)


def _offer_jammer_if_ready(game: Game, batch: list[dict]) -> None:
    """待決事項都解決(對手效果的選擇完成)後,才詢問ジャマー。"""
    st = game.state
    if game.jammer is None or st.pending is not None:
        return
    on = game.jammer.get("on", "mamodo_effect")
    if st.phase == GAME_OVER or _jammer_holder(game, game.jammer["player"], on) is None:
        offer, game.jammer = game.jammer, None
        if "battle_side" in offer and st.phase != GAME_OVER:
            _battle_jammer_done(game, batch, offer["battle_side"])
        return
    player, negated = game.jammer["player"], game.jammer["negated"]
    number, _slot, spec = _jammer_holder(game, player, on)
    options = [{"value": None, "label": "skip"},
               {"value": True, "label": "jammer_use", "card": negated,
                "cost": spec["mp_cost"], "discard": spec["discard_self"]}]
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


def _discard_jammer_silently(state: GameState, player: int, slot_uid: int) -> None:
    """在快照上支付「このカードを捨て札にする」的費用(不發事件;M-032 的連鎖快照用)。"""
    ps = state.players[player]
    slot = next((s for s in ps.slots if s.uid == slot_uid), None)
    if slot is None:
        return
    ps.slots.remove(slot)
    for number in slot.stack + ([slot.partner] if slot.partner else []):
        to_discard(ps, number)


def _offer_battle_jammer(game: Game, batch: list[dict], side: str, player: int, negated: str,
                         negate: bool = True) -> bool:
    """魔物效果攻擊 / 魔物效果防禦(魔物の効果)後,player 有可用的ジャマー時詢問是否使該側無效(官方規則書第 42 頁:
    「無効にする」包括取消戰鬥中使用的攻擊與防禦,所以不還原盤面,以攻擊 / 防禦無效處理)。
    negate=False 為連鎖:使上一次的無效化失效。建立詢問時回傳 True,詢問結束後由 _battle_jammer_done 續行。"""
    if _jammer_holder(game, player) is None:
        return False
    game.jammer = {"player": player, "negated": negated, "battle_side": side, "negate": negate}
    _offer_jammer_if_ready(game, batch)
    return True


def _battle_jammer_done(game: Game, batch: list[dict], side: str) -> None:
    """戰鬥中攻防的ジャマー詢問結束:續行魔物效果攻擊的宣告時效果,或進入魔物效果防禦後的效果步驟。"""
    game.jammer = None
    if game.state.battle is None or game.state.phase == GAME_OVER:
        return
    if side == "attack":
        _attack_declare_continue(game, batch)
    else:
        _enter_effects_step(game, batch)


def _battle_jammer_use(game: Game, batch: list[dict], offer: dict) -> None:
    st = game.state
    player, side = offer["player"], offer["battle_side"]
    number, slot, spec = _jammer_holder(game, player)
    st.players[player].used_abilities.add(f"mamodo:{number}")
    pay_mp(game, batch, player, spec["mp_cost"], f"ability:{number}")
    if spec["discard_self"]:
        _discard_slot(game, batch, player, slot, reason="cost")
    game.emit(batch, "ability_used", player=player, card=number, slot=slot.uid, zone="mamodo")
    battle = st.battle
    setattr(battle, f"{side}_negated", offer["negate"])
    if offer["negate"]:
        battle.data[f"{side}_negated_by"] = number
    else:
        battle.data.pop(f"{side}_negated_by", None)
    game.emit(batch, "effect_negated", player=player, source=number, negated=offer["negated"])
    # 連鎖:無效化本身也是魔物的效果,被無效的一方可再以ジャマー使它失效
    if not _offer_battle_jammer(game, batch, side, 1 - player, number, negate=not offer["negate"]):
        _battle_jammer_done(game, batch, side)


def _jammer_resolver(game: Game, batch: list[dict], value, data) -> None:
    if value is not True and value is not None:
        raise IllegalCommand("choose.invalid", "須選擇是否使用")
    offer = game.jammer
    if offer is not None and "battle_side" in offer:
        if value is None:
            _battle_jammer_done(game, batch, offer["battle_side"])
        elif _jammer_holder(game, offer["player"]) is None:
            raise IllegalCommand("choose.invalid", "目前無法使用此效果")
        else:
            _battle_jammer_use(game, batch, offer)
        return
    if value is None or offer is None:
        game.jammer = None
        return
    player = offer["player"]
    holder = _jammer_holder(game, player, offer.get("on", "mamodo_effect"))
    if holder is None:
        raise IllegalCommand("choose.invalid", "目前無法使用此效果")
    number, slot, spec = holder
    st = game.state
    slot_uid = slot.uid
    # 連鎖:無效化本身是「魔物の効果」,對手可再以回應魔物效果的ジャマー(M-026)使它失效
    # → 以「已支付本次費用、尚未還原」的狀態當快照
    chain = None
    if _jammer_holder(game, 1 - player) is not None:
        chain = copy.deepcopy(st)
        chain.players[player].mp -= spec["mp_cost"]
        chain.players[player].used_abilities.add(f"mamodo:{number}")
        if spec["discard_self"]:
            _discard_jammer_silently(chain, player, slot_uid)
    _restore_effect_state(st, offer["snapshot"])
    game.jammer = None
    st.players[player].used_abilities.add(f"mamodo:{number}")
    pay_mp(game, batch, player, spec["mp_cost"], f"ability:{number}")
    if spec["discard_self"]:   # M-032:費用為棄掉自己(在還原之後支付,不會被還原回場上)
        restored = st.slot_by_uid(player, slot_uid)
        if restored is not None:
            _discard_slot(game, batch, player, restored, reason="cost")
    game.emit(batch, "ability_used", player=player, card=number, slot=slot_uid, zone="mamodo")
    game.emit(batch, "effect_negated", player=player, source=number, negated=offer["negated"])
    if chain is not None:
        game.jammer = {"player": 1 - player, "negated": number, "snapshot": chain, "on": "mamodo_effect"}


reg.CHOICE_RESOLVERS["jammer_negate"] = _jammer_resolver


def _end_battle(game: Game, batch: list[dict]) -> None:
    st = game.state
    # 「このバトルの終了後」「このバトル後」的效果(S-068 / S-062):戰鬥結束時生效,攻擊被無效時不生效
    after = [sb for sb in st.standby if sb.kind == "after_battle"]
    st.standby = [sb for sb in st.standby if sb.kind != "after_battle"]
    if st.battle is not None and not st.battle.attack_negated:
        for sb in after:
            _apply_after_battle(game, batch, sb)
    st.modifiers = [m for m in st.modifiers if m.duration != DUR_BATTLE]
    st.standby = [s for s in st.standby if s.data.get("expires") != "battle"]   # 「このバトル中」的待命(P-006)
    st.battle = None
    game.emit(batch, "battle_ended")
    if st.phase == GAME_OVER:
        return
    st.action_player = st.turn_player
    st.consecutive_passes = 0


# ---------------------------------------------------------------- 傷害系統

def _apply_after_battle(game: Game, batch: list[dict], sb: Standby) -> None:
    from .effects.primitives import add_modifier, add_restriction
    st = game.state
    data = sb.data
    game.emit(batch, "standby_resolved", card=sb.source, kind=sb.kind)
    if data.get("action") == "restrict":
        add_restriction(game, batch, source=sb.source, owner=sb.owner, target_player=1 - sb.owner,
                        flag=data["flag"], duration=data["duration"])
    elif data.get("action") == "attr_power":
        # 「重複しない」:同屬性的加成已在生效時不再加
        if any(m.kind == "attr_power" and m.data.get("attr") == data["attr"] and m.active(st.turn_no)
               for m in st.modifiers):
            return
        add_modifier(game, batch, kind="attr_power", source=sb.source, owner=sb.owner,
                     duration=data["duration"], amount=data["amount"], data={"attr": data["attr"]})


def _eligible_protectors(game: Game, item: dict, ctx: dict | None = None) -> list[tuple[int, MamodoSlot]]:
    """可保護此項傷害的魔物 (持有者, 魔物)。魔書傷害:任何自己魔物;魔物傷害:其他魔物。
    對手攻擊造成的魔書傷害,另可用 P-027 選定的對手魔物保護。"""
    st = game.state
    player = item["player"]
    battle = st.battle
    # 「かばうことができない」:不能保護魔書(E-013 / S-035 類)、只能以選定魔物保護(P-026 / E-043);
    # M-042 / E-031 的魔物照樣可保護;M-051(reg.CANNOT_PROTECT)一律不能保護
    no_book = (item["kind"] == "book" and battle is not None and battle.data.get("no_protect_book")
               and player == battle.defender)
    only = [m.target_slot for m in _restrictions(game, player) if m.flag in (PROTECT_ONLY, ONLY_MAMODO)]
    banned = {m.target_slot for m in _restrictions(game, player) if m.flag == NO_PROTECT_SLOT}   # P-043

    def can_protect(s: MamodoSlot) -> bool:
        if s.top in reg.CANNOT_PROTECT:
            return False
        if _protect_anyway(game, player, s):
            return True
        return not no_book and s.uid not in banned and all(s.uid == uid for uid in only)

    if item["kind"] == "book":
        out = [(player, s) for s in st.players[player].slots if can_protect(s)]
        if (ctx is not None and ctx.get("cause") == "battle_attack"
                and ctx.get("source_player") == 1 - player):
            for m in st.modifiers:
                if m.kind == "protect_with_opponent" and m.owner == player and m.active(st.turn_no):
                    s = st.slot_by_uid(1 - player, m.target_slot)
                    if (s is not None and s.top not in reg.CANNOT_PROTECT
                            and all(s is not t for _, t in out)):
                        out.append((1 - player, s))
        return out
    return [(player, s) for s in st.players[player].slots if s.uid != item.get("slot_uid") and can_protect(s)]


def _forced_protector(game: Game, receiver: int, protectors: list[tuple[int, MamodoSlot]]):
    """Ex-047 指定、且能保護這份傷害的受方魔物:(modifier, 魔物);沒有時 None。"""
    st = game.state
    for m in st.modifiers:
        if m.kind == "forced_protector" and m.target_player == receiver and m.active(st.turn_no):
            slot = next((s for owner, s in protectors if owner == receiver and s.uid == m.target_slot), None)
            if slot is not None:
                return m, slot
    return None


def _damage_info(game: Game, item: dict) -> dict:
    """保護決策的公開脈絡:目前這份傷害(對象、受傷害的玩家、傷害值、魔物是否已負傷、魔書是否會耗盡)。"""
    st = game.state
    player = item["player"]
    if item["kind"] == "book":
        lethal = st.players[player].pos + 2 * item["amount"] > BOOK_SIZE
        return {"kind": "book", "player": player, "amount": item["amount"], "slot": None,
                "injured": False, "lethal": lethal}
    slot = st.slot_by_uid(player, item.get("slot_uid"))
    return {"kind": "slot", "player": player, "amount": item.get("amount", 1), "slot": item.get("slot_uid"),
            "injured": bool(slot and slot.injured), "lethal": False}


def _protect_choice(game: Game, batch: list[dict], item: dict, ctx: dict) -> bool:
    """有可保護的魔物時建立保護決策並回傳 True。"""
    protectors = _eligible_protectors(game, item, ctx)
    if not protectors or item.get("no_protect"):
        return False
    receiver = item["player"]
    forced = _forced_protector(game, receiver, protectors)
    if forced is not None:   # Ex-047:「可能な限り」以指定的魔物保護,不詢問
        m, slot = forced
        game.emit(batch, "protect_forced", player=receiver, slot=slot.uid, card=slot.top, source=m.source)
        game.state.pending = PendingChoice(kind="protect", player=receiver, source=ctx.get("source"),
                                           options=[slot_option(receiver, slot)], data={"ctx": ctx})
        _handle_choose(game, batch, {"value": slot.uid})   # 照一般的保護選擇處理,之後續行傷害
        return True
    game.state.pending = PendingChoice(
        kind="protect", player=receiver, source=ctx.get("source"),
        options=[{"value": None, "label": "no_protect"}]
        + [slot_option(owner, s) for owner, s in protectors],
        data={"ctx": ctx}, info={"damage": _damage_info(game, item)})
    game.emit(batch, "choice_required", kind="protect", player=receiver, item=dict(item))
    return True


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
        if _protect_choice(game, batch, item, ctx):
            return
        ctx["items"].pop(0)
        _apply_damage_item(game, batch, item, ctx)
    _finish_damage(game, batch, ctx)


def _apply_damage_item(game: Game, batch: list[dict], item: dict, ctx: dict) -> None:
    st = game.state
    player = item["player"]
    full_immune = _full_immune(game, player)
    if full_immune:  # S-037/038/041:自己魔書與所有魔物不受傷害/負傷
        game.emit(batch, "damage_prevented", player=player,
                  slot=item.get("slot_uid"), reason="immune", source=full_immune)
        return
    named_immune = _named_immune(game, item)
    if named_immune:  # PR-009:自己的魔書與「ガッシュ・ベル」不受傷害
        game.emit(batch, "damage_prevented", player=player,
                  slot=item.get("slot_uid"), reason="immune", source=named_immune)
        return
    if item["kind"] == "book":
        ps = st.players[player]
        ps.pos += 2 * item["amount"]
        ctx["dealt"] = True
        _note_damage_dealt(game, ctx, player)
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
    if (immunity and immunity(game, player, slot, ctx)
            and not note_effect_blocked(game, batch, player, slot, slot.top, "damage")):
        game.emit(batch, "damage_prevented", player=player, slot=slot.uid, reason="immunity", source=slot.top)
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
    no_damage = next((m for m in st.modifiers if m.kind == "no_damage" and m.target_player == player
                      and m.target_slot == slot.uid and m.active(st.turn_no)), None)
    if no_damage:
        game.emit(batch, "damage_prevented", player=player, slot=slot.uid, source=no_damage.source)
        return
    ctx["dealt"] = True
    _note_damage_dealt(game, ctx, player)
    battle = st.battle
    # S-031 バオウ:因此戰術負傷的魔物直接入墓
    injure_to_discard = (battle is not None and battle.data.get("injure_to_discard")
                         and ctx.get("cause") in ("battle_attack",))
    if slot.injured or injure_to_discard:
        _discard_slot(game, batch, player, slot, reason="damage")
    else:
        slot.injured = True
        game.emit(batch, "mamodo_injured", player=player, slot=slot.uid, card=slot.top)


def _note_damage_dealt(game: Game, ctx: dict, receiver: int) -> None:
    """E-041「自分が相手か相手の魔物にダメージをあたえていれば」:傷害的來源玩家對對手(魔書或魔物,
    含保護者)實際造成傷害時記錄;被免疫或無效擋下的不會走到這裡。"""
    source = ctx.get("source_player")
    if source in (0, 1) and source != receiver:
        game.state.players[source].dealt_damage_this_turn = True


def _discard_slot(game: Game, batch: list[dict], player: int, slot: MamodoSlot, reason: str) -> None:
    st = game.state
    ps = st.players[player]
    if slot not in ps.slots:
        return
    # 疊放頂層單獨入墓、下層保留(M-027 裝甲)
    if len(slot.stack) > 1 and slot.top in reg.DETACH_KEEP_UNDER:
        _detach_top(game, batch, player, slot, reason)
        return
    ps.slots.remove(slot)
    for number in reversed(slot.stack):
        to_discard(ps, number)
    if slot.partner:
        to_discard(ps, slot.partner)
        game.emit(batch, "card_discarded", player=player, card=slot.partner, zone="partner", reason="attached",
                  slot=slot.uid)
    game.emit(batch, "mamodo_discarded", player=player, slot=slot.uid,
              cards=list(slot.stack), reason=reason)
    for number in slot.stack:
        if number in reg.ON_DISCARD and not note_effect_blocked(game, batch, player, slot, number, "discard"):
            reg.ON_DISCARD[number](game, batch, player, slot)


def _detach_top(game: Game, batch: list[dict], player: int, slot: MamodoSlot, reason: str) -> None:
    """只把疊放的最上層棄掉,下層以原狀態(搭檔、負傷)留在場上;發出分離事件供 M-028 觸發器使用。
    M-027 的任何離場、M-046 的 1 行動、M-047 的定時離場都走這裡。"""
    ps = game.state.players[player]
    top = slot.stack.pop()
    to_discard(ps, top)
    game.emit(batch, "card_discarded", player=player, card=top, zone="mamodo", reason=reason,
              slot=slot.uid)
    game.emit(batch, "stack_detached", player=player, slot=slot.uid,
              detached=top, remaining=slot.top)
    if top in reg.ON_DISCARD and not note_effect_blocked(game, batch, player, slot, top, "discard"):
        reg.ON_DISCARD[top](game, batch, player, slot)


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
    if ctx["cause"] == "battle_attack" and ctx.get("protected"):
        rider = reg.SPELL_RIDERS.get(ctx["source"]) if ctx.get("source") else None
        if rider and rider.on_protected:
            rider.on_protected(game, batch, ctx["source_player"])
            if game.state.phase == GAME_OVER:
                return
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

def _guard_immune(game: Game, player: int, slot: MamodoSlot, ctx: dict) -> str | None:
    """S-079:本場戰鬥中,player 以指定家族的魔物保護對手攻擊的傷害時,該魔物不受傷害;生效時回傳來源卡號。"""
    st = game.state
    if ctx.get("cause") != "battle_attack" or ctx.get("source_player") != 1 - player:
        return None
    fam = family(game, slot)
    return next((m.source for m in st.modifiers if m.kind == "guard_immune" and m.target_player == player
                 and m.active(st.turn_no) and m.data.get("mamodo") == fam), None)


def _maybe_discard_protector(game: Game, batch: list[dict], player: int,
                             slot: MamodoSlot, ctx: dict) -> None:
    """P-012 雪莉:對自己布拉葛攻擊傷害進行保護的魔物,承受後直接入墓。"""
    st = game.state
    battle = st.battle
    if battle is None or ctx.get("cause") != "battle_attack":
        return
    atk_slot = st.slot_by_uid(battle.attacker, battle.attack_slot)
    atk_name = family(game, atk_slot) if atk_slot else None
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
        owner = next((o["player"] for o in pending.options
                      if o.get("value") is not None and o["value"] == value), None)
        slot = st.slot_by_uid(owner, value) if owner is not None else None
        if slot is None or slot.uid == item.get("slot_uid"):
            raise IllegalCommand("choose.invalid", "無效的保護對象")
        st.pending = None
        ctx["items"].pop(0)
        # 保護的魔物(P-027 時為對手的魔物)承受傷害;player 為保護的魔物的持有者
        game.emit(batch, "protected", player=owner, slot=slot.uid, card=slot.top,
                  target=item["kind"], target_slot=item.get("slot_uid"),   # 原本的傷害對象(魔書或魔物)
                  target_player=item["player"])
        ctx["protected"] = True   # S-112「この術のダメージを『かばわれた』とき」
        guard = _guard_immune(game, owner, slot, ctx)
        if guard:     # S-079:以ウォンレイ保護對手攻擊的傷害時不受傷害
            game.emit(batch, "damage_prevented", player=owner, slot=slot.uid, reason="guard", source=guard)
        else:
            _apply_damage_item(game, batch,
                               {"kind": "slot", "player": owner,
                                "slot_uid": slot.uid, "amount": 1}, ctx)
            _maybe_discard_protector(game, batch, owner, slot, ctx)
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
        if _protect_choice(game, batch, first, ctx):
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
    _resolve_end_phase_effects(game, batch)


# ---------------------------------------------------------------- 結束階段的效果(規則頁「エンドフェイズ」1、効果の解決)
# 結束階段要解決的效果:M-047 的定時離場、E-038 的 MP 增加、E-041 的翻對手魔書、E-042 的棄魔物。
# 2 個以上時由回合玩家選擇下一個要解決的(「ターンプレイヤーが解決の順番を決めることができます」),
# 都解決後才進行魔物消失處理與強制翻頁。

def _end_phase_effects(game: Game) -> list:
    """本回合結束階段待解決的效果:[(種類, 來源卡, Modifier 或 Standby)],順序固定。"""
    st = game.state
    out = [("scheduled_detach", m.source, m) for m in st.modifiers
           if m.kind == "scheduled_detach" and m.data.get("turn") == st.turn_no]
    # 「このターンのエンドフェイズに」:本回合排定的(M-061 在對手的回合也能使用)
    out += [(sb.kind, sb.source, sb) for sb in st.standby
            if sb.kind in ("end_phase_mp", "end_phase_turn_opponent", "end_phase_discard",
                           "end_phase_discard_partners")
            and sb.created_turn == st.turn_no]
    # PR-011:回合玩家場上的結束階段常駐效果,條件成立且本次結束階段尚未解決者
    ps = st.players[st.turn_player]
    for number, slot in _field_cards(game, st.turn_player, reg.END_PHASE):
        when = reg.END_PHASE_WHEN.get(number)
        if (f"end_phase:{number}:{slot.uid}" not in ps.used_abilities
                and (when is None or when.test(game, {"player": st.turn_player}))):
            out.append(("end_phase_field", number, slot))
    return out


def _resolve_end_phase_effects(game: Game, batch: list[dict]) -> None:
    st = game.state
    while True:
        if st.phase == GAME_OVER:
            return
        effects = _end_phase_effects(game)
        if not effects:
            break
        if len(effects) == 1:
            _resolve_end_phase_effect(game, batch, effects[0])
            continue
        options = [{"value": i, "label": "end_phase_effect", "card": src, "kind": kind}
                   for i, (kind, src, _obj) in enumerate(effects)]
        st.pending = PendingChoice(kind="end_phase_order", player=st.turn_player, options=options)
        game.emit(batch, "choice_required", kind="end_phase_order", player=st.turn_player, options=options)
        return
    _continue_end_phase(game, batch, stage=0)


def _end_phase_order_resolver(game: Game, batch: list[dict], value, data) -> None:
    effects = _end_phase_effects(game)
    if not isinstance(value, int) or not 0 <= value < len(effects):
        raise IllegalCommand("choose.invalid", "須選擇要先解決的效果")
    game.state.pending = None
    _resolve_end_phase_effect(game, batch, effects[value])
    _resolve_end_phase_effects(game, batch)


reg.CHOICE_RESOLVERS["end_phase_order"] = _end_phase_order_resolver


def _resolve_end_phase_effect(game: Game, batch: list[dict], effect) -> None:
    from .effects.primitives import turn_pages
    st = game.state
    kind, source, obj = effect
    if kind == "scheduled_detach":
        # M-047:只棄掉上層、留下下層;「捨て札にならない」的效果也不阻止。魔物已離場或上層已不是那張卡時不處理
        st.modifiers.remove(obj)
        slot = st.slot_by_uid(obj.target_player, obj.target_slot)
        if slot is not None and len(slot.stack) > 1 and slot.top == obj.source:
            _detach_top(game, batch, obj.target_player, slot, reason="scheduled")
        return
    if kind == "end_phase_field":           # PR-011:場上卡的結束階段效果
        st.players[st.turn_player].used_abilities.add(f"end_phase:{source}:{obj.uid}")
        reg.END_PHASE[source](game, batch, st.turn_player, obj)
        return
    st.standby.remove(obj)
    game.emit(batch, "standby_resolved", card=source, kind=kind)
    if kind == "end_phase_mp":              # E-038:結束階段 MP 增加(強制翻頁之前)
        gain_mp(game, batch, obj.owner, obj.data.get("amount", 0), source, by=obj.owner)
    elif kind == "end_phase_turn_opponent":   # E-041:效果的翻頁,不獲得 MP,翻完即敗
        turn_pages(game, batch, 1 - obj.owner, obj.data.get("leaves", 1), source)
    elif kind == "end_phase_discard":       # E-042 / Ex-021:使用時選定的魔物(之後已離場的跳過)
        for player, uid in obj.data.get("slots", []):
            slot = st.slot_by_uid(player, uid)
            if slot is not None:
                _discard_slot(game, batch, player, slot, reason="effect")
    elif kind == "end_phase_discard_partners":   # M-061:雙方全部搭檔;對手受 M-049 / M-066 保護的除外
        from .effects.primitives import discard_partner, partner_discard_guarded
        for player in (obj.owner, 1 - obj.owner):
            for slot in st.players[player].slots:
                if slot.partner and not (player != obj.owner and partner_discard_guarded(game, player, slot)):
                    discard_partner(game, batch, player, slot, source)


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
    # S-090:「このターンが終わると捨て札になる」的搭檔(那時仍裝在那隻魔物上才棄掉)
    for m in [m for m in st.modifiers if m.kind == "discard_partner_at_turn_end"]:
        slot = st.slot_by_uid(m.target_player, m.target_slot)
        if slot is not None and slot.partner == m.data.get("card"):
            slot.partner = None
            to_discard(st.players[m.target_player], m.data["card"])
            game.emit(batch, "card_discarded", player=m.target_player, card=m.data["card"], zone="partner",
                      reason="turn_end", slot=slot.uid)
    # 時效到期與回合收尾
    st.modifiers = [m for m in st.modifiers if not _expires_now(m, st.turn_no)]
    st.standby = [s for s in st.standby
                  if not (s.data.get("expires", "turn") in ("turn", "next_battle")
                          and s.created_turn == st.turn_no)
                  and not (s.created_turn < st.turn_no and not s.data.get("own_start"))]   # M-067:到擁有者的開始階段
    for p in st.players:
        p.spell_page_uses.clear()
        p.used_abilities.clear()
        p.used_nonbattle_pages.clear()
        p.events_used_this_turn = 0
        p.dealt_damage_this_turn = False
        p.mp_reduced_by_opponent = 0
        p.start_phase_mp_gain = 0
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
    if m.duration == DUR_UNTIL_END_OWN_NEXT_TURN:
        return turn_no >= m.created_turn + 2
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
    place_slot(ps.slots, slot)
    ps.consumed_pages.add(page)
    game.emit(batch, "card_played", player=player, card=number, slot=slot.uid, zone="mamodo", forced=True)
    run_on_play(game, batch, player, slot, number)


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
