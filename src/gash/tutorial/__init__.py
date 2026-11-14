"""教學對局(tutorial):固定局面與腳本對手。

對手腳本依當下盤面回傳候選指令(格式同 npc.decide,交給 npc.submit_ranked;被引擎拒絕時退回安全預設),
不照固定順序送出,玩家在沒有鎖定的步驟偏離劇本時也接得下去(tutorial「自由步驟的偏離」)。
"""
from __future__ import annotations

import json
import random

from ..engine.awaiting import awaited_player
from ..engine.cards import DATA_DIR
from ..engine.engine import exhausted_spell_pages
from ..engine.state import START, Game

TUTORIAL_DIR = DATA_DIR / "tutorial"
ATTACK_SPELL = "S-037"          # 對手的ジキル:攻擊與防禦都用它


def tutorial_decks() -> tuple[list[str], list[str]]:
    """(玩家, 對手)的魔書頁序。"""
    def load(name):
        with open(TUTORIAL_DIR / f"{name}.json", encoding="utf-8") as f:
            return list(json.load(f)["pages"])
    return load("player"), load("opponent")


class TailsRng(random.Random):
    """教學對局的 RNG:擲硬幣一律反面(tutorial「教學局面」);randint 只用在擲先攻,教學不擲。
    繼承 random.Random,快照預覽等複製盤面時照常取得狀態。"""

    def random(self) -> float:
        return 0.9

    def randint(self, a: int, b: int) -> int:
        return a


def _usable_spell_page(game: Game, seat: int) -> int | None:
    ps = game.state.players[seat]
    used = exhausted_spell_pages(game, seat)
    return next((p for p in ps.open_pages() if ps.card_at(p) == ATTACK_SPELL and p not in used), None)


def opponent_commands(game: Game, seat: int) -> list[dict]:
    """對手的候選指令(依偏好排序);空清單時由 submit_ranked 送安全預設。"""
    st = game.state
    if awaited_player(game) != seat or st.pending is not None:
        return []
    cmd = lambda **kw: [{**kw, "player": seat}]                                   # noqa: E731
    if st.phase == START:
        return cmd(type="flip_pages", count=1)
    page = _usable_spell_page(game, seat)
    if st.battle is not None:
        if st.battle.step == "defense" and page is not None:
            return cmd(type="declare_defense", page=page)                         # 不能防禦時被拒,退回不防禦
        return []
    if st.battle_in is not None:
        return []                                                                 # 同意進入戰鬥
    if st.turn_player == seat and page is not None:
        return cmd(type="declare_attack", page=page)
    return []
