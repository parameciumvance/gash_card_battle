"""魔書(deck)載入與構築合法性驗證。

構築規則(rule3.md「魔書檔案夾」):
- 32 頁全部放入卡片
- 第 1 頁為魔物卡、最後一頁為戰術卡
- 中級卡放在第 12 頁以後、上級卡放在第 22 頁以後
- 相同編號最多 4 張
- 魔物卡合計最多 8 張
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .cards import MAMODO, SPELL, CardDef, pending_cards
from .seasons import card_season

BOOK_SIZE = 32
INTERMEDIATE_MIN_PAGE = 12
SUPERIOR_MIN_PAGE = 22
MAX_COPIES = 4
MAX_PR_COPIES = 1
MAX_MAMODO = 8


class DeckError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


@dataclass(frozen=True)
class Deck:
    id: str
    pages: tuple[str, ...]  # pages[i] = 第 i+1 頁的卡號


def validate_deck(pages: list[str], db: dict[str, CardDef], season: int | None = None) -> None:
    """season 有指定時,另外拒絕不屬於該賽季可用範圍的卡(deck.season)。"""
    if len(pages) != BOOK_SIZE:
        raise DeckError("deck.size", f"魔書須為 {BOOK_SIZE} 頁,實際 {len(pages)} 頁")
    for number in pages:
        if number not in db:
            raise DeckError("deck.unknown_card", f"卡號不存在: {number}")
    pending = sorted(set(pages) & pending_cards())
    if pending:
        raise DeckError("deck.card_pending", f"尚未開放的卡: {', '.join(pending)}")
    if season is not None:
        beyond = sorted({n for n in pages if (card_season(n) or season + 1) > season})
        if beyond:
            raise DeckError("deck.season", f"第 {season} 賽季不能使用: {', '.join(beyond)}")
    if db[pages[0]].type != MAMODO:
        raise DeckError("deck.first_page", f"第 1 頁須為魔物卡,實際為 {pages[0]}")
    if db[pages[-1]].type != SPELL:
        raise DeckError("deck.last_page", f"最後一頁須為戰術卡,實際為 {pages[-1]}")
    for i, number in enumerate(pages, start=1):
        klass = db[number].klass
        if klass == "intermediate" and i < INTERMEDIATE_MIN_PAGE:
            raise DeckError("deck.intermediate_page", f"中級卡 {number} 須在第 {INTERMEDIATE_MIN_PAGE} 頁以後(第 {i} 頁)")
        if klass == "superior" and i < SUPERIOR_MIN_PAGE:
            raise DeckError("deck.superior_page", f"上級卡 {number} 須在第 {SUPERIOR_MIN_PAGE} 頁以後(第 {i} 頁)")
    for number, count in Counter(pages).items():
        if count > MAX_COPIES:
            raise DeckError("deck.max_copies", f"同編號 {number} 超過 {MAX_COPIES} 張({count} 張)")
        if number.startswith("PR-") and count > MAX_PR_COPIES:   # 大會規則:プロモーションカードは1種類につき1枚まで
            raise DeckError("deck.pr_copies", f"PR 卡 {number} 只能放 {MAX_PR_COPIES} 張({count} 張)")
    mamodo_count = sum(1 for n in pages if db[n].type == MAMODO)
    if mamodo_count > MAX_MAMODO:
        raise DeckError("deck.max_mamodo", f"魔物卡超過 {MAX_MAMODO} 張({mamodo_count} 張)")


def load_deck(path: Path, db: dict[str, CardDef]) -> Deck:
    raw = json.loads(path.read_text(encoding="utf-8"))
    pages = list(raw["pages"])
    validate_deck(pages, db)
    return Deck(id=raw["id"], pages=tuple(pages))


def deck_warnings(pages: list[str | None], db: dict[str, CardDef] | None = None) -> list[dict]:
    """魔書組合的提醒(deck-builder「魔書組合的提醒」):不是構築規則,只指出一定不能運作的卡。
    - spell_no_user:魔書中沒有任何魔物能使用的戰術(指令戰術除外)。
    - partner_no_mamodo:魔書中沒有對應魔物的搭檔。
    「能使用」沿用引擎的 _spell_usable_by:把魔書中每張魔物卡放成假設的場上魔物判斷(家族、戰術相容規則
    都只依卡片資料);對局中由搭檔效果產生的屬性相容(P-029 AllowAttrSpellsThisTurn)另外掃描效果樹。
    空頁略過;頁碼從 1 起。"""
    from .cards import PARTNER, card_db
    from .effects import tree as T
    from .effects.primitives import family
    from .engine import _spell_usable_by, new_game
    from .state import MamodoSlot

    db = db or card_db()
    cards = [(i, n) for i, n in enumerate(pages, 1) if n]
    # 判斷用的對局環境:只借用引擎的函式,場上換成假設的魔物、清掉修正
    game = new_game(["M-001"] + ["S-001"] * (BOOK_SIZE - 1), seed=0, db=db)
    game.state.modifiers = []
    slots = [MamodoSlot(uid=1000 + i, stack=[n]) for i, n in cards if db[n].type == MAMODO]
    families = {family(game, s) for s in slots}
    # 魔書中的卡讓某家族使用某屬性的戰術(P-029):(家族, 屬性)
    granted = set()
    numbers = {n for _, n in cards}
    for key, root in T.EFFECTS.items():
        if key.split(":", 1)[0] in numbers:
            for node in _tree_nodes(root):
                if isinstance(node, T.AllowAttrSpellsThisTurn):
                    granted.add((node.mamodo, node.attr))

    def usable(card: CardDef) -> bool:
        for slot in slots:
            game.state.players[0].slots = [slot]
            if _spell_usable_by(game, 0, slot, card):
                return True
        return any(fam in families and card.attr_name == attr for fam, attr in granted)

    warnings = []
    for page, number in cards:
        card = db[number]
        if card.type == SPELL and not card.is_command_spell and not usable(card):
            warnings.append({"kind": "spell_no_user", "page": page, "card": number})
        elif card.type == PARTNER and card.related_mamodo not in families:
            warnings.append({"kind": "partner_no_mamodo", "page": page, "card": number})
    return warnings


def _tree_nodes(node):
    """效果樹的所有節點(依 dataclass 欄位遞迴,含 Sequence / When 的子節點)。"""
    from dataclasses import fields, is_dataclass
    from .effects import tree as T
    if isinstance(node, (list, tuple)):
        for item in node:
            yield from _tree_nodes(item)
        return
    if not isinstance(node, T.Effect):
        return
    yield node
    if is_dataclass(node):
        for f in fields(node):
            yield from _tree_nodes(getattr(node, f.name))
