"""候選指令列舉:依決策點列出可能的指令(含參數),合法與否由引擎在副本上試送判斷。"""

from __future__ import annotations

from ..engine.cards import EVENT, MAMODO, PARTNER, SPELL
from ..engine.effects import registry as reg
from ..engine.engine import _spell_any_page_standby, _spell_usable_by
from ..engine.state import BOOK_SIZE, GAME_OVER, START, STEP_DEFENSE, Game


def choice_value(options: list[dict], i: int):
    """pending 第 i 個選項的指令值(與逾時代打的取值方式相同;damage_order 以索引選)。"""
    opt = options[i]
    if "index" in opt:
        return opt["index"]
    return opt.get("value", opt.get("page"))


def candidates(game: Game, player: int) -> list[dict]:
    """player 在目前決策點的候選指令(未過濾合法性),順序固定以利重現。"""
    st = game.state
    if st.phase == GAME_OVER:
        return []
    if st.pending is not None:
        if st.pending.player != player:
            return []
        opts = st.pending.options
        return [{"type": "choose", "value": choice_value(opts, i)} for i in range(len(opts))]
    if st.phase == START:
        return [{"type": "flip_pages", "count": n} for n in range(4)]
    if st.battle is not None:
        if st.battle.step == STEP_DEFENSE:
            return [{"type": "no_defense"}] + _spell_declarations(game, player, "declare_defense")
        return [{"type": "pass"}] + _field_abilities(game, player)
    if st.battle_in is not None:
        return [{"type": "battle_in_response", "allow": True}] + _actions(game, player)
    return ([{"type": "pass"}] + _actions(game, player)
            + _spell_declarations(game, player, "declare_attack") + _mamodo_attacks(game, player))


def _actions(game: Game, player: int) -> list[dict]:
    """非戰鬥中的一般行動:放卡、使用魔本中的卡、場上卡的啟動效果。"""
    ps = game.state.players[player]
    out = []
    for page in ps.open_pages():
        card = game.db[ps.card_at(page)]
        if card.type in (MAMODO, PARTNER):
            out.append({"type": "play_card", "page": page})
        elif card.type == EVENT or (card.type == SPELL and card.effect_icon == "nonbattle"):
            out.append({"type": "use_book_card", "page": page})
    return out + _field_abilities(game, player)


def _field_abilities(game: Game, player: int) -> list[dict]:
    st = game.state
    out = []
    for slot in st.players[player].slots:
        if slot.top in reg.ACTIVATED:
            out.append({"type": "use_field_ability", "zone": "mamodo", "slot_uid": slot.uid})
        if slot.partner in reg.ACTIVATED:
            out.append({"type": "use_field_ability", "zone": "partner", "slot_uid": slot.uid})
    # E-010:使用本回合借用的對手搭檔卡效果(以卡號記錄,該搭檔離場也可用)
    if any(m.kind == "borrow_partner" and m.owner == player and not m.data.get("used")
           for m in st.modifiers):
        out.append({"type": "use_borrowed_effect"})
    return out


def _spell_declarations(game: Game, player: int, ctype: str) -> list[dict]:
    """攻擊 / 防禦術宣告:目前翻開頁與待命允許的任意頁,每隻能使用該術的魔物各一個候選。"""
    ps = game.state.players[player]
    pages = list(ps.open_pages())
    pages += [p for p in range(1, BOOK_SIZE + 1)
              if p not in pages and _spell_any_page_standby(game, player, p)]
    out = []
    for page in pages:
        card = game.db[ps.card_at(page)]
        if card.type != SPELL:
            continue
        if ctype == "declare_attack" and not card.can_attack():
            continue
        if ctype == "declare_defense" and not card.can_defend():
            continue
        for slot in ps.slots:
            if card.is_command_spell or _spell_usable_by(game, player, slot, card):
                out.append({"type": ctype, "page": page, "slot_uid": slot.uid})
    return out


def _mamodo_attacks(game: Game, player: int) -> list[dict]:
    return [{"type": "declare_attack", "mode": "mamodo", "slot_uid": slot.uid}
            for slot in game.state.players[player].slots if slot.top in reg.MAMODO_ATTACK]
