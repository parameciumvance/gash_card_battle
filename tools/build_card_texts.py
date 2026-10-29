"""產生日文與英文的卡片文字檔(card-data「日文與英文卡片文字」)。

- `data/cards.ja.json`:完全由 `data/cards_ja.csv`(日文權威來源)產生,不手動編輯。
  `name` / `name_ja` = `name_ja`;`effect` = `effect_ja`;`attr` 對戰術卡為 `attr_ja`(元素),
  對魔物與搭檔卡為 `effect_ja` 中第一個《》括起的效果名,沒有時 None;事件卡 None。
- `data/cards.en.json`:`name` / `attr` 由 TTS 卡表(`Zatch Bell CCG List for TTS.xlsx`)的英文卡名與
  Attribute / Effect Name 寫入(「-」為 None);卡表屬性缺漏的戰術,依卡表中同一元素其他戰術的英文補上
  (`element_names`,卡表沒有該元素的英文時仍為 None)。`effect` 是依 `effect_ja` 手寫的翻譯,保留檔中既有的值。
  卡表的英文效果文與日文效果文有出入,不作為翻譯依據。卡表的擴張卡寫作 EX-,對應為卡號 Ex-。

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
    """卡號 → {name, attr}。同一卡號有 e / j 兩版時英文名稱相同,取第一筆。
    卡表的擴張卡寫作「EX-」,依 atwiki 的卡號寫法對應為「Ex-」。"""
    wb = openpyxl.load_workbook(xlsx_path, read_only=True)
    ws = wb["The Table"]
    out: dict[str, dict] = {}
    for cells in ws.iter_rows():
        m = re.fullmatch(r"([A-Z]+-\d+)[ej]?", _card_number(cells[0]))
        number = m and re.sub(r"^EX-", "Ex-", m.group(1))
        if not m or number in out:
            continue
        out[number] = {"name": _dash_none(cells[2].value), "attr": _dash_none(cells[7].value)}
    return out


def element_names(rows: list[dict], tts: dict[str, dict]) -> dict[str, str]:
    """日文元素 → 卡表中戰術的英文屬性(S-091 / S-092 等卡表缺漏時補值用)。
    卡表對同一元素有兩種英文時報錯,不默默挑一個。"""
    out: dict[str, str] = {}
    for row in rows:
        element, attr = ja_attr(row), tts.get(row["number"], {}).get("attr")
        if row["type"] != "spell" or not element or not attr:
            continue
        if out.setdefault(element, attr) != attr:
            raise ValueError(f"卡表中元素「{element}」有兩種英文:{out[element]} / {attr}({row['number']})")
    return out


def build_en(rows: list[dict], tts: dict[str, dict], existing: dict[str, dict]) -> dict[str, dict]:
    names = element_names(rows, tts)
    out = {}
    for row in sorted(rows, key=lambda r: r["number"]):
        num = row["number"]
        attr = tts[num]["attr"] if ja_attr(row) else None  # 日文沒有效果名(白板魔物)時不留卡表的英文
        if attr is None and row["type"] == "spell" and ja_attr(row):
            attr = names.get(ja_attr(row))
        out[num] = {
            "name": tts[num]["name"],
            "name_ja": row["name_ja"],
            "attr": attr,
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
    effect_ja = {row["number"]: row["effect_ja"] for row in rows}
    missing = [n for n, c in en.items() if not c["effect"] and effect_ja[n]]   # 白板魔物沒有效果文
    print(f"已寫入 {JA_OUT.name}、{EN_OUT.name}: {len(en)} 張;英文效果未翻譯: {missing or '無'}")


if __name__ == "__main__":
    main()
