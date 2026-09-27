"""尚未遷移到效果樹的魔物卡(依日版 j 文意)。已遷移的魔物卡見 tree_cards.py。

進度見 openspec/changes/effect-tree-migration/tasks.md 第 4 組。
"""

from __future__ import annotations

from ..cards import MAMODO
from ..state import DUR_BATTLE, PendingChoice
from . import registry as reg
from .primitives import attach_partner_from_book, choose_or_auto, turn_pages

# 疊放魔物(變身後)
reg.STACK_ON["M-007"] = {"M-006"}
reg.STACK_ON["M-010"] = {"M-009"}


# M-011 フェイン:[宣告使用] 檢視對手魔本,棄掉 1 張魔物卡(一場遊戲限一次)
def _m011_condition(game, player, slot):
    opp = game.state.players[1 - player]
    return any(
        game.db[opp.card_at(p)].type == MAMODO
        for p in range(1, 33) if p not in opp.consumed_pages
    )


@reg.activated("M-011", mode="declare", timing="nonbattle", per_game=True,
               condition=_m011_condition)
def m011(game, batch, player, slot):
    opp = game.state.players[1 - player]
    pages = [p for p in range(1, 33)
             if p not in opp.consumed_pages and game.db[opp.card_at(p)].type == MAMODO]
    game.emit(batch, "book_revealed", player=1 - player, viewer=player,
              cards=[{"page": p, "card": opp.card_at(p)}
                     for p in range(1, 33) if p not in opp.consumed_pages])
    choose_or_auto(game, batch, kind="m011_pick", player=player,
                   options=[{"value": p, "card": opp.card_at(p)} for p in pages],
                   data={"player": player}, source="M-011")


@reg.choice_resolver("m011_pick")
def m011_pick(game, batch, value, data):
    from ..engine import IllegalCommand
    player = data["player"]
    opp = game.state.players[1 - player]
    if (not isinstance(value, int) or not 1 <= value <= 32
            or value in opp.consumed_pages
            or game.db[opp.card_at(value)].type != MAMODO):
        raise IllegalCommand("choose.invalid", "須選擇對手魔本中的魔物卡")
    number = opp.card_at(value)
    opp.consumed_pages.add(value)
    opp.discard.append(number)
    game.emit(batch, "card_discarded", player=1 - player, card=number,
              zone="book", page=value, reason="M-011")


# M-016 ガッシュ《失去的記憶》:[宣告使用] 交換翻開頁與之前頁的卡(一場遊戲限一次)
def _m016_condition(game, player, slot):
    ps = game.state.players[player]
    open_now = [p for p in ps.open_pages()]
    prev = [p for p in range(1, ps.pos) if p not in ps.consumed_pages]
    return bool(open_now and prev)


@reg.activated("M-016", mode="declare", timing="nonbattle", per_game=True,
               condition=_m016_condition)
def m016(game, batch, player, slot):
    ps = game.state.players[player]
    open_now = [{"value": p, "card": ps.card_at(p)} for p in ps.open_pages()]
    game.state.pending = PendingChoice(kind="m016_open", player=player, source="M-016",
                                       options=open_now, data={"player": player})
    game.emit(batch, "choice_required", kind="m016_open", player=player, options=open_now)


@reg.choice_resolver("m016_open")
def m016_open(game, batch, value, data):
    from ..engine import IllegalCommand
    player = data["player"]
    ps = game.state.players[player]
    if value not in ps.open_pages():
        raise IllegalCommand("choose.invalid", "須選擇目前翻開頁面的卡")
    prev = [{"value": p, "card": ps.card_at(p)}
            for p in range(1, ps.pos) if p not in ps.consumed_pages]
    game.state.pending = PendingChoice(kind="m016_prev", player=player, source="M-016",
                                       options=prev, data={"player": player, "open": value})
    game.emit(batch, "choice_required", kind="m016_prev", player=player, options=prev)


@reg.choice_resolver("m016_prev")
def m016_prev(game, batch, value, data):
    from ..engine import IllegalCommand
    player = data["player"]
    ps = game.state.players[player]
    if (not isinstance(value, int) or value >= ps.pos or value < 1
            or value in ps.consumed_pages):
        raise IllegalCommand("choose.invalid", "須選擇之前頁面的卡")
    a, b = data["open"], value
    ps.book[a - 1], ps.book[b - 1] = ps.book[b - 1], ps.book[a - 1]
    game.state.pending = None
    game.emit(batch, "effect_applied", source="M-016", pages=[a, b])


