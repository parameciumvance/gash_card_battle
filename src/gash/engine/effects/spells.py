"""術卡附加效果(非香草)。香草術卡(攻/防獲勝→魔本傷害)由卡片資料直接驅動。

宣告時效果(硬幣)依規則於宣告時擲出並確定。
"""

from __future__ import annotations

from ..state import DUR_UNTIL_END_NEXT_TURN, NO_PARTNER_EFFECTS, NO_SPELLS
from . import registry as reg
from .primitives import (
    add_modifier, add_restriction, choose_or_auto, discard_partner, flip_coins,
    play_mamodo_from_book, schedule_standby, take_from_book,
)


# ---- S-003 ラシルド:【反擊】防禦方獲勝時對對手魔本造成傷害
reg.spell_rider("S-003", counter=True)


# ---- 傷害後禁術(擲硬幣):S-004 ジケルド / S-014 ジュロン
def _coin_lock_spells(number):
    def on_damage(game, batch, player):
        flip_coins(game, batch, player, 1, number, "lock_spells_coin",
                   {"player": player, "source": number})
    return on_damage


@reg.choice_resolver("lock_spells_coin")
def lock_spells_coin(game, batch, results, data):
    if results[0]:
        add_restriction(game, batch, source=data["source"], owner=data["player"],
                        target_player=1 - data["player"], flag=NO_SPELLS,
                        duration=DUR_UNTIL_END_NEXT_TURN)


reg.spell_rider("S-004", on_damage=_coin_lock_spells("S-004"))
reg.spell_rider("S-014", on_damage=_coin_lock_spells("S-014"))


# ---- 傷害後禁術(必定):S-009 グラビレイ / S-011 アイアン・グラビレイ
def _lock_spells(number):
    def on_damage(game, batch, player):
        add_restriction(game, batch, source=number, owner=player,
                        target_player=1 - player, flag=NO_SPELLS,
                        duration=DUR_UNTIL_END_NEXT_TURN)
    return on_damage


reg.spell_rider("S-009", on_damage=_lock_spells("S-009"))
reg.spell_rider("S-011", on_damage=_lock_spells("S-011"))


# ---- S-007 フリズド:傷害後,對手夥伴效果失效(至其下回合結束階段)
def _s007_on_damage(game, batch, player):
    add_restriction(game, batch, source="S-007", owner=player,
                    target_player=1 - player, flag=NO_PARTNER_EFFECTS,
                    duration=DUR_UNTIL_END_NEXT_TURN)


reg.spell_rider("S-007", on_damage=_s007_on_damage)


# ---- S-016 ゼルク:以此術防禦時魔力加值
def _defense_self_bonus(amount):
    def on_declare(game, batch, player, side):
        if side == "defense":
            b = game.state.battle
            b.data["defense_self_bonus"] = b.data.get("defense_self_bonus", 0) + amount
            game.emit(batch, "effect_applied", source="defense_bonus", amount=amount)
    return on_declare


# ---- S-017 ゼルセン:以此術攻擊時魔力加值(重用攻擊方通用的 attack_spell_bonus 累加欄位)
def _attack_self_bonus(amount):
    def on_declare(game, batch, player, side):
        if side == "attack":
            b = game.state.battle
            b.data["attack_spell_bonus"] = b.data.get("attack_spell_bonus", 0) + amount
            game.emit(batch, "effect_applied", source="attack_bonus", amount=amount)
    return on_declare


reg.spell_rider("S-016", on_declare=_defense_self_bonus(1000))
reg.spell_rider("S-017", on_declare=_attack_self_bonus(2000))


# ---- S-019 ウルク:攻擊獲勝時,[待命] 本回合下一次攻擊不可被防禦(無魔本傷害)
def _s019_on_win(game, batch, player):
    schedule_standby(game, batch, kind="attack_undefendable", source="S-019", owner=player)


