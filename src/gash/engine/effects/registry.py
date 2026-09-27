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
    on_win_owns_damage: bool = False      # on_win 自行呼叫 _start_damage 處理完整傷害流程,呼叫後不再執行預設分支(S-036)
    damage_cap: int | None = None         # 傷害上限(S-032/S-034)
    injure_instead: bool = False          # 獲勝時負傷對手魔物代替魔本傷害(S-058)
    on_defense_damaged: Callable | None = None  # 以此術防禦卻被造成傷害後 fn(game, batch, defender, amount)
    damage_bonus: Callable | None = None  # 依合計魔力調整傷害 fn(game, battle) -> int(S-042)


SPELL_RIDERS: dict[str, SpellRider] = {}

# 非戰鬥術卡 handler(自分/相手のターン、不經戰鬥流程直接使用): fn(game, batch, player)
SPELL_NONBATTLE: dict[str, Callable] = {}

# 疊放魔物(變身後): 卡號 -> 變身前魔物卡號集合
STACK_ON: dict[str, set[str]] = {}

# 只能經卡片效果疊放、不可自對頁直接放出(M-027 需經傑貝爾術)
SPELL_ONLY_STACK: set[str] = set()

# 疊放頂層單獨入墓、下層保留(M-027);分離時發出 stack_detached 事件供觸發器使用
DETACH_KEEP_UNDER: set[str] = set()

# 同名魔物同場上限(未註冊=1;M-024=2)
MAX_COPIES: dict[str, int] = {}

# [IN PLAY] 事件型觸發器: 事件型別 -> [(卡號, fn(game, batch, owner, slot, event))]
TRIGGERS: dict[str, list[tuple[str, Callable]]] = {}

# 查詢型 hook(驗證/結算時查詢場上卡)
# 傷害/負傷免疫: 卡號 -> fn(game, player, slot, ctx) -> bool(True=免疫)
DAMAGE_IMMUNITY: dict[str, Callable] = {}
# 術相容性擴充: 場上魔物卡號 -> fn(game, player, slot, spell_card) -> bool(True=可為其出此術)
SPELL_COMPAT: dict[str, Callable] = {}

# 無術攻擊(M-027): 卡號 -> {"mp_cost": int, "power": int, "damage": int}
MAMODO_ATTACK: dict[str, dict] = {}

# pending choice 的解決器: key -> fn(game, batch, choice_value, data)
CHOICE_RESOLVERS: dict[str, Callable] = {}


def _slot_hook(table: dict, number: str, hook: str, effect):
    """on_play / on_discard / start_phase 共用:effect= 註冊效果樹,否則回傳裝飾器。"""
    if effect is not None:
        from . import tree
        table[number] = tree.register_slot_hook(number, hook, effect, number in table)
        return None

    def deco(fn):
        if _tree_claimed(number, hook):
            raise ValueError(f"{number} 的 {hook} 掛鉤已以效果樹註冊")
        table[number] = fn
        return fn
    return deco


def on_play(number: str, *, effect=None):
    return _slot_hook(ON_PLAY, number, "on_play", effect)


def on_discard(number: str, *, effect=None):
    return _slot_hook(ON_DISCARD, number, "on_discard", effect)


def start_phase(number: str, *, effect=None):
    return _slot_hook(START_PHASE, number, "start_phase", effect)


def _value_hook(table: dict, number: str, hook: str, value):
    """查詢型掛鉤(回傳數值 / 真假,不是效果):value= 直接登記可呼叫的規格物件,否則回傳裝飾器。"""
    if value is not None:
        if number in table:
            raise ValueError(f"{number} 的 {hook} 已註冊")
        table[number] = value
        return None

    def deco(fn):
        table[number] = fn
        return fn
    return deco


def static_power(number: str, *, value=None):
    """常駐魔力加成 fn(game, player, slot) -> int。value= 通常是 tree.PowerBonus(number, spec)。"""
    if value is not None:
        from . import tree
        value = tree.PowerBonus(number, value)
    return _value_hook(STATIC_POWER, number, "static_power", value)


def activated(number: str, *, effect=None, **kwargs):
    """啟動型效果。effect= 註冊效果樹(mode / mp_cost / timing / per_game / condition 照舊由引擎檢查);
    否則回傳裝飾器。任何檢查失敗時,註冊表保持不變。"""
    if effect is not None:
        from . import tree
        Activated(handler=_no_handler, **kwargs)      # 先驗證參數,失敗不留痕跡
        handler = tree.register_slot_hook(number, "activated", effect, number in ACTIVATED)
        ACTIVATED[number] = Activated(handler=handler, **kwargs)
        return None

    def deco(fn):
        if _tree_claimed(number, "activated"):
            raise ValueError(f"{number} 的 activated 掛鉤已以效果樹註冊")
        ACTIVATED[number] = Activated(handler=fn, **kwargs)
        return fn
    return deco


