"""魔本(deck)載入與構築合法性驗證。

構築規則(rule3.md「魔本檔案夾」):
- 32 頁全部放入卡片
- 第 1 頁為魔物卡、最後一頁為術卡
- 中級卡放在第 12 頁以後、上級卡放在第 22 頁以後
- 相同編號最多 4 張
- 魔物卡合計最多 8 張
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .cards import MAMODO, SPELL, CardDef

BOOK_SIZE = 32
INTERMEDIATE_MIN_PAGE = 12
SUPERIOR_MIN_PAGE = 22
MAX_COPIES = 4
MAX_MAMODO = 8


class DeckError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


@dataclass(frozen=True)
class Deck:
    id: str
    pages: tuple[str, ...]  # pages[i] = 第 i+1 頁的卡號


def validate_deck(pages: list[str], db: dict[str, CardDef]) -> None:
    if len(pages) != BOOK_SIZE:
        raise DeckError("deck.size", f"魔本須為 {BOOK_SIZE} 頁,實際 {len(pages)} 頁")
    for number in pages:
        if number not in db:
            raise DeckError("deck.unknown_card", f"卡號不存在: {number}")
    if db[pages[0]].type != MAMODO:
        raise DeckError("deck.first_page", f"第 1 頁須為魔物卡,實際為 {pages[0]}")
    if db[pages[-1]].type != SPELL:
        raise DeckError("deck.last_page", f"最後一頁須為術卡,實際為 {pages[-1]}")
    for i, number in enumerate(pages, start=1):
        klass = db[number].klass
        if klass == "intermediate" and i < INTERMEDIATE_MIN_PAGE:
            raise DeckError("deck.intermediate_page", f"中級卡 {number} 須在第 {INTERMEDIATE_MIN_PAGE} 頁以後(第 {i} 頁)")
        if klass == "superior" and i < SUPERIOR_MIN_PAGE:
            raise DeckError("deck.superior_page", f"上級卡 {number} 須在第 {SUPERIOR_MIN_PAGE} 頁以後(第 {i} 頁)")
    for number, count in Counter(pages).items():
        if count > MAX_COPIES:
            raise DeckError("deck.max_copies", f"同編號 {number} 超過 {MAX_COPIES} 張({count} 張)")
    mamodo_count = sum(1 for n in pages if db[n].type == MAMODO)
    if mamodo_count > MAX_MAMODO:
        raise DeckError("deck.max_mamodo", f"魔物卡超過 {MAX_MAMODO} 張({mamodo_count} 張)")


def load_deck(path: Path, db: dict[str, CardDef]) -> Deck:
    raw = json.loads(path.read_text(encoding="utf-8"))
    pages = list(raw["pages"])
    validate_deck(pages, db)
    return Deck(id=raw["id"], pages=tuple(pages))