reg.spell_rider("S-019", on_win=_s019_on_win, no_book_damage=True)


# ---- S-020 ポルク:攻擊獲勝時對手 MP-3(無魔本傷害)
def _s020_on_win(game, batch, player):
    from .primitives import reduce_mp
    reduce_mp(game, batch, 1 - player, 3, "S-020")


reg.spell_rider("S-020", on_win=_s020_on_win, no_book_damage=True)


# ---- 硬幣無效攻擊:S-021 コポルク(2枚,至少1正)/ S-025 逃げるぞ!(1枚)
def _coin_negate(number, count, need_heads=1):
    def on_declare(game, batch, player, side):
        if side != "defense":
            return
        flip_coins(game, batch, player, count, number, "coin_negate_resolve",
                   {"player": player, "source": number, "need": need_heads})
    return on_declare


@reg.choice_resolver("coin_negate_resolve")
def coin_negate_resolve(game, batch, results, data):
    b = game.state.battle
    if b is None:
        return
    if sum(results) >= data["need"]:
        b.attack_negated = True
        game.emit(batch, "attack_negated", source=data["source"], player=data["player"])


reg.spell_rider("S-021", on_declare=_coin_negate("S-021", 2))
reg.spell_rider("S-025", on_declare=_coin_negate("S-025", 1))


# ---- S-026 ＳＥＴ!(非戰鬥術):擲硬幣,正面→[待命] 本回合下一場戰鬥對手不能防禦
@reg.spell_nonbattle("S-026")
def s026(game, batch, player):
    flip_coins(game, batch, player, 1, "S-026", "s026_resolve", {"player": player})


@reg.choice_resolver("s026_resolve")
def s026_resolve(game, batch, results, data):
    if results[0]:
        schedule_standby(game, batch, kind="attack_undefendable", source="S-026",
                         owner=data["player"])


# ---- S-027 耐えてくれよ!:擲2硬幣,至少1正→對手攻擊傷害 -1
def _s027_on_declare(game, batch, player, side):
    if side != "defense":
        return
    flip_coins(game, batch, player, 2, "S-027", "s027_resolve", {"player": player})


@reg.choice_resolver("s027_resolve")
def s027_resolve(game, batch, results, data):
    b = game.state.battle
    if b is None:
        return
    if sum(results) >= 1:
        b.data["defense_damage_delta"] = b.data.get("defense_damage_delta", 0) - 1
        game.emit(batch, "effect_applied", source="S-027", amount=-1)


reg.spell_rider("S-027", on_declare=_s027_on_declare)

# ---- S-022 セウシル / S-024 マ・セシルド / S-028 伏せろ!:
#      防禦獲勝時將攻擊無效 = 防方獲勝本就使攻方效果不解決,無需額外處理(純資料驅動)


# ======================================================================
# Level 2 術卡(S-029~S-058)。純香草(攻/防獲勝→魔本傷害)不需 handler:
# S-029 S-044 S-047 S-049 S-050 S-051 S-052 S-053 S-054 S-055。
# ======================================================================

# ---- S-030 ラシルド:【反擊】防禦方獲勝時對對手魔本造成傷害(傷害 1)
reg.spell_rider("S-030", counter=True)


# ---- S-031 バオウ・ザケルガ:因此術負傷的魔物直接入墓
def _s031_on_declare(game, batch, player, side):
    if side == "attack" and game.state.battle is not None:
        game.state.battle.data["injure_to_discard"] = True


reg.spell_rider("S-031", on_declare=_s031_on_declare)


# ---- S-032 レイス / S-034 ギガノ・レイス:傷害上限
reg.spell_rider("S-032", damage_cap=3)
reg.spell_rider("S-034", damage_cap=4)


