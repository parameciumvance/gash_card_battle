"""從 data/cards_ja.csv(日文權威來源)轉換產出 data/cards.json。

- `power` 單一字串欄位解析回 {base/bonus/special/per_heads} 結構。
- `attr_name` 只在術卡填入 `attr_ja`,魔物/搭檔卡一律 None(僅 M-023 讀取,不承擔顯示職責)。
- `related_mamodo`:術/搭檔/事件卡直接取 `related_mamodo_ja`;魔物卡以 `name_ja` 去除
  括號後綴(如「（変身後）」)推導,使變身/形態卡與基礎家族名一致。
- `effect_icon`:バトル/非バトル/ジャマー 轉為 battle/nonbattle/jammer,空字串為 None。
- `sets`:`sets_ja` 每筆取全形空白前的產品名(去掉稀有度與販售形式),依 PRODUCTS 轉為產品代號,
  去重並依 PRODUCTS 順序;PRODUCTS 沒有的產品名中止轉換(新產品要先決定代號)。
  魔本ファイル第1、2弾在 atwiki 都寫「別売魔本」,MAHON_FILE_2 的卡轉為第2弾。
- 不含卡圖連結:卡圖來源是 `tools/download_images.py` 的資料夾。

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

EXPECTED_COUNT = 332  # 第一彈+Level 2 共 135(含 S-042)+ 第三彈 102 + 第 3 賽季其餘 95

FORM_SUFFIX_RE = re.compile(r"（[^）]*）")
POWER_X_RE = re.compile(r"^(\d+)×$")
POWER_BONUS_RE = re.compile(r"^\+(\d+)$")
POWER_BASE_RE = re.compile(r"^(\d+)$")

EFFECT_ICON_MAP = {"バトル": "battle", "非バトル": "nonbattle", "ジャマー": "jammer"}

# 日文產品名 → 產品代號(前端篩選、產品圖檔名與介面字串的鍵);順序即 sets 的排列順序
PRODUCTS = {
    "LEVEL:1": "level-1",
    "LEVEL:2": "level-2",
    "別売魔本": "mahon-file",
    "LEVEL:3": "level-3",
    "ガッシュ・ベルと仲間たち": "cardset-gash-nakama",
    "ゼオンと最凶魔物達": "cardset-zeon",
    "LTD1": "limited-1",
    "SPBOX": "special-box",
    "別売魔本(第2弾)": "mahon-file-2",   # atwiki 不分第1、2弾,依卡號轉換(MAHON_FILE_2)
    "拡張1": "ex-sheet-1",
    "拡張2": "ex-sheet-2",
    "プロモ": "promo",
    "LEVEL:S": "level-s",
    "TBB1": "tbb1",
    "TBB2": "tbb2",
    "RE": "re",
    "FILE:1": "file-1",
}
PRODUCT_ORDER = list(PRODUCTS.values())
# 魔本ファイル第2弾的卡:atwiki 卡頁的收錄產品與第1弾同為「別売魔本」,只有商品頁分開列出
MAHON_FILE_2 = {"M-059", "M-060", "M-061"}


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


def derive_effect_icon(row: dict) -> str | None:
    icon = row["effect_icon_ja"].strip()
    if not icon:
        return None
    return EFFECT_ICON_MAP[icon]


def derive_sets(row: dict) -> list[str]:
    codes = set()
    for entry in filter(None, row["sets_ja"].split("|")):
        name = entry.split("\u3000")[0]
        if name == "別売魔本" and row["number"] in MAHON_FILE_2:
            name = "別売魔本(第2弾)"
        if name not in PRODUCTS:
            raise SystemExit(f"{row['number']}: 產品對照表沒有「{name}」,請先在 PRODUCTS 登記代號")
        codes.add(PRODUCTS[name])
    return sorted(codes, key=PRODUCT_ORDER.index)


def convert(csv_path: Path, expected: int | None = EXPECTED_COUNT) -> list[dict]:
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    cards = []
    for row in rows:
        card = (
            {
                "number": row["number"],
                "type": row["type"],
                "name_ja": row["name_ja"],
                "related_mamodo": derive_related_mamodo(row),
                "cost": _int_or_none(row["cost"]),
                "ad": _none_if_blank(row["ad"]),
                "class": row["class"],
                "attr_name": derive_attr_name(row),
                "effect_ja": row["effect_ja"],
                "effect_icon": derive_effect_icon(row),
                "power": parse_power(row["power"]),
                "damage": None if row["damage"] == "?" else _int_or_none(row["damage"]),
                "sets": derive_sets(row),
            }
        )
        if row["damage"] == "?":                 # 傷害依效果決定(卡面「ダメージ?」)
            card["damage_variable"] = True
        cards.append(card)

    cards.sort(key=lambda c: (c["number"][0], c["number"]))
    if expected is not None and len(cards) != expected:
        raise SystemExit(f"轉換出 {len(cards)} 種,預期 {expected} 種")
    return cards


def main() -> None:
    cards = convert(CSV_PATH)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(cards, ensure_ascii=False, indent=1), encoding="utf-8")

    from collections import Counter

    counts = Counter(c["type"] for c in cards)
    print(f"已寫入 {OUT}: {len(cards)} 種 {dict(counts)}")


if __name__ == "__main__":
    main()
