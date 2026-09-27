"""術卡附加效果(非香草)。香草術卡(攻/防獲勝→魔本傷害)由卡片資料直接驅動。

宣告時效果(硬幣)依規則於宣告時擲出並確定。
"""

from __future__ import annotations

from . import registry as reg
from .primitives import play_mamodo_from_book, take_from_book

# S-022 セウシル / S-024 マ・セシルド / S-028 伏せろ!:防禦獲勝時將攻擊無效 = 防方獲勝本就使攻方
# 效果不解決,無需額外處理(純資料驅動)。Level 2 純香草術卡(攻/防獲勝→魔本傷害)同樣不需註冊:
# S-029 S-044 S-047 S-049 S-050 S-051 S-052 S-053 S-054 S-055。
# 其餘已遷移的術卡見 tree_cards.py;本檔只剩尚未遷移的 S-043 / S-048(待「書內選頁」節點)。


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