# ---- S-033 グラビレイ:造成傷害/負傷時,對手場上所有魔物 -2000(至對手下個結束階段)
def _s033_on_damage(game, batch, player):
    opp = 1 - player
    for s in game.state.players[opp].slots:
        add_modifier(game, batch, kind="power", source="S-033", owner=player,
                     duration=DUR_UNTIL_END_NEXT_TURN, target_player=opp,
                     target_slot=s.uid, amount=-2000)


reg.spell_rider("S-033", on_damage=_s033_on_damage)


# ---- S-035 イオン・グラビレイ:擲2硬幣,2正→對手不能犧牲/庇護魔本
def _s035_on_declare(game, batch, player, side):
    if side != "attack":
        return
    flip_coins(game, batch, player, 2, "S-035", "s035_resolve", {"player": player})


@reg.choice_resolver("s035_resolve")
def s035_resolve(game, batch, results, data):
    b = game.state.battle
    if b is not None and sum(results) >= 2:
        b.data["no_protect_book"] = True
        game.emit(batch, "effect_applied", source="S-035")


reg.spell_rider("S-035", on_declare=_s035_on_declare)


# ---- S-036 ディオガ・グラビドン:獲勝時對防方魔本與場上所有魔物造成傷害
def _s036_on_win(game, batch, player):
    from ..engine import _attack_damage_amount, _start_damage
    opp = 1 - player
    battle = game.state.battle
    amount = _attack_damage_amount(game, battle)
    items = []
    if amount > 0:
        items.append({"kind": "book", "player": opp, "amount": amount})
    items += [{"kind": "slot", "player": opp, "slot_uid": s.uid, "amount": 1}
              for s in list(game.state.players[opp].slots)]
    _start_damage(game, batch, items,
                  {"cause": "battle_attack", "source": battle.attack_spell,
                   "source_player": player, "amount": amount})


reg.spell_rider("S-036", on_win=_s036_on_win, on_win_owns_damage=True)


# ---- 自身免疫(至對手下個結束階段):S-037(擲幣)/ S-038(必定)/ S-041(擲幣)
def _grant_full_immune(game, batch, player, source):
    add_modifier(game, batch, kind="full_immune", source=source, owner=player,
                 duration=DUR_UNTIL_END_NEXT_TURN, target_player=player)


def _s037_on_damage(game, batch, player):
    flip_coins(game, batch, player, 1, "S-037", "s037_resolve", {"player": player})


@reg.choice_resolver("s037_resolve")
def s037_resolve(game, batch, results, data):
    if results[0]:
        _grant_full_immune(game, batch, data["player"], "S-037")


reg.spell_rider("S-037", on_damage=_s037_on_damage)


def _s038_on_damage(game, batch, player):
    _grant_full_immune(game, batch, player, "S-038")


reg.spell_rider("S-038", on_damage=_s038_on_damage)


# ---- S-039 ラドム:造成傷害/負傷時,棄掉對手 1 張夥伴卡
def _s039_on_damage(game, batch, player):
    opp = game.state.players[1 - player]
    options = [{"value": x.uid, "card": x.partner} for x in opp.slots if x.partner]
    if not options:
        return
    choose_or_auto(game, batch, kind="s039_pick", player=player, options=options,
                   data={"player": player}, source="S-039")


@reg.choice_resolver("s039_pick")
def s039_pick(game, batch, value, data):
    from ..engine import IllegalCommand
    player = data["player"]
    slot = game.state.slot_by_uid(1 - player, value if isinstance(value, int) else -1)
    if slot is None or not slot.partner:
        raise IllegalCommand("choose.invalid", "須選擇對手場上的夥伴卡")
    discard_partner(game, batch, 1 - player, slot, "S-039")


reg.spell_rider("S-039", on_damage=_s039_on_damage)


# ---- S-040 バルジュロン:擲3硬幣,術魔力 = 正面數 ×2000(香草傷害 1)
def _s040_on_declare(game, batch, player, side):
    if side != "attack":
        return
    flip_coins(game, batch, player, 3, "S-040", "s040_resolve", {"player": player})


