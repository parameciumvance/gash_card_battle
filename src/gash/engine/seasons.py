"""賽季(data/seasons.json):一張卡屬於包含其卡號的最早賽季,魔書的賽季是其中各卡賽季的最大值。"""

from __future__ import annotations

import json
from collections.abc import Iterable
from functools import lru_cache

from .cards import DATA_DIR


@lru_cache(maxsize=1)
def _definition() -> dict:
    return json.loads((DATA_DIR / "seasons.json").read_text(encoding="utf-8"))


def selectable_seasons() -> tuple[int, ...]:
    return tuple(_definition()["selectable"])


def default_season() -> int:
    return _definition()["default"]


def card_season(number: str) -> int | None:
    """卡號所屬的賽季;沒有任何賽季包含時為 None。"""
    data = _definition()
    if number in data["special"]:
        return data["special"][number]
    prefix, _, digits = number.rpartition("-")
    if not prefix or not digits.isdigit():
        return None
    value = int(digits)
    seasons = sorted(data["seasons"].items(), key=lambda kv: int(kv[0]))
    for season, limits in seasons:
        if prefix in limits and value <= limits[prefix]:
            return int(season)
    return None


def deck_season(pages: Iterable[str]) -> int | None:
    """魔書從哪個賽季起可用;含沒有賽季的卡時為 None。"""
    seasons = [card_season(n) for n in pages]
    if any(s is None for s in seasons):
        return None
    return max(seasons, default=None)
