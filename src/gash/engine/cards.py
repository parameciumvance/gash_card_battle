"""卡片定義與載入。cards.json 由 tools/build_cards_json.py 產出。"""

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

# 指示卡(對所有魔物的命令)的 related_mamodo 標記(日文權威來源用語)
COMMAND_ALL = "コマンド"


@dataclass(frozen=True)
class CardDef:
    number: str
    type: str
    name_ja: str
    related_mamodo: str | None
    cost: int | None
    ad: str | None          # "A" / "D" / "AD" / None
    klass: str              # "none" / "intermediate" / "superior"
    attr_name: str | None   # 屬性或《效果名》
    effect_ja: str
    effect_icon: str | None     # "battle" / "nonbattle" / "jammer" / None
    power_base: int | None      # 魔物本體魔力
    power_bonus: int | None     # 戰術的魔力加值
    power_special: bool         # 戰術魔力為 Special(不參與合計)
    damage: int | None
    image_url: str | None
    damage_variable: bool = False   # 卡面「ダメージ?」:傷害依效果決定

    @property
    def is_command_spell(self) -> bool:
        return self.type == SPELL and self.related_mamodo == COMMAND_ALL

    def can_attack(self) -> bool:
        return (self.type == SPELL and self.effect_icon != "nonbattle"
                and self.ad in ("A", "AD"))

    def can_defend(self) -> bool:
        return (self.type == SPELL and self.effect_icon != "nonbattle"
                and self.ad in ("D", "AD"))


def _to_def(raw: dict) -> CardDef:
    power = raw.get("power") or {}
    return CardDef(
        number=raw["number"],
        type=raw["type"],
        name_ja=raw["name_ja"],
        related_mamodo=raw.get("related_mamodo"),
        cost=raw.get("cost"),
        ad=raw.get("ad"),
        klass=raw.get("class", "none"),
        attr_name=raw.get("attr_name"),
        effect_ja=raw.get("effect_ja", ""),
        effect_icon=raw.get("effect_icon"),
        power_base=power.get("base"),
        power_bonus=power.get("bonus"),
        power_special=bool(power.get("special")),
        damage=raw.get("damage"),
        image_url=raw.get("image_url"),
        damage_variable=bool(raw.get("damage_variable")),
    )


def load_cards(path: Path | None = None) -> dict[str, CardDef]:
    path = path or DATA_DIR / "cards.json"
    raws = json.loads(path.read_text(encoding="utf-8"))
    return {c["number"]: _to_def(c) for c in raws}


@lru_cache(maxsize=1)
def pending_cards() -> frozenset[str]:
    """資料已收錄、效果尚未實作的卡號(data/pending_cards.json):構築規則拒絕。"""
    path = DATA_DIR / "pending_cards.json"
    if not path.exists():
        return frozenset()
    return frozenset(json.loads(path.read_text(encoding="utf-8"))["cards"])


@lru_cache(maxsize=1)
def card_db() -> dict[str, CardDef]:
    """預設卡片資料庫(載入 repo 內 data/cards.json)。"""
    return load_cards()
