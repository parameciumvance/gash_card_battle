"""局面評估:對 NPC 越有利分數越高。權重集中在本檔的常數,調整時只改這裡。

只讀 NPC 看得到的資訊:對手的翻開頁(未公開)不計入對手的潛力。傳入的盤面是 determinize 後的副本。
"""

from __future__ import annotations

from ..engine.cards import SPELL
from ..engine.engine import _spell_usable_by, slot_power, spell_cost
from ..engine.state import BOOK_SIZE, GAME_OVER, Game

WIN = 1_000_000.0

# 生命:還能承受幾點魔書傷害((BOOK_SIZE - pos) / 2);低於 LIFE_LOW 時每點另扣 LIFE_LOW_PENALTY
LIFE_VALUE = 2.0
LIFE_LOW = 5
LIFE_LOW_PENALTY = 4.0
# MP:需要的部分(看得到的戰術費用)全額計,超過的部分打折;對手的需要看不到,以固定值估計
MP_VALUE = 0.6
MP_EXTRA_VALUE = 0.15
MP_MIN_NEED = 2
OPP_MP_NEED = 4
# 場面:每隻魔物、每 1000 魔力、負傷折扣、搭檔、場上沒有魔物
MAMODO_VALUE = 3.0
POWER_VALUE = 0.8
INJURED_FACTOR = 0.5
PARTNER_VALUE = 1.5
NO_MAMODO_PENALTY = 10.0
# 潛力:目前翻開頁上用得起的攻擊戰術,每點傷害
THREAT_VALUE = 1.0


def evaluate(game: Game, npc: int) -> float:
    st = game.state
    if st.phase == GAME_OVER:
        return WIN if st.winner == npc else -WIN
    opp = 1 - npc
    mine = _life(game, npc) + _mp(game, npc, _mp_need(game, npc)) + _board(game, npc) + _threat(game, npc)
    theirs = _life(game, opp) + _mp(game, opp, OPP_MP_NEED) + _board(game, opp)
    return mine - theirs


def _life(game: Game, player: int) -> float:
    life = max(0.0, (BOOK_SIZE - game.state.players[player].pos) / 2)
    return LIFE_VALUE * life - LIFE_LOW_PENALTY * max(0.0, LIFE_LOW - life)


def _mp(game: Game, player: int, need: int) -> float:
    mp = game.state.players[player].mp
    return MP_VALUE * min(mp, need) + MP_EXTRA_VALUE * max(0, mp - need)


def _mp_need(game: Game, player: int) -> int:
    """目前與下一個對頁上戰術卡的最高費用(自己的魔書 NPC 看得到)。"""
    ps = game.state.players[player]
    need = MP_MIN_NEED
    for page in range(ps.pos, min(ps.pos + 4, BOOK_SIZE + 1)):
        if page in ps.consumed_pages:
            continue
        card = game.db[ps.card_at(page)]
        if card.type == SPELL:
            cost = spell_cost(game, player, page, card) if page in ps.open_pages() else (card.cost or 0)
            need = max(need, cost)
    return need


def _board(game: Game, player: int) -> float:
    slots = game.state.players[player].slots
    if not slots:
        return -NO_MAMODO_PENALTY
    total = 0.0
    for slot in slots:
        value = MAMODO_VALUE + POWER_VALUE * slot_power(game, player, slot) / 1000
        if slot.injured:
            value *= INJURED_FACTOR
        if slot.partner:
            value += PARTNER_VALUE
        total += value
    return total


def _threat(game: Game, player: int) -> float:
    """目前翻開頁上、有魔物能用且付得起的攻擊戰術的最大傷害。"""
    ps = game.state.players[player]
    best = 0
    for page in ps.open_pages():
        card = game.db[ps.card_at(page)]
        if not card.can_attack() or not card.damage:
            continue
        if not any(card.is_command_spell or _spell_usable_by(game, player, s, card) for s in ps.slots):
            continue
        if spell_cost(game, player, page, card) <= ps.mp:
            best = max(best, card.damage)
    return THREAT_VALUE * best
