"""遊戲狀態資料模型。

魔本頁面模型:pos = 目前翻開對頁的第一頁(1-based)。
- 準備階段後 pos=2(翻開第 2、3 頁);翻 1 張(1 對頁)= pos+2。
- pos=32 時只剩最後一頁;pos>32 = 魔本耗盡(敗北條件)。
- 已離開魔本的卡(魔物/夥伴放到場上)記錄於 consumed_pages;術/事件卡使用後仍留在魔本中。
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from .cards import CardDef

BOOK_SIZE = 32
MAX_FIELD_MAMODO = 3

# --- 階段 ---
SETUP = "setup"
START = "start"
BATTLE = "battle"
GAME_OVER = "game_over"
# 結束階段為自動處理,不對外暴露成可停留的階段

# --- 戰鬥子步驟 ---
BATTLE_IN = "battle_in"        # 戰鬥開始確認中(等待非回合玩家回應)
STEP_DEFENSE = "defense"       # 等待防禦宣告
STEP_EFFECTS = "effects"       # 戰鬥中效果輪流

# --- 禁止旗標 ---
NO_SPELLS = "no_spells"                    # 不能使用術卡
NO_PARTNER_EFFECTS = "no_partner_effects"  # 夥伴卡效果失效
NO_PROTECT_BOOK = "no_protect_book"        # 不能庇護魔本傷害(戰鬥時效)
NO_DEFENSE = "no_defense"                  # 不能防禦(戰鬥時效)
NO_ATTACK_SPELL = "no_attack_spell"        # 不能使用術卡攻擊(P-014)
NO_MAMODO_EFFECTS = "no_mamodo_effects"    # 魔物卡效果失效(E-025)
MAMODO_LOCKED = "mamodo_locked"            # 指定魔物:禁其術與效果(E-024,target_slot)

# --- modifier 時效 ---
DUR_BATTLE = "battle"                    # 本場戰鬥中
DUR_TURN = "turn"                        # 本回合(至結束階段完畢)
DUR_UNTIL_END_NEXT_TURN = "until_end_next_turn"  # 至下回合結束階段
DUR_NEXT_TURN = "next_turn"              # 僅下一回合中生效(E-001)


@dataclass
class Modifier:
    """持續效果。kind: power / damage_delta / damage_double / restriction / no_damage / spell_cost_zero"""
    kind: str
    source: str                 # 來源卡號
    owner: int                  # 建立者
    duration: str
    created_turn: int
    target_player: int | None = None   # 效果作用對象玩家(restriction: 被限制者)
    target_slot: int | None = None     # 作用的魔物槽 uid
    amount: int = 0
    flag: str | None = None            # restriction 旗標名
    data: dict[str, Any] = field(default_factory=dict)

    def active(self, turn_no: int) -> bool:
        if self.duration == DUR_NEXT_TURN:
            return turn_no == self.created_turn + 1
        return True


@dataclass
class Standby:
    """待命效果:於指定觸發時機自動解決。kind 由效果 handler 與引擎共同約定。"""
    kind: str                   # 例: attack_undefendable / no_defense_next_battle / start_phase_effect ...
    source: str
    owner: int
    created_turn: int
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class MamodoSlot:
    uid: int
    stack: list[str]            # 疊放的魔物卡號,最上層生效
    injured: bool = False
    partner: str | None = None

    @property
    def top(self) -> str:
        return self.stack[-1]


@dataclass
class PlayerState:
    book: list[str]                            # 32 頁卡號(效果可換頁/回書,故為可變)
    pos: int = 1                               # 目前對頁的第一頁
    mp: int = 0
    slots: list[MamodoSlot] = field(default_factory=list)
    discard: list[str] = field(default_factory=list)
    consumed_pages: set[int] = field(default_factory=set)   # 已離開魔本的頁(1-based)
    used_spell_pages: set[int] = field(default_factory=set)  # 本回合已用術卡頁
    used_event_this_turn: bool = False
    used_abilities: set[str] = field(default_factory=set)   # 本回合已用啟動效果 key
    used_nonbattle_spells: set[str] = field(default_factory=set)  # 本回合已用非戰鬥術卡號
    used_per_game: set[str] = field(default_factory=set)    # 一場遊戲限一次
    discarded_this_turn: list[str] = field(default_factory=list)  # 本回合入墓的卡(E-022)
    page_effect_used: bool = False        # 本回合已用「翻自己書頁」效果(P-010 條款)
    page_back_effect_used: bool = False   # 本回合已用「回翻自己書頁」效果(P-018 條款)

    def open_pages(self) -> list[int]:
        """目前翻開、且卡片仍在魔本中的頁碼。"""
        pages = [p for p in (self.pos, self.pos + 1) if 1 <= p <= BOOK_SIZE]
        return [p for p in pages if p not in self.consumed_pages]

    def card_at(self, page: int) -> str:
        return self.book[page - 1]

    def pages_remaining(self) -> int:
        return max(0, BOOK_SIZE + 1 - self.pos - (1 if self.pos <= BOOK_SIZE else 0))

    def book_exhausted(self) -> bool:
        return self.pos > BOOK_SIZE


@dataclass
class BattleState:
    attacker: int
    step: str                            # STEP_DEFENSE / STEP_EFFECTS
    attack_page: int | None              # 無術攻擊(M-027)時為 None
    attack_spell: str | None             # 無術攻擊時為 None
    attack_slot: int                     # 使用術(或直接攻擊)的魔物槽 uid
    attack_negated: bool = False
    attack_undefendable: bool = False
    defense_page: int | None = None
    defense_spell: str | None = None
    defense_slot: int | None = None
    defense_declared: bool = False       # 已做出防禦/不防禦決定
    defense_negated: bool = False
    effect_passes: int = 0
    data: dict[str, Any] = field(default_factory=dict)   # 效果掛載的戰鬥內旗標

    @property
    def defender(self) -> int:
        return 1 - self.attacker


@dataclass
class PendingChoice:
    """引擎等待玩家決策。kind: protect / choose_target / reflip / resolve_order ..."""
    kind: str
    player: int
    options: list[dict]
    source: str | None = None
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class GameState:
    players: list[PlayerState]
    turn_player: int = 0
    turn_no: int = 1
    phase: str = SETUP
    action_player: int | None = None      # 戰鬥階段中目前可行動者
    consecutive_passes: int = 0
    battle_in: dict | None = None         # 戰鬥開始確認中 {page, slot, attacker}
    battle: BattleState | None = None
    pending: PendingChoice | None = None
    modifiers: list[Modifier] = field(default_factory=list)
    standby: list[Standby] = field(default_factory=list)
    winner: int | None = None
    end_reason: str | None = None
    _uid_seq: int = 0

    def next_uid(self) -> int:
        self._uid_seq += 1
        return self._uid_seq

    def slot_by_uid(self, player: int, uid: int) -> MamodoSlot | None:
        for s in self.players[player].slots:
            if s.uid == uid:
                return s
        return None

    def find_mamodo(self, player: int, name: str) -> MamodoSlot | None:
        """以魔物名(英文 related_mamodo 名)找自己場上的魔物槽。"""
        from .cards import card_db
        db = card_db()
        for s in self.players[player].slots:
            if db[s.top].related_mamodo == name:
                return s
        return None


MAX_TRIGGER_DEPTH = 4  # 被動觸發器遞迴上限(防止入墓/翻頁連鎖失控)


@dataclass
class Game:
    """引擎頂層:狀態 + RNG + 卡片資料庫。"""
    state: GameState
    rng: random.Random
    db: dict[str, CardDef]
    events: list[dict] = field(default_factory=list)   # 全部歷史事件(含序號)
    _trigger_depth: int = 0

    def emit(self, batch: list[dict], type_: str, **payload) -> dict:
        ev = {"seq": len(self.events), "type": type_, **payload}
        self.events.append(ev)
        batch.append(ev)
        self._dispatch_triggers(batch, ev)
        return ev

    def _dispatch_triggers(self, batch: list[dict], ev: dict) -> None:
        """[IN PLAY] 事件型觸發器:場上有註冊此事件型別的卡時執行其 handler。"""
        from .effects import registry as reg
        regs = reg.TRIGGERS.get(ev["type"])
        if not regs or self.state.phase == GAME_OVER:
            return
        if self._trigger_depth >= MAX_TRIGGER_DEPTH:
            return  # 超出深度:安全丟棄(規則上不應發生的連鎖)
        self._trigger_depth += 1
        try:
            for number, handler in regs:
                for owner in (0, 1):
                    for slot in list(self.state.players[owner].slots):
                        if self.state.phase == GAME_OVER:
                            return
                        cards = [slot.top] + ([slot.partner] if slot.partner else [])
                        if number in cards:
                            handler(self, batch, owner, slot, ev)
        finally:
            self._trigger_depth -= 1
