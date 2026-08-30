"""從 data/cards_ja.csv(日文權威來源)轉換產出 data/cards.json。

- `power` 單一字串欄位解析回 {base/bonus/special/per_heads} 結構。
- `attr_name` 只在術卡填入 `attr_ja`,魔物/夥伴卡一律 None(僅 M-023 讀取,不承擔顯示職責)。
- `related_mamodo`:術/夥伴/事件卡直接取 `related_mamodo_ja`;魔物卡以 `name_ja` 去除
  括號後綴(如「（変身後）」)推導,使變身/形態卡與基礎家族名一致。
- `image_url`/`sets` 沿用轉換前 `data/cards.json` 同卡號的舊值;無舊值(新卡如 S-042)
  則分別為 None / []。

用法: python tools/build_cards_json.py
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data/cards_ja.csv"
OUT = ROOT / "data/cards.json"

EXPECTED_COUNT = 135  # 134(第一彈+Level 2)+ S-042

FORM_SUFFIX_RE = re.compile(r"（[^）]*）")
POWER_X_RE = re.compile(r"^(\d+)×$")
POWER_BONUS_RE = re.compile(r"^\+(\d+)$")
POWER_BASE_RE = re.compile(r"^(\d+)$")


def _none_if_blank(s: str) -> str | None:
    s = s.strip()
    return s or None


def _int_or_none(s: str) -> int | None:
    s = s.strip()
    return int(s) if s else None


def parse_power(value: str) -> dict:
    s = value.strip()
    if not s:
        return {}
    if s == "特殊":
        return {"special": True}
    m = POWER_X_RE.match(s)
    if m:
        return {"special": True, "per_heads": int(m.group(1))}
    m = POWER_BONUS_RE.match(s)
    if m:
        return {"bonus": int(m.group(1))}
    m = POWER_BASE_RE.match(s)
    if m:
        return {"base": int(m.group(1))}
    raise ValueError(f"無法解析 power 格式: {value!r}")


def derive_related_mamodo(row: dict) -> str | None:
    if row["type"] == "mamodo":
        base = FORM_SUFFIX_RE.sub("", row["name_ja"]).strip()
        return base or None
    return _none_if_blank(row["related_mamodo_ja"])


def derive_attr_name(row: dict) -> str | None:
    if row["type"] == "spell":
        return _none_if_blank(row["attr_ja"])
    return None


def load_old_cards(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    raws = json.loads(path.read_text(encoding="utf-8"))
    return {c["number"]: c for c in raws}


def convert(csv_path: Path, old_cards: dict[str, dict]) -> list[dict]:
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    cards = []
    for row in rows:
        old = old_cards.get(row["number"], {})
        cards.append(
            {
                "number": row["number"],
                "type": row["type"],
                "name_en": row["name_ja"],
                "related_mamodo": derive_related_mamodo(row),
                "cost": _int_or_none(row["cost"]),
                "ad": _none_if_blank(row["ad"]),
                "class": row["class"],
                "attr_name": derive_attr_name(row),
                "effect_en": row["effect_ja"],
                "power": parse_power(row["power"]),
                "damage": _int_or_none(row["damage"]),
                "sets": old.get("sets", []),
                "image_url": old.get("image_url"),
            }
        )

    cards.sort(key=lambda c: (c["number"][0], c["number"]))
    if len(cards) != EXPECTED_COUNT:
        raise SystemExit(f"轉換出 {len(cards)} 種,預期 {EXPECTED_COUNT} 種")
    return cards


def main() -> None:
    old_cards = load_old_cards(OUT)
    cards = convert(CSV_PATH, old_cards)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(cards, ensure_ascii=False, indent=1), encoding="utf-8")

    from collections import Counter

    counts = Counter(c["type"] for c in cards)
    no_image = [c["number"] for c in cards if c["image_url"] is None]
    print(f"已寫入 {OUT}: {len(cards)} 種 {dict(counts)}")
    print(f"沒有卡圖連結(新卡): {no_image}")


if __name__ == "__main__":
    main()
