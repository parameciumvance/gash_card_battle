"""產生日文與英文的卡片文字檔(card-data「日文與英文卡片文字」)。

- `data/cards.ja.json`:完全由 `data/cards_ja.csv`(日文權威來源)產生,不手動編輯。
  `name` / `name_ja` = `name_ja`;`effect` = `effect_ja`;`attr` 對術卡為 `attr_ja`(元素),
  對魔物與搭檔卡為 `effect_ja` 中第一個《》括起的效果名,沒有時 None;事件卡 None。
- `data/cards.en.json`:`name` / `attr` 由 TTS 卡表(`Zatch Bell CCG List for TTS.xlsx`)的英文卡名與
  Attribute / Effect Name 寫入(「-」為 None);`effect` 是依 `effect_ja` 手寫的翻譯,保留檔中既有的值。
  卡表的英文效果文與日文效果文有出入,不作為翻譯依據。

用法: python tools/build_card_texts.py
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data/cards_ja.csv"
XLSX = ROOT / "openspec/specs/card-data/Zatch Bell CCG List for TTS.xlsx"
JA_OUT = ROOT / "data/cards.ja.json"
EN_OUT = ROOT / "data/cards.en.json"

EFFECT_NAME_RE = re.compile(r"《([^》]+)》")


def load_csv(csv_path: Path = CSV_PATH) -> list[dict]:
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def ja_attr(row: dict) -> str | None:
    if row["type"] == "spell":
        return row["attr_ja"].strip() or None
    if row["type"] in ("mamodo", "partner"):
        m = EFFECT_NAME_RE.search(row["effect_ja"])
        return m.group(1) if m else None
    return None


def build_ja(rows: list[dict]) -> dict[str, dict]:
    return {
        row["number"]: {
            "name": row["name_ja"],
            "name_ja": row["name_ja"],
            "attr": ja_attr(row),
            "effect": row["effect_ja"],
        }
        for row in sorted(rows, key=lambda r: r["number"])
    }


def _card_number(cell) -> str:
    value = str(cell.value or "")
    if value.startswith("=HYPERLINK"):
        return re.findall(r'"([^"]*)"', value)[-1]
    return value.strip()


def _dash_none(value) -> str | None:
    s = str(value or "").strip()
    return None if s in ("", "-") else s


def load_tts_names(xlsx_path: Path = XLSX) -> dict[str, dict]:
    """卡號 → {name, attr}。同一卡號有 e / j 兩版時英文名稱相同,取第一筆。"""
    wb = openpyxl.load_workbook(xlsx_path, read_only=True)
    ws = wb["The Table"]
    out: dict[str, dict] = {}
    for cells in ws.iter_rows():
        m = re.fullmatch(r"([A-Z]+-\d+)[ej]?", _card_number(cells[0]))
        if not m or m.group(1) in out:
            continue
        out[m.group(1)] = {"name": _dash_none(cells[2].value), "attr": _dash_none(cells[7].value)}
    return out


def build_en(rows: list[dict], tts: dict[str, dict], existing: dict[str, dict]) -> dict[str, dict]:
    out = {}
    for row in sorted(rows, key=lambda r: r["number"]):
        num = row["number"]
        out[num] = {
            "name": tts[num]["name"],
            "name_ja": row["name_ja"],
            "attr": tts[num]["attr"],
            "effect": existing.get(num, {}).get("effect", ""),
        }
    return out


def _write(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def main() -> None:
    rows = load_csv()
    _write(JA_OUT, build_ja(rows))
    existing = json.loads(EN_OUT.read_text(encoding="utf-8")) if EN_OUT.exists() else {}
    en = build_en(rows, load_tts_names(), existing)
    _write(EN_OUT, en)
    missing = [n for n, c in en.items() if not c["effect"]]
    print(f"已寫入 {JA_OUT.name}、{EN_OUT.name}: {len(en)} 張;英文效果未翻譯: {missing or '無'}")


if __name__ == "__main__":
    main()