@reg.choice_resolver("s040_resolve")
def s040_resolve(game, batch, results, data):
    b = game.state.battle
    if b is not None:
        b.data["attack_spell_bonus"] = b.data.get("attack_spell_bonus", 0) + sum(results) * 2000
        game.emit(batch, "effect_applied", source="S-040", amount=sum(results) * 2000)


reg.spell_rider("S-040", on_declare=_s040_on_declare)


# ---- S-041 ジュルク(非戰鬥術):擲幣正→自身免疫(至對手下個結束階段)
@reg.spell_nonbattle("S-041")
def s041(game, batch, player):
    flip_coins(game, batch, player, 1, "S-041", "s041_resolve", {"player": player})


@reg.choice_resolver("s041_resolve")
def s041_resolve(game, batch, results, data):
    if results[0]:
        _grant_full_immune(game, batch, data["player"], "S-041")


# ---- S-043 レイ・ブルク(非戰鬥術):羅布諾斯雙向轉換
@reg.spell_nonbattle("S-043")
def s043(game, batch, player):
    ps = game.state.players[player]
    doubles = [s for s in ps.slots if s.top == "M-024"]
    completes = [s for s in ps.slots if s.top == "M-025"]
    options = []
    if len(doubles) >= 2:
        options.append({"value": "fuse", "label": "s043_fuse"})
    if completes:
        options.append({"value": "split", "label": "s043_split"})
    if not options:
        return
    if len(options) == 1:
        s043_resolve(game, batch, options[0]["value"], {"player": player})
        return
    from ..state import PendingChoice
    game.state.pending = PendingChoice(kind="s043_choice", player=player,
                                       source="S-043", options=options, data={"player": player})
    game.emit(batch, "choice_required", kind="s043_choice", player=player, options=options)


@reg.choice_resolver("s043_choice")
def s043_resolve(game, batch, value, data):
    from ..engine import IllegalCommand, _discard_slot
    player = data["player"]
    game.state.pending = None
    ps = game.state.players[player]
    if value == "fuse":
        doubles = [s for s in ps.slots if s.top == "M-024"]
        if len(doubles) < 2:
            raise IllegalCommand("choose.invalid", "場上羅布諾斯(二體)不足 2 隻")
        for s in doubles[:2]:
            _discard_slot(game, batch, player, s, reason="S-043")
        pages = [o["page"] for o in _book_pages_of(game, player, "M-025")]
        if pages:
            _pick_book_page(game, batch, player, "M-025", "s043_place_complete")
    elif value == "split":
        completes = [s for s in ps.slots if s.top == "M-025"]
        if not completes:
            raise IllegalCommand("choose.invalid", "場上沒有羅布諾斯(完全體)")
        _discard_slot(game, batch, player, completes[0], reason="S-043")
        # 放至多 2 隻二體(自書任意頁,依序)
        _place_up_to_two_doubles(game, batch, player)
    else:
        raise IllegalCommand("choose.invalid", "無效的選擇")


def _book_pages_of(game, player, number):
    ps = game.state.players[player]
    return [{"value": p, "card": ps.card_at(p), "page": p}
            for p in range(1, 33)
            if p not in ps.consumed_pages and ps.card_at(p) == number]


def _pick_book_page(game, batch, player, number, resolver_key):
    options = _book_pages_of(game, player, number)
    if not options:
        return
    if len(options) == 1:
        reg.CHOICE_RESOLVERS[resolver_key](game, batch, options[0]["value"], {"player": player})
        return
    from ..state import PendingChoice
    game.state.pending = PendingChoice(kind=resolver_key, player=player, source="S-043",
                                       options=options, data={"player": player})
    game.emit(batch, "choice_required", kind=resolver_key, player=player, options=options)


@reg.choice_resolver("s043_place_complete")
def s043_place_complete(game, batch, value, data):
    game.state.pending = None
    play_mamodo_from_book(game, batch, data["player"], value)