# M-020 ティオ:[1MP] 自書任意頁取大海惠夥伴裝備到此魔物
def _partner_pages(game, player, mamodo_name):
    ps = game.state.players[player]
    return [{"value": p, "card": ps.card_at(p), "page": p}
            for p in range(1, 33)
            if p not in ps.consumed_pages
            and game.db[ps.card_at(p)].type == "partner"
            and game.db[ps.card_at(p)].related_mamodo == mamodo_name]


@reg.activated("M-020", mode="mp", mp_cost=1, timing="nonbattle",
               condition=lambda g, p, s: s.partner is None and bool(_partner_pages(g, p, "ティオ")))
def m020(game, batch, player, slot):
    _attach_from_book(game, batch, player, slot, "ティオ", "m020_pick")


@reg.choice_resolver("m020_pick")
def m020_pick(game, batch, value, data):
    _resolve_attach(game, batch, value, data, "ティオ")


# M-021 ハイド:[1MP] 自書任意頁取艾多夥伴裝備到此魔物
@reg.activated("M-021", mode="mp", mp_cost=1, timing="nonbattle",
               condition=lambda g, p, s: s.partner is None and bool(_partner_pages(g, p, "ハイド")))
def m021(game, batch, player, slot):
    _attach_from_book(game, batch, player, slot, "ハイド", "m021_pick")


@reg.choice_resolver("m021_pick")
def m021_pick(game, batch, value, data):
    _resolve_attach(game, batch, value, data, "ハイド")


def _attach_from_book(game, batch, player, slot, mamodo_name, resolver_key):
    options = _partner_pages(game, player, mamodo_name)
    data = {"player": player, "slot_uid": slot.uid, "mamodo": mamodo_name}
    if len(options) == 1:
        reg.CHOICE_RESOLVERS[resolver_key](game, batch, options[0]["value"], data)
        return
    game.state.pending = PendingChoice(kind=resolver_key, player=player, source="attach",
                                       options=options, data=data)
    game.emit(batch, "choice_required", kind=resolver_key, player=player, options=options)


def _resolve_attach(game, batch, value, data, mamodo_name):
    from ..engine import IllegalCommand
    player = data["player"]
    slot = game.state.slot_by_uid(player, data["slot_uid"])
    valid = {o["value"] for o in _partner_pages(game, player, mamodo_name)}
    if value not in valid or slot is None:
        raise IllegalCommand("choose.invalid", "須選擇魔本中對應的夥伴卡")
    game.state.pending = None
    attach_partner_from_book(game, batch, player, value, slot)


# M-022 ゾフィス:[5MP] 棄掉對手場上 1 張夥伴卡
@reg.activated("M-022", mode="mp", mp_cost=5, timing="nonbattle",
               condition=lambda g, p, s: any(x.partner for x in g.state.players[1 - p].slots))
def m022(game, batch, player, slot):
    opp = game.state.players[1 - player]
    options = [{"value": x.uid, "card": x.partner} for x in opp.slots if x.partner]
    choose_or_auto(game, batch, kind="m022_pick", player=player, options=options,
                   data={"player": player}, source="M-022")


@reg.choice_resolver("m022_pick")
def m022_pick(game, batch, value, data):
    from ..engine import IllegalCommand
    from .primitives import discard_partner
    player = data["player"]
    slot = game.state.slot_by_uid(1 - player, value if isinstance(value, int) else -1)
    if slot is None or not slot.partner:
        raise IllegalCommand("choose.invalid", "須選擇對手場上的夥伴卡")
    discard_partner(game, batch, 1 - player, slot, "M-022")


# M-023 ポッケリオ:[此卡在場上] 木屬性術可為此魔物使用(相容性 hook)
@reg.spell_compat("M-023")
def m023_compat(game, player, slot, spell_card):
    return slot.top == "M-023" and spell_card.attr_name == "木"


# M-024 ロブノス(二体):同名可 2 隻;比萊茲術次數上限由 M-024 查詢
reg.MAX_COPIES["M-024"] = 2


