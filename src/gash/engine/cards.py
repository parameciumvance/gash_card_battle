"""卡片定義與載入。cards.json 由 tools/extract_cards.py 產出。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from ..paths import data_dir

DATA_DIR = data_dir()

# 卡片類型
MAMODO = "mamodo"
PARTNER = "partner"
SPELL = "spell"
EVENT = "event"

# 指示卡(對所有魔物的命令)在 xlsx 中的 related_mamodo 標記
COMMAND_ALL = "Command: All"


@dataclass(frozen=True)
class CardDef:
    number: str
    type: str
    name_en: str
    related_mamodo: str | None
    cost: int | None
    ad: str | None          # "A" / "D" / "AD" / None
    klass: str              # "none" / "intermediate" / "superior"
    attr_name: str | None   # 屬性或《效果名》
    effect_en: str
    power_base: int | None      # 魔物本體魔力
    power_bonus: int | None     # 術的魔力加值
    power_special: bool         # 術魔力為 Special(不參與合計)
    damage: int | None
    image_url: str | None

    @property
    def is_command_spell(self) -> bool:
        return self.type == SPELL and self.related_mamodo == COMMAND_ALL

    def can_attack(self) -> bool:
        return self.type == SPELL and self.ad in ("A", "AD")

    def can_defend(self) -> bool:
        return self.type == SPELL and self.ad in ("D", "AD")


def _to_def(raw: dict) -> CardDef:
    power = raw.get("power") or {}
    return CardDef(
        number=raw["number"],
        type=raw["type"],
        name_en=raw["name_en"],
        related_mamodo=raw.get("related_mamodo"),
        cost=raw.get("cost"),
        ad=raw.get("ad"),
        klass=raw.get("class", "none"),
        attr_name=raw.get("attr_name"),
        effect_en=raw.get("effect_en", ""),
        power_base=power.get("base"),
        power_bonus=power.get("bonus"),
        power_special=bool(power.get("special")),
        damage=raw.get("damage"),
        image_url=raw.get("image_url"),
    )


def load_cards(path: Path | None = None) -> dict[str, CardDef]:
    path = path or DATA_DIR / "cards.json"
    raws = json.loads(path.read_text(encoding="utf-8"))
    return {c["number"]: _to_def(c) for c in raws}


@lru_cache(maxsize=1)
def card_db() -> dict[str, CardDef]:
    """預設卡片資料庫(載入 repo 內 data/cards.json)。"""
    return load_cards()
