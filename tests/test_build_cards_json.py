"""tools/build_cards_json.py 的轉換規則(card-data「卡片資料轉換」)。"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.build_cards_json import convert  # noqa: E402
from tools.scrape_ja_effects import FIELDNAMES  # noqa: E402


def write_csv(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FIELDNAMES})


SPELL = {"number": "S-061", "type": "spell", "name_ja": "ギガ・ラ・セウシル", "related_mamodo_ja": "ティオ",
         "cost": "4", "ad": "D", "class": "intermediate", "power": "+8000", "damage": "?", "effect_ja": "x"}
MAMODO = {"number": "M-048", "type": "mamodo", "name_ja": "ガッシュ・ベル", "related_partner_ja": "高嶺清麿",
          "class": "none", "power": "4000", "effect_ja": ""}


def test_variable_damage_and_sets_from_tts(tmp_path):
    p = tmp_path / "cards_ja.csv"
    write_csv(p, [SPELL, MAMODO])
    tts = {"M-048": {"sets": ["Zatch Bell and his Friends", "File 1"]}}
    cards = {c["number"]: c for c in convert(p, tts, {}, expected=None)}
    assert cards["S-061"]["damage"] is None and cards["S-061"]["damage_variable"] is True
    assert "damage_variable" not in cards["M-048"]
    assert cards["M-048"]["sets"] == ["Zatch Bell and his Friends", "File 1"]
    assert all("image_url" not in c for c in cards.values())       # 卡圖來源是資料夾,不是卡表的連結


def test_old_sets_take_precedence(tmp_path):
    p = tmp_path / "cards_ja.csv"
    write_csv(p, [MAMODO])
    tts = {"M-048": {"sets": ["From TTS"]}}
    cards = convert(p, tts, {"M-048": {"sets": ["Old"]}}, expected=None)
    assert cards[0]["sets"] == ["Old"]
