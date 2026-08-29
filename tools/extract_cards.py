"""從 openspec/specs/card-data 的 xlsx 抽取 Level 1 + Level 2 卡片資料,產出 data/cards.json。

- 過濾「The Table」工作表中 Sets 標籤含 "Level 1"、"Level 2" 或 "Series 1 Level 2"
  (最後者為 1 張卡的資料例外標籤)的列;標籤以逗號拆分後精確比對。
- 卡號取自 A 欄 HYPERLINK 公式的顯示文字(如 M-001、S-019j),卡圖連結取自 URL。
- 同卡號存在 e(美版)/j(日版)兩版時,只保留 j 版,以基礎卡號入庫;
  同卡號跨產品重複時只入庫一筆(sets 保留該列完整標籤)。

用法: python tools/extract_cards.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
XLSX = ROOT / "openspec/specs/card-data/Zatch Bell CCG List for TTS.xlsx"
OUT = ROOT / "data/cards.json"

EXPECTED_COUNT = 134  # Level 1: M×15+S×28+P×9+E×15 = 67;Level 2 新增: M×16+S×29+P×10+E×12 = 67
INCLUDE_SETS = {"Level 1", "Level 2", "Series 1 Level 2"}

CARD_TYPES = {"Mamodo": "mamodo", "Partner": "partner", "Spell": "spell", "Event": "event"}
CLASSES = {"None": "none", "Intermediate": "intermediate", "Superior": "superior"}


def parse_card_cell(cell) -> tuple[str | None, str]:
    """回傳 (卡圖URL, 卡號)。A 欄有兩種形態:
    - HYPERLINK 公式(前幾列): =HYPERLINK("url","E-001")
    - 純文字卡號 + 儲存格超連結物件(需非 read_only 模式才讀得到)
    """
    value = str(cell.value or "")
    if value.startswith("=HYPERLINK"):
        quoted = re.findall(r'"([^"]*)"', value)
        if len(quoted) >= 2:
            return quoted[0], quoted[-1]
        raise ValueError(f"無法解析卡號欄: {value!r}")
    url = cell.hyperlink.target if cell.hyperlink is not None else None
    return url, value.strip()


def parse_int(value, *, none_ok=True) -> int | None:
    s = str(value).strip()
    if s in ("-", "", "None"):
        if none_ok:
            return None
        raise ValueError(f"預期數值: {value!r}")
    return int(float(s))


def parse_power(value) -> dict:
    """魔物: 4000.0 → {'base': 4000}; 術: '+2000' → {'bonus': 2000}; 'Special' → {'special': True};
    'x2000'(S-040 擲幣倍乘)→ {'special': True, 'per_heads': 2000}"""
    s = str(value).strip()
    if s in ("-", "", "None"):
        return {}
    if s == "Special":
        return {"special": True}
    if s.startswith("x"):
        return {"special": True, "per_heads": int(float(s[1:]))}
    if s.startswith("+"):
        return {"bonus": int(float(s[1:]))}
    return {"base": int(float(s))}


def extract() -> list[dict]:
    wb = openpyxl.load_workbook(XLSX)  # 非 read_only:才能讀儲存格超連結物件
    ws = wb["The Table"]
    all_rows = list(ws.iter_rows())
    header = [c.value for c in all_rows[0]]
    assert header[0] == "Card #" and header[8] == "Effect", "工作表欄位不符預期"

    by_number: dict[str, dict] = {}
    versions: dict[str, str] = {}  # 基礎卡號 → 已入庫版本尾碼('' / 'e' / 'j')

    for cells in all_rows[1:]:
        row = [c.value for c in cells]
        tags = {s.strip() for s in str(row[11] or "").split(",") if s.strip()}
        if not tags & INCLUDE_SETS:
            continue
        image_url, raw_number = parse_card_cell(cells[0])
        m = re.fullmatch(r"([A-Z]+-\d+)([ej]?)", raw_number)
        if not m:
            raise ValueError(f"卡號格式不符: {raw_number!r}")
        number, suffix = m.group(1), m.group(2)

        # e/j 去重: j 版優先
        if number in versions and not (suffix == "j" and versions[number] == "e"):
            continue
        versions[number] = suffix

        card_type = CARD_TYPES[str(row[1]).strip()]
        power = parse_power(row[9])
        by_number[number] = {
            "number": number,
            "type": card_type,
            "name_en": str(row[2]).strip(),
            "related_mamodo": None if str(row[3]).strip() == "-" else str(row[3]).strip(),
            "cost": parse_int(row[4]),
            "ad": None if str(row[5]).strip() == "-" else str(row[5]).strip(),
            "class": CLASSES[str(row[6]).strip()] if row[6] else "none",
            "attr_name": None if str(row[7]).strip() == "-" else str(row[7]).strip(),
            "effect_en": str(row[8]).strip(),
            "power": power,
            "damage": parse_int(row[10]),
            "sets": [s.strip() for s in str(row[11]).split(",") if s.strip()],
            "text_version": suffix or None,
            "image_url": image_url,
        }

    cards = sorted(by_number.values(), key=lambda c: (c["number"][0], c["number"]))
    if len(cards) != EXPECTED_COUNT:
        raise SystemExit(f"抽出 {len(cards)} 種,預期 {EXPECTED_COUNT} 種")
    return cards


def main() -> None:
    cards = extract()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(cards, ensure_ascii=False, indent=1), encoding="utf-8")
    from collections import Counter

    counts = Counter(c["type"] for c in cards)
    dual = [c["number"] for c in cards if c["text_version"] == "j"]
    print(f"已寫入 {OUT}: {len(cards)} 種 {dict(counts)}")
    print(f"e/j 雙版本、採 j 版: {dual}")


if __name__ == "__main__":
    main()
