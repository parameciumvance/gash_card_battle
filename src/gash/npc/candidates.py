"""候選指令列舉:依決策點列出可能的指令(含參數),合法與否由引擎在副本上試送判斷。"""

from __future__ import annotations

from ..engine.cards import EVENT, MAMODO, MJ12, PARTNER, SPELL
from ..engine.effects import registry as reg
from ..engine.effects.primitives import family
from ..engine.engine import _spell_any_page_standby, _spell_usable_by, mamodo_attack_spec, mamodo_defense_spec
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
            return ([{"type": "no_defense"}] + _spell_declarations(game, player, "declare_defense")
                    + _mamodo_defenses(game, player))
        return [{"type": "pass"}] + _field_abilities(game, player) + _battle_events(game, player)
    if st.battle_in is not None:
        return [{"type": "battle_in_response", "allow": True}] + _actions(game, player)
    return ([{"type": "pass"}] + _actions(game, player)
            + _spell_declarations(game, player, "declare_attack") + _mamodo_attacks(game, player))


def _actions(game: Game, player: int) -> list[dict]:
    """非戰鬥中的一般行動:放卡、使用魔書中的卡、場上卡的啟動效果。"""
    ps = game.state.players[player]
    out = []
    for page in ps.open_pages():
        card = game.db[ps.card_at(page)]
        if card.type in (MAMODO, MJ12):
            out.append({"type": "play_card", "page": page})
        elif card.type == PARTNER:   # 對應的魔物各一個(兩隻對應魔物時由 NPC 選擇裝備對象)
            out += [{"type": "play_card", "page": page, "slot_uid": s.uid} for s in ps.slots
                    if family(game, s) == card.related_mamodo and s.partner is None]
        elif card.type == EVENT or (card.type == SPELL and card.effect_icon == "nonbattle"):
            out.append({"type": "use_book_card", "page": page})
    # 待命允許從任意頁使用的非戰鬥戰術(P-025)
    for page in range(1, BOOK_SIZE + 1):
        card = game.db[ps.card_at(page)]
        if (page not in ps.open_pages() and card.type == SPELL and card.effect_icon == "nonbattle"
                and _spell_any_page_standby(game, player, page)):
            out.append({"type": "use_book_card", "page": page})
    # 「1アクションを使って…捨て札にできる」(M-046 / P-020)
    for slot in ps.slots:
        if len(slot.stack) > 1 and reg.ACTION_DISCARD.get(slot.top) == "top":
            out.append({"type": "use_action_effect", "zone": "mamodo", "slot_uid": slot.uid})
        if reg.ACTION_DISCARD.get(slot.partner) == "partner":
            out.append({"type": "use_action_effect", "zone": "partner", "slot_uid": slot.uid})
    return out + _field_abilities(game, player)


def _battle_events(game: Game, player: int) -> list[dict]:
    """戰鬥中的「効果の使用」:今のページ上有戰鬥圖示的事件卡(E-053)。"""
    ps = game.state.players[player]
    return [{"type": "use_book_card", "page": page} for page in ps.open_pages()
            if game.db[ps.card_at(page)].type == EVENT and game.db[ps.card_at(page)].effect_icon == "battle"]


def _field_abilities(game: Game, player: int) -> list[dict]:
    st = game.state
    out = []
    for slot in st.players[player].slots:
        if slot.top in reg.ACTIVATED:
            out.append({"type": "use_field_ability", "zone": "mamodo", "slot_uid": slot.uid})
        if slot.partner in reg.ACTIVATED:
            out.append({"type": "use_field_ability", "zone": "partner", "slot_uid": slot.uid})
    for fc in st.players[player].field_cards:   # 獨立卡區(MJ12)
        if fc.card in reg.ACTIVATED:
            out.append({"type": "use_field_ability", "zone": "field", "field_uid": fc.uid})
    # E-010:使用本回合借用的對手搭檔卡效果(以卡號記錄,該搭檔離場也可用)
    if any(m.kind == "borrow_partner" and m.owner == player and not m.data.get("used")
           for m in st.modifiers):
        out.append({"type": "use_borrowed_effect"})
    return out


def _spell_declarations(game: Game, player: int, ctype: str) -> list[dict]:
    """攻擊 / 防禦戰術宣告:目前翻開頁與待命允許的任意頁,每隻能使用該戰術的魔物各一個候選。"""
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


def _mamodo_defenses(game: Game, player: int) -> list[dict]:
    return [{"type": "declare_defense", "mode": "mamodo", "slot_uid": slot.uid}
            for slot in game.state.players[player].slots if mamodo_defense_spec(game, player, slot)]


def _mamodo_attacks(game: Game, player: int) -> list[dict]:
    return [{"type": "declare_attack", "mode": "mamodo", "slot_uid": slot.uid}
            for slot in game.state.players[player].slots if mamodo_attack_spec(game, player, slot)]


def other_actions_available(game: Game, player: int) -> bool:
    """player 在目前決策點除了預設回應(default_command:pass / 進入戰鬥 / 不防禦)之外,
    是否還有其他合法的行動(battle-api「非回合玩家可用行動的快照」)。在副本上逐一試送判斷。"""
    from ..engine.awaiting import default_command
    from .settle import clone, try_submit
    default = default_command(game)
    return any(cmd != default and try_submit(clone(game), player, cmd) for cmd in candidates(game, player))
