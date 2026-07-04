"""卡片效果註冊表:引擎透過這些掛鉤呼叫各卡效果,各卡 handler 於 effects 子模組註冊。

香草術卡(效果僅「攻/防獲勝→對魔本傷害N」)完全由卡片資料驅動,不需註冊。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

# fn(game, batch, player, slot) — 魔物/夥伴進場時
ON_PLAY: dict[str, Callable] = {}

# fn(game, batch, player, slot) — 該卡被棄掉時(M-009)
ON_DISCARD: dict[str, Callable] = {}

# fn(game, player, slot) -> int — 常在魔力加成(此卡在場上)
STATIC_POWER: dict[str, Callable] = {}

# fn(game, batch, player, slot) — 回合玩家開始階段的常在效果(M-002)
START_PHASE: dict[str, Callable] = {}


@dataclass
class Activated:
    """啟動型效果(場上卡)。mode: declare(宣告使用)/ mp(MP減少N)/ discard(將此卡棄掉)"""
    mode: str
    handler: Callable                     # fn(game, batch, player, slot)
    mp_cost: int = 0
    timing: str = "any"                   # any / battle / nonbattle
    per_game: bool = False
    condition: Callable | None = None     # fn(game, player, slot) -> bool


ACTIVATED: dict[str, Activated] = {}

# 事件卡 handler: fn(game, batch, player, page)
EVENT: dict[str, Callable] = {}

# 事件卡使用前置條件: fn(game, player) -> bool(於支付費用前檢查)
EVENT_CONDITION: dict[str, Callable] = {}

# 非香草術卡的附加效果
@dataclass
class SpellRider:
    on_declare: Callable | None = None    # 宣告時(擲硬幣等) fn(game, batch, player, side)
    on_win: Callable | None = None        # 該側獲勝時(取代或附加於傷害) fn(game, batch, player)
    on_damage: Callable | None = None     # 造成傷害後 fn(game, batch, player)
    counter: bool = False                 # 【反擊】防方獲勝時仍解決
    no_book_damage: bool = False          # 獲勝時不造成魔本傷害(改由 on_win 處理)


SPELL_RIDERS: dict[str, SpellRider] = {}

# 疊放魔物(變身後): 卡號 -> 變身前魔物卡號集合
STACK_ON: dict[str, set[str]] = {}

# pending choice 的解決器: key -> fn(game, batch, choice_value, data)
CHOICE_RESOLVERS: dict[str, Callable] = {}


def on_play(number: str):
    def deco(fn):
        ON_PLAY[number] = fn
        return fn
    return deco


def on_discard(number: str):
    def deco(fn):
        ON_DISCARD[number] = fn
        return fn
    return deco


def static_power(number: str):
    def deco(fn):
        STATIC_POWER[number] = fn
        return fn
    return deco


def start_phase(number: str):
    def deco(fn):
        START_PHASE[number] = fn
        return fn
    return deco


def activated(number: str, **kwargs):
    def deco(fn):
        ACTIVATED[number] = Activated(handler=fn, **kwargs)
        return fn
    return deco


def event(number: str, condition: Callable | None = None):
    def deco(fn):
        EVENT[number] = fn
        if condition is not None:
            EVENT_CONDITION[number] = condition
        return fn
    return deco


def spell_rider(number: str, **kwargs):
    SPELL_RIDERS[number] = SpellRider(**kwargs)
    return SPELL_RIDERS[number]


def choice_resolver(key: str):
    def deco(fn):
        CHOICE_RESOLVERS[key] = fn
        return fn
    return deco