def _no_handler(game, batch, player, slot):
    raise AssertionError("僅供驗證參數用")


def _tree_claimed(number: str, hook: str) -> bool:
    from . import tree
    return (number, hook) in tree.TREE_HOOKS


def event(number: str, condition: Callable | None = None, *, effect=None, when: Callable | None = None):
    """事件卡註冊。裝飾器形式註冊 handler;`effect=<效果樹>` 形式直接註冊效果樹(`when` 為使用前置條件)。"""
    if effect is not None:
        from . import tree
        EVENT[number] = tree.register_event(number, effect)
        if when is not None:
            EVENT_CONDITION[number] = when
        return None

    def deco(fn):
        if _tree_claimed(number, "event"):
            raise ValueError(f"{number} 的 event 掛鉤已以效果樹註冊")
        EVENT[number] = fn
        if condition is not None:
            EVENT_CONDITION[number] = condition
        return fn
    return deco


def spell_rider(number: str, **kwargs):
    """術卡附加效果,每張卡只能註冊一次(整筆記錄,不做部分更新)。

    on_declare / on_damage / on_win / on_defense_damaged 可傳可呼叫物件或效果樹。
    任何檢查失敗時,註冊表保持不變。
    """
    from . import tree
    if number in SPELL_RIDERS:
        raise ValueError(f"{number} 的術卡附加效果已註冊,每張卡只能註冊一次")
    misplaced = [k for k, v in kwargs.items()
                 if isinstance(v, tree.Effect) and k not in tree.RIDER_TREE_HOOKS]
    if misplaced:
        raise ValueError(f"{number} 的 {', '.join(misplaced)} 不是效果掛鉤,不能傳效果樹")
    trees = {h: kwargs[h] for h in tree.RIDER_TREE_HOOKS
             if isinstance(kwargs.get(h), tree.Effect)}
    for hook, root in trees.items():        # 先驗證樹與掛鉤是否被佔用
        tree.validate_tree(root)
        tree.check_free(number, f"rider.{hook}")
    # 用佔位值試建構,確認 kwargs 對 SpellRider 合法(拼錯的關鍵字在此就被拒絕)——
    # 此時尚未寫入 TREE_HOOKS / EFFECTS,失敗不留下任何痕跡。
    SpellRider(**{**kwargs, **{h: None for h in trees}})
    for hook, root in trees.items():        # 通過後才真正安裝樹,換成包裝後的 handler
        kwargs[hook] = tree.rider_hook(number, hook, root)
    SPELL_RIDERS[number] = SpellRider(**kwargs)
    return SPELL_RIDERS[number]


def spell_nonbattle(number: str, *, effect=None):
    """非戰鬥術註冊。裝飾器形式註冊 handler;`effect=<效果樹>` 形式直接註冊效果樹。"""
    if effect is not None:
        from . import tree
        SPELL_NONBATTLE[number] = tree.register_spell_nonbattle(number, effect)
        return None

    def deco(fn):
        if _tree_claimed(number, "spell_nonbattle"):
            raise ValueError(f"{number} 的 spell_nonbattle 掛鉤已以效果樹註冊")
        SPELL_NONBATTLE[number] = fn
        return fn
    return deco


def choice_resolver(key: str):
    def deco(fn):
        CHOICE_RESOLVERS[key] = fn
        return fn
    return deco


def trigger(number: str, event_type: str, *, effect=None):
    """[IN PLAY] 事件型觸發器:該卡在場上且事件發生時執行。effect= 註冊效果樹(ctx 含 event)。"""
    if effect is not None:
        from . import tree
        legacy = any(n == number for n, _ in TRIGGERS.get(event_type, []))
        handler = tree.register_trigger(number, event_type, effect, legacy)
        TRIGGERS.setdefault(event_type, []).append((number, handler))
        return None

    def deco(fn):
        if _tree_claimed(number, f"trigger.{event_type}"):
            raise ValueError(f"{number} 的 trigger.{event_type} 掛鉤已以效果樹註冊")
        TRIGGERS.setdefault(event_type, []).append((number, fn))
        return fn
    return deco


def damage_immunity(number: str, *, check=None):
    """傷害 / 負傷免疫查詢 fn(game, player, slot, ctx) -> bool。"""
    return _value_hook(DAMAGE_IMMUNITY, number, "damage_immunity", check)


def spell_compat(number: str, *, check=None):
    """術相容性擴充查詢 fn(game, player, slot, spell_card) -> bool。"""
    return _value_hook(SPELL_COMPAT, number, "spell_compat", check)