# M-025 ロブノス(完全体):登場時從墓把 Robnos 卡放回書空頁 + MP+2
@reg.on_play("M-025")
def m025(game, batch, player, slot):
    from ..engine import gain_mp
    ps = game.state.players[player]
    empties = sorted(ps.consumed_pages)
    targets = [i for i, n in enumerate(ps.discard) if n in ("M-024", "M-025")]
    if empties and targets:
        options = [{"value": i, "card": ps.discard[i]} for i in targets]
        choose_or_auto(game, batch, kind="m025_pick", player=player, options=options,
                       data={"player": player}, source="M-025")
    gain_mp(game, batch, player, 2, "M-025")


@reg.choice_resolver("m025_pick")
def m025_pick(game, batch, value, data):
    from ..engine import IllegalCommand
    from .primitives import return_to_book
    player = data["player"]
    ps = game.state.players[player]
    if not isinstance(value, int) or not 0 <= value < len(ps.discard):
        raise IllegalCommand("choose.invalid", "須選擇棄牌區的羅布諾斯卡")
    number = ps.discard[value]
    if number not in ("M-024", "M-025"):
        raise IllegalCommand("choose.invalid", "只能選羅布諾斯卡")
    empties = sorted(ps.consumed_pages)
    if not empties:
        game.state.pending = None
        return
    ps.discard.pop(value)
    return_to_book(game, batch, player, number, empties[0])
    game.state.pending = None


# M-026 マルス:[2MP] 將對手剛套用的 1 個魔物效果無效
@reg.activated("M-026", mode="mp", mp_cost=2, timing="any",
               condition=lambda g, p, s: g.state.battle is not None)
def m026(game, batch, player, slot):
    # 簡化:清除對手本場戰鬥剛加上的 power/damage 類 modifier(最近一筆)
    opp = 1 - player
    for m in reversed(game.state.modifiers):
        if m.owner == opp and m.kind in ("power", "damage_delta", "damage_double") \
                and m.duration == DUR_BATTLE:
            game.state.modifiers.remove(m)
            game.emit(batch, "effect_applied", source="M-026", negated=m.source)
            return


# M-027 バルトロ(装甲):只能經 S-048 疊放;[1MP] 不用術直接攻擊(5000/傷害2)
reg.STACK_ON["M-027"] = {"M-028"}
reg.SPELL_ONLY_STACK.add("M-027")
reg.DETACH_KEEP_UNDER.add("M-027")
reg.MAMODO_ATTACK["M-027"] = {"mp_cost": 1, "power": 5000, "damage": 2}


# M-028 バルトロ:[此卡在場上] 疊放其上的裝甲入墓時翻對手 2 頁(觸發器)
@reg.trigger("M-028", "stack_detached")
def m028(game, batch, owner, slot, ev):
    if ev.get("slot") == slot.uid and ev.get("detached") == "M-027":
        turn_pages(game, batch, 1 - owner, 2, "M-028")


# M-029 ゼオン:賈修的ザケル術可為此魔物使用;[7MP] 棄掉對手 1 隻負傷魔物
@reg.spell_compat("M-029")
def m029_compat(game, player, slot, spell_card):
    return (slot.top == "M-029" and spell_card.related_mamodo == "ガッシュ・ベル"
            and "ザケル" in (spell_card.name_ja or ""))


@reg.activated("M-029", mode="mp", mp_cost=7, timing="nonbattle",
               condition=lambda g, p, s: any(x.injured for x in g.state.players[1 - p].slots))
def m029(game, batch, player, slot):
    opp = game.state.players[1 - player]
    options = [{"value": x.uid, "card": x.top} for x in opp.slots if x.injured]
    choose_or_auto(game, batch, kind="m029_pick", player=player, options=options,
                   data={"player": player}, source="M-029")


@reg.choice_resolver("m029_pick")
def m029_pick(game, batch, value, data):
    from ..engine import IllegalCommand, _discard_slot
    player = data["player"]
    slot = game.state.slot_by_uid(1 - player, value if isinstance(value, int) else -1)
    if slot is None or not slot.injured:
        raise IllegalCommand("choose.invalid", "須選擇對手場上負傷的魔物")
    _discard_slot(game, batch, 1 - player, slot, reason="M-029")


# M-031 キクロプ:[此卡在場上] 不受合計魔力 ≤6000 的術造成的傷害與負傷
@reg.damage_immunity("M-031")
def m031_immune(game, player, slot, ctx):
    b = game.state.battle
    if b is None or ctx.get("cause") != "battle_attack":
        return False
    if b.attack_spell is None:  # 無術攻擊不算「術」
        return False
    return b.data.get("attack_total", 0) <= 6000