def _place_up_to_two_doubles(game, batch, player):
    for _ in range(2):
        pages = _book_pages_of(game, player, "M-024")
        if not pages:
            break
        # 自動取第一個可用頁(同名雙隻上限 2 由 play_mamodo_from_book 把關)
        if play_mamodo_from_book(game, batch, player, pages[0]["value"]) is None:
            break


# ---- S-048 ゼベル(非戰鬥術):自書任意頁取 M-027 疊放到場上巴爾特羅
@reg.spell_nonbattle("S-048")
def s048(game, batch, player):
    ps = game.state.players[player]
    base = next((s for s in ps.slots if s.top == "M-028"), None)
    pages = _book_pages_of(game, player, "M-027")
    if base is None or not pages:
        return
    _pick_book_page(game, batch, player, "M-027", "s048_place")


@reg.choice_resolver("s048_place")
def s048_place(game, batch, value, data):
    from ..state import MamodoSlot  # noqa: F401
    player = data["player"]
    game.state.pending = None
    ps = game.state.players[player]
    base = next((s for s in ps.slots if s.top == "M-028"), None)
    if base is None:
        return
    number = take_from_book(game, batch, player, value)
    base.stack.append(number)
    base.injured = False
    game.emit(batch, "card_played", player=player, card=number, slot=base.uid,
              zone="mamodo", stacked=True, from_book=True)


# ---- S-056 しっかりしろ!:防禦獲勝→無效攻擊(自動);被造成傷害→ MP = 2×傷害
def _s056_on_defense_damaged(game, batch, defender, amount):
    from ..engine import gain_mp
    gain_mp(game, batch, defender, 2 * amount, "S-056")


reg.spell_rider("S-056", on_defense_damaged=_s056_on_defense_damaged)


# ---- S-057 チェックメイト!(非戰鬥術):擲幣正→[待命] 本回合下一場戰鬥獲勝改為負傷代替傷害
@reg.spell_nonbattle("S-057")
def s057(game, batch, player):
    flip_coins(game, batch, player, 1, "S-057", "s057_resolve", {"player": player})


@reg.choice_resolver("s057_resolve")
def s057_resolve(game, batch, results, data):
    if results[0]:
        schedule_standby(game, batch, kind="injure_instead", source="S-057",
                         owner=data["player"])


# ---- S-058 ザケル(ゼオン):獲勝時使對手 1 隻魔物負傷代替魔本傷害
reg.spell_rider("S-058", injure_instead=True)


# ---- S-042 ビライツ:攻擊時,自身合計魔力 8000 以上 → 此術傷害 +2
reg.spell_rider("S-042", damage_bonus=lambda game, battle: (
    2 if battle.data.get("attack_total", 0) >= 8000 else 0))


# ---- S-045 ガンズ・ガロン:擲2硬幣,2 正 → 不可被防禦
def _s045_on_declare(game, batch, player, side):
    if side != "attack":
        return
    flip_coins(game, batch, player, 2, "S-045", "s045_resolve", {"player": player})


@reg.choice_resolver("s045_resolve")
def s045_resolve(game, batch, results, data):
    if sum(results) >= 2:
        b = game.state.battle
        if b is not None:
            b.attack_undefendable = True


reg.spell_rider("S-045", on_declare=_s045_on_declare)


# ---- S-046 エイジャス・ガロン:擲1硬幣,正 → 不可被防禦
def _s046_on_declare(game, batch, player, side):
    if side != "attack":
        return
    flip_coins(game, batch, player, 1, "S-046", "s046_resolve", {"player": player})


@reg.choice_resolver("s046_resolve")
def s046_resolve(game, batch, results, data):
    if results[0]:
        b = game.state.battle
        if b is not None:
            b.attack_undefendable = True


reg.spell_rider("S-046", on_declare=_s046_on_declare)
