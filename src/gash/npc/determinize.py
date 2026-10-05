"""隱藏資訊替換:NPC 取得盤面副本的唯一入口。

NPC 看得到的:自己的一切、對手已離開魔本的頁、宣告中的術頁、事件記錄中公開或只給 NPC 看的頁
(`book_card_used`、`book_revealed` / `pages_peeked` 的 viewer 為 NPC)。其餘對手魔本頁以抽樣替換,
對局 RNG 換成 NPC 的隨機來源產生的新 RNG(不預知擲幣),事件記錄不帶進副本。
"""

from __future__ import annotations

import copy
import random

from ..engine.state import BOOK_SIZE, Game, GameState

# 抽樣先驗:與對手場上魔物同家族的卡(其術、搭檔)較可能在對手魔本中
FAMILY_WEIGHT = 6.0
SEEN_WEIGHT = 3.0      # 對手用過的卡(同卡可重複放入魔本)
BASE_WEIGHT = 1.0


def in_use_pages(game: Game, player: int) -> set[int]:
    """player 已宣告的攻防術頁:宣告即公開(同 views 的使用中頁)。"""
    st = game.state
    pages: set[int] = set()
    if st.battle_in is not None and st.battle_in.get("attacker") == player:
        page = st.battle_in.get("page")
        if page is not None:
            pages.add(page)
    if st.battle is not None:
        b = st.battle
        if b.attacker == player and b.attack_page is not None:
            pages.add(b.attack_page)
        if b.defender == player and b.defense_page is not None:
            pages.add(b.defense_page)
    return pages


def known_opponent_pages(game: Game, npc: int) -> dict[int, str]:
    """NPC 知道內容的對手魔本頁(頁碼 → 卡號),不含已離開魔本的頁。"""
    opp = 1 - npc
    known: dict[int, str] = {}
    for ev in game.events:
        kind = ev["type"]
        if kind in ("book_revealed", "pages_peeked"):
            if ev.get("viewer") == npc and ev.get("player") == opp:
                for c in ev.get("cards", ()):
                    known[c["page"]] = c["card"]
        elif kind == "book_card_used" and ev.get("player") == opp:
            known[ev["page"]] = ev["card"]
    ps = game.state.players[opp]
    for page in in_use_pages(game, opp):
        known[page] = ps.card_at(page)
    return {p: c for p, c in known.items() if p not in ps.consumed_pages}


class Determinizer:
    """為一個決策點產生多份「NPC 視角一致」的副本;先驗與已知頁只計算一次。"""

    def __init__(self, game: Game, npc: int):
        self.game = game
        self.npc = npc
        opp = 1 - npc
        ps = game.state.players[opp]
        self.known = known_opponent_pages(game, npc)
        self.hidden = [p for p in range(1, BOOK_SIZE + 1)
                       if p not in ps.consumed_pages and p not in self.known]
        families = {game.db[s.top].related_mamodo for s in ps.slots}
        seen = (set(self.known.values()) | set(ps.discard)
                | {n for s in ps.slots for n in s.stack} | {s.partner for s in ps.slots if s.partner})
        self.population = sorted(game.db)
        self.weights = [
            FAMILY_WEIGHT if game.db[n].related_mamodo in families
            else SEEN_WEIGHT if n in seen else BASE_WEIGHT
            for n in self.population]

    def sample(self, rng: random.Random) -> tuple[dict[int, str], int]:
        """抽一組對手隱藏頁的內容與副本 RNG 的 seed。"""
        cards = rng.choices(self.population, weights=self.weights, k=len(self.hidden))
        book = dict(self.known)
        book.update(zip(self.hidden, cards))
        return book, rng.getrandbits(64)

    def build(self, sample: tuple[dict[int, str], int]) -> Game:
        book, seed = sample
        opp = 1 - self.npc
        st = copy.deepcopy(self.game.state)
        _apply(st, opp, book)
        jammer = None
        if self.game.jammer is not None:
            jammer = dict(self.game.jammer)
            snap = copy.deepcopy(jammer["snapshot"])
            _apply(snap, opp, book)
            jammer["snapshot"] = snap
        return Game(state=st, rng=random.Random(seed), db=self.game.db, jammer=jammer)


def _apply(st: GameState, opp: int, book: dict[int, str]) -> None:
    pages = st.players[opp].book
    for page, card in book.items():
        pages[page - 1] = card
