"""卡片效果註冊表:引擎透過這些掛鉤呼叫各卡效果,各卡 handler 於 effects 子模組註冊。

香草戰術卡(效果僅「攻/防獲勝→對魔書傷害N」)完全由卡片資料驅動,不需註冊。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

# fn(game, batch, player, slot) — 魔物/搭檔進場時
ON_PLAY: dict[str, Callable] = {}

# fn(game, batch, player, slot) — 該卡被棄掉時(M-009)
ON_DISCARD: dict[str, Callable] = {}

# fn(game, player, slot) -> int — 常在魔力加成(此卡在場上)
STATIC_POWER: dict[str, Callable] = {}

# fn(game, batch, player, slot) — 回合玩家開始階段的常在效果(M-002)
START_PHASE: dict[str, Callable] = {}

# 結束階段觸發的常駐效果(PR-011):fn(game, batch, player, slot);與結束階段的待命一起由回合玩家定序。
# END_PHASE_WHEN:觸發條件(條件型,test(game, ctx));不成立時不列入結束階段的效果
END_PHASE: dict[str, Callable] = {}
END_PHASE_WHEN: dict[str, Any] = {}

# 常駐的戰術魔力加成(PR-004):fn(game, player, spell_card) -> int
STATIC_SPELL_POWER: dict[str, Callable] = {}

# 常駐的合計魔力加成(Ex-036):fn(game, player, slot) -> int;slot 為該方戰鬥中的魔物
STATIC_TOTAL_POWER: dict[str, Callable] = {}


@dataclass
class Activated:
    """啟動型效果(場上卡)。mode: declare(宣告使用)/ mp(MP減少N)/ discard(將此卡棄掉)"""
    mode: str
    handler: Callable                     # fn(game, batch, player, slot)
    mp_cost: int = 0
    timing: str = "any"                   # any / battle / nonbattle
    own_turn: bool = False                # 只能在自己的回合使用(M-018)
    per_game: bool = False
    condition: Callable | None = None     # fn(game, player, slot) -> bool


ACTIVATED: dict[str, Activated] = {}

# 事件卡 handler: fn(game, batch, player, page)
EVENT: dict[str, Callable] = {}

# 事件卡使用前置條件: fn(game, player) -> bool(於支付費用前檢查)
EVENT_CONDITION: dict[str, Callable] = {}

# 非香草戰術卡的附加效果
@dataclass
class SpellRider:
    on_declare: Callable | None = None    # 宣告時(擲硬幣等) fn(game, batch, player, side)
    on_win: Callable | None = None        # 該側獲勝時(取代或附加於傷害) fn(game, batch, player)
    on_damage: Callable | None = None     # 造成傷害後 fn(game, batch, player)
    counter: bool = False                 # 【反擊】防方獲勝時仍解決
    no_book_damage: bool = False          # 獲勝時不造成魔書傷害(改由 on_win 處理)
    on_win_owns_damage: bool = False      # on_win 自行呼叫 _start_damage 處理完整傷害流程,呼叫後不再執行預設分支(S-036)
    damage_cap: int | None = None         # 傷害上限(S-032/S-034)
    injure_instead: bool = False          # 獲勝時負傷對手魔物代替魔書傷害(S-058)
    on_defense_damaged: Callable | None = None  # 以此戰術防禦卻被造成傷害後 fn(game, batch, defender, amount)
    damage_bonus: Callable | None = None  # 依合計魔力調整傷害 fn(game, battle) -> int(S-042)
    damage_regardless: bool = False       # 不論魔力勝負都造成攻擊的傷害(攻擊被無效時除外)(S-100)
    extra_cost: tuple | None = None       # 宣告時的追加費用 (step, max, power, damage):每 step 魔力 +power、傷害 +damage(S-067 / S-097)
    counter_damage_from_attack: bool = False  # 【反擊】傷害等於對手攻擊的傷害(S-061)
    fixed_total: dict | None = None       # 合計魔力固定值 {"attack": n, "defense": n},不加其他加成(S-087)
    on_counter: Callable | None = None    # 【反擊】防方獲勝時取代預設的反擊傷害,自行處理到戰鬥結束 fn(game, batch, defender)(S-109)
    on_protected: Callable | None = None  # 此戰術攻擊的傷害被保護後 fn(game, batch, attacker)(S-112)


SPELL_RIDERS: dict[str, SpellRider] = {}

# 非戰鬥戰術卡 handler(自分/相手のターン、不經戰鬥流程直接使用): fn(game, batch, player)
SPELL_NONBATTLE: dict[str, Callable] = {}

# 非戰鬥戰術使用前置條件: fn(game, player) -> bool(於支付費用前檢查;不成立拒絕 spell.condition)
SPELL_NONBATTLE_CONDITION: dict[str, Callable] = {}

# 疊放魔物(變身後): 卡號 -> 變身前魔物卡號集合
STACK_ON: dict[str, set[str]] = {}

# 依家族疊放(M-047「自分の『ガッシュ・ベル』に重ねる」): 卡號 -> 家族名;疊在該家族、非疊放型的魔物上
STACK_ON_FAMILY: dict[str, str] = {}

# 場上時視為另一個魔物(M-047「『ガッシュ・ベル』としてあつかう」): 卡號 -> 名稱(名稱與家族判定都用它)
TREATED_AS: dict[str, str] = {}

# 「1アクションを使って…捨て札にできる」(M-046 / P-020): 卡號 -> "top"(棄掉疊放的上層)/ "partner"(棄掉搭檔)
ACTION_DISCARD: dict[str, str] = {}

# 只能經卡片效果疊放、不可自對頁直接放出(M-027 需經傑貝爾戰術)
SPELL_ONLY_STACK: set[str] = set()

# 疊放頂層單獨入墓、下層保留(M-027);分離時發出 stack_detached 事件供觸發器使用
DETACH_KEEP_UNDER: set[str] = set()

# 專用規則(《》以外的文字,不是效果,不受「使えない」影響;game-engine「專用規則不是效果」)
# 放出時的規則: 卡號 -> fn(game, batch, player, slot)(M-047 的定時離場)
RULE_ON_PLAY: dict[str, Callable] = {}
# 戰術相容的規則: 場上魔物卡號 -> fn(game, player, slot, spell_card) -> bool(M-029「この魔物で『ザケル』を使える」)
RULE_SPELL_COMPAT: dict[str, Callable] = {}

# 同名魔物同場上限(未註冊=1;M-024=2)
MAX_COPIES: dict[str, int] = {}

# [IN PLAY] 事件型觸發器: 事件型別 -> [(卡號, fn(game, batch, owner, slot, event))]
TRIGGERS: dict[str, list[tuple[str, Callable]]] = {}

# 查詢型 hook(驗證/結算時查詢場上卡)
# 傷害/負傷免疫: 卡號 -> fn(game, player, slot, ctx) -> bool(True=免疫)
DAMAGE_IMMUNITY: dict[str, Callable] = {}
# 戰術相容性擴充: 場上魔物卡號 -> fn(game, player, slot, spell_card) -> bool(True=可為其出此戰術)
SPELL_COMPAT: dict[str, Callable] = {}

# ジャマー(妨礙者):場上魔物卡號 -> {"mp_cost": int, "discard_self": bool, "on": "mamodo_effect" | "event"};
# 對手完成對應的動作(使用魔物的啟動效果 M-026 / 使用事件卡 M-032)後立即詢問是否使其無效
JAMMER: dict[str, dict] = {}

# 戰術卡每張每回合可用次數: 場上魔物卡號 -> fn(game, player, spell_card) -> int | None(None=不影響;M-024)
SPELL_USE_LIMIT: dict[str, Callable] = {}

# 擲幣重擲(M-012 / M-019): 場上魔物卡號 -> "self"(重擲自己擲的硬幣)/ "opponent"(令對手重擲);
# 只在擲硬幣子階段(primitives.flip_coins)中詢問,不能主動宣告
COIN_REFLIP: dict[str, str] = {}

# 把自己擲的 1 枚硬幣改成正面(M-034,棄掉自己);只在擲硬幣子階段中詢問
COIN_SET_HEADS: set[str] = set()

# 魔物效果攻擊(M-027): 卡號 -> {"mp_cost": int, "power": int, "damage": int}
MAMODO_ATTACK: dict[str, dict] = {}

# 魔物效果防禦(M-039): 卡號 -> {"mp_cost": int, "power": int}
MAMODO_DEFENSE: dict[str, dict] = {}

# 此魔物身上的搭檔不會被對手的效果棄掉(M-049)
PARTNER_DISCARD_GUARD: set[str] = set()

# 此卡在場上時,對手不能使用指定家族魔物的「魔物の効果」與指定名稱的事件卡(P-031): 卡號 -> (家族, 事件卡名)
BLOCK_OPPONENT_FAMILY: dict[str, tuple[str, str]] = {}

# 此搭檔在場上時,戰鬥階段中持有者的 MP 不因對手的效果減少、不因自己的效果增加(P-020)
BATTLE_PHASE_MP_LOCK: set[str] = set()

# 此搭檔在場上時,持有者的戰鬥階段中對手不能使用事件卡(P-038)
OPPONENT_EVENT_LOCK: set[str] = set()

# 攻擊時解決的待命(「このターン中の次のバトルで、…攻撃したとき」M-055 / P-043):
# 卡號 -> (效果樹 id, 條件 fn(game, standby, attack) -> bool);待命種類 on_attack,由 tree.ScheduleOnAttack 排定
ON_ATTACK: dict[str, tuple[str, Callable]] = {}

# 「術を使えない」時仍可使用「這隻魔物の術」(M-038;engine.spell_block 依名稱判定)
IGNORE_SPELL_BLOCK: set[str] = set()

# 不能保護的魔物(「かばうことができる」時也不能;M-051)
CANNOT_PROTECT: set[str] = set()

# 此卡在場上時,對手使用事件卡的費用增加量(M-040)
OPPONENT_EVENT_COST: dict[str, int] = {}

# 此卡在場上時,持有者看得到對手翻開的頁(P-024)
REVEAL_OPPONENT_PAGES: set[str] = set()

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


def end_phase(number: str, *, effect, when=None):
    """自己的結束階段觸發的常駐效果(PR-011);when 為觸發條件。"""
    if when is not None:
        END_PHASE_WHEN[number] = when
    return _slot_hook(END_PHASE, number, "end_phase", effect)


def static_spell_power(number: str, *, value=None):
    """常駐的戰術魔力加成 fn(game, player, spell_card) -> int(PR-004)。"""
    return _value_hook(STATIC_SPELL_POWER, number, "static_spell_power", value)


def static_total_power(number: str, *, value=None):
    """常駐的合計魔力加成 fn(game, player, slot) -> int(Ex-036)。"""
    return _value_hook(STATIC_TOTAL_POWER, number, "static_total_power", value)


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
    """戰術卡附加效果,每張卡只能註冊一次(整筆記錄,不做部分更新)。

    on_declare / on_damage / on_win / on_defense_damaged 可傳可呼叫物件或效果樹。
    任何檢查失敗時,註冊表保持不變。
    """
    from . import tree
    if number in SPELL_RIDERS:
        raise ValueError(f"{number} 的戰術卡附加效果已註冊,每張卡只能註冊一次")
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


def spell_nonbattle(number: str, *, effect=None, when: Callable | None = None):
    """非戰鬥戰術註冊。裝飾器形式註冊 handler;`effect=<效果樹>` 形式直接註冊效果樹。
    `when` 為使用前置條件(例如選得到對象),與事件卡的 `when` 相同介面。"""
    if when is not None:
        SPELL_NONBATTLE_CONDITION[number] = when
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


def spell_use_limit(number: str, *, value=None):
    """此卡在場上時,戰術卡每張每回合可用次數的查詢 fn(game, player, spell_card) -> int | None。"""
    return _value_hook(SPELL_USE_LIMIT, number, "spell_use_limit", value)


def spell_compat(number: str, *, check=None):
    """戰術相容性擴充查詢 fn(game, player, slot, spell_card) -> bool。"""
    return _value_hook(SPELL_COMPAT, number, "spell_compat", check)


# 常駐效果(「このカードが場にある→」,持續中或之後仍可能發動)所在的登記表;快照據此列出失效中的效果。
# ON_PLAY(出場時已解決)與 IGNORE_SPELL_BLOCK(M-038「使えないときにも使える」)不在內。
PASSIVE_TABLES = ("START_PHASE", "END_PHASE", "STATIC_POWER", "STATIC_SPELL_POWER", "STATIC_TOTAL_POWER", "ON_DISCARD", "SPELL_COMPAT", "SPELL_USE_LIMIT", "DAMAGE_IMMUNITY",
                  "OPPONENT_EVENT_COST", "REVEAL_OPPONENT_PAGES", "PARTNER_DISCARD_GUARD", "BATTLE_PHASE_MP_LOCK",
                  "BLOCK_OPPONENT_FAMILY", "OPPONENT_EVENT_LOCK")


def has_passive(number: str | None) -> bool:
    """number 有常駐效果(PASSIVE_TABLES 或事件型觸發器)。"""
    if number is None:
        return False
    tables = globals()
    return (any(number in tables[name] for name in PASSIVE_TABLES)
            or any(n == number for regs in TRIGGERS.values() for n, _ in regs))


# ---------------------------------------------------------------- 純資料登記(不是效果)

def rule_on_play(number: str, *, effect):
    """放出時執行的專用規則(效果樹);與 on_play 不同,不受「使えない」影響。"""
    _slot_hook(RULE_ON_PLAY, number, "rule_on_play", effect)


def rule_spell_compat(number: str, *, check):
    """戰術相容的專用規則 fn(game, player, slot, spell_card) -> bool;與 spell_compat 不同,不受「使えない」影響。"""
    _value_hook(RULE_SPELL_COMPAT, number, "rule_spell_compat", check)


def stack_on(number: str, *, base=(), family: str | None = None, spell_only: bool = False,
             detach_keep_under: bool = False):
    """number 為疊放魔物,可疊在 base(卡號組)或 family(家族名,非疊放型的該家族魔物)上;
    spell_only=只能經卡片效果疊放;detach_keep_under=單獨入墓時下層保留(發出 stack_detached)。"""
    if number in STACK_ON:
        raise ValueError(f"{number} 的 stack_on 已登記")
    if not base and not family:
        raise ValueError(f"{number} 的 stack_on 須指定 base 或 family")
    STACK_ON[number] = set(base)
    if family:
        STACK_ON_FAMILY[number] = family
    if spell_only:
        SPELL_ONLY_STACK.add(number)
    if detach_keep_under:
        DETACH_KEEP_UNDER.add(number)


def max_copies(number: str, n: int):
    """同名魔物同場上限(未登記 = 1)。"""
    if number in MAX_COPIES:
        raise ValueError(f"{number} 的 max_copies 已登記")
    MAX_COPIES[number] = n


def jammer(number: str, *, mp_cost: int = 0, discard_self: bool = False, on: str = "mamodo_effect"):
    """ジャマー效果:對手完成 on 的動作(mamodo_effect:使用「魔物的效果」(啟動型)/ event:使用事件卡)後
    立即詢問是否使用(支付 mp_cost;discard_self 時把這張卡棄掉)使其無效。不能主動宣告(不登記為 activated)。"""
    if on not in ("mamodo_effect", "event"):
        raise ValueError(f"{number} 的 jammer on 須為 mamodo_effect / event")
    if number in JAMMER:
        raise ValueError(f"{number} 的 jammer 已登記")
    JAMMER[number] = {"mp_cost": mp_cost, "discard_self": discard_self, "on": on}


def coin_reflip(number: str, *, coins: str):
    """擲幣重擲(「魔物の効果」,每回合一次):coins="self" 重擲自己擲的 1 枚,"opponent" 令對手重擲。
    擲幣後由引擎在擲硬幣子階段中詢問,不能主動宣告(不登記為 activated)。"""
    if coins not in ("self", "opponent"):
        raise ValueError(f"{number} 的 coin_reflip coins 須為 self / opponent")
    if number in COIN_REFLIP:
        raise ValueError(f"{number} 的 coin_reflip 已登記")
    COIN_REFLIP[number] = coins


def coin_set_heads(number: str):
    """把自己擲的 1 枚硬幣改成正面(棄掉這張卡);擲幣後由引擎在擲硬幣子階段中詢問(M-034)。"""
    COIN_SET_HEADS.add(number)


def treated_as(number: str, name: str):
    """此卡在場上時視為名為 name 的魔物(名稱、家族判定)(M-047)。"""
    TREATED_AS[number] = name


def action_discard(number: str, what: str):
    """「1アクションを使って…捨て札にできる」:what="top" 棄掉疊放的上層、"partner" 棄掉搭檔。"""
    if what not in ("top", "partner"):
        raise ValueError(f"{number} 的 action_discard 須為 top / partner")
    ACTION_DISCARD[number] = what


def mamodo_defense(number: str, *, mp_cost: int, power: int):
    """魔物效果防禦規格:支付 mp_cost,以合計魔力 power 防禦(M-039)。"""
    if number in MAMODO_DEFENSE:
        raise ValueError(f"{number} 的 mamodo_defense 已登記")
    MAMODO_DEFENSE[number] = {"mp_cost": mp_cost, "power": power}


def partner_discard_guard(number: str):
    """此魔物身上的搭檔不會被對手的效果棄掉(M-049)。"""
    PARTNER_DISCARD_GUARD.add(number)


def block_opponent_family(number: str, *, family: str, event_name: str):
    """此卡在場上時,對手不能使用 family 魔物的「魔物の効果」與名為 event_name 的事件卡(P-031)。"""
    BLOCK_OPPONENT_FAMILY[number] = (family, event_name)


def battle_phase_mp_lock(number: str):
    """戰鬥階段中持有者的 MP 不因對手的效果減少、不因自己的效果增加(P-020)。"""
    BATTLE_PHASE_MP_LOCK.add(number)


def opponent_event_lock(number: str):
    """此搭檔在場上時,持有者的戰鬥階段中對手不能使用事件卡(P-038)。"""
    OPPONENT_EVENT_LOCK.add(number)


def on_attack(number: str, *, effect, when: Callable):
    """攻擊時解決的待命效果:下一場戰鬥開始時 when(game, standby, attack) 成立才在防禦宣告前執行 effect
    (效果樹,可建立決策);不成立時待命隨該戰鬥結束而消失。"""
    from . import tree
    effect_id = tree.register_on_attack(number, effect)
    ON_ATTACK[number] = (effect_id, when)


def mamodo_attack(number: str, *, mp_cost: int, power: int, damage: int, per_turn: int = 1):
    """魔物效果攻擊規格:支付 mp_cost,以合計魔力 power 攻擊,造成 damage 點傷害;
    每回合可用 per_turn 次(效果文明示次數時,如 M-068「1ターンに2回まで」)。"""
    if number in MAMODO_ATTACK:
        raise ValueError(f"{number} 的 mamodo_attack 已登記")
    MAMODO_ATTACK[number] = {"mp_cost": mp_cost, "power": power, "damage": damage, "per_turn": per_turn}


def ignore_spell_block(number: str):
    """「術を使えない」時,「這隻魔物の術」(名稱,含其他魔物使用的與這隻使用的戰術)仍可使用(M-038)。"""
    IGNORE_SPELL_BLOCK.add(number)


def cannot_protect(number: str):
    """這隻魔物不能保護,任何效果都不能使它保護(M-051)。"""
    CANNOT_PROTECT.add(number)


def opponent_event_cost(number: str, amount: int):
    """此卡在場上時,對手使用事件卡的費用 +amount(M-040)。"""
    if number in OPPONENT_EVENT_COST:
        raise ValueError(f"{number} 的 opponent_event_cost 已登記")
    OPPONENT_EVENT_COST[number] = amount


def reveal_opponent_pages(number: str):
    """此卡在場上時,持有者看得到對手翻開的頁(P-024)。"""
    REVEAL_OPPONENT_PAGES.add(number)
