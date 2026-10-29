"""tools/build_cards_json.py 的轉換規則(card-data「卡片資料轉換」)。"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402

from tools.build_cards_json import CSV_PATH, convert  # noqa: E402
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


def test_variable_damage(tmp_path):
    p = tmp_path / "cards_ja.csv"
    write_csv(p, [SPELL, MAMODO])
    cards = {c["number"]: c for c in convert(p, expected=None)}
    assert cards["S-061"]["damage"] is None and cards["S-061"]["damage_variable"] is True
    assert "damage_variable" not in cards["M-048"]
    assert all("image_url" not in c for c in cards.values())       # 卡圖來源是資料夾,不是卡表的連結


def test_sets_from_sets_ja(tmp_path):
    # 去掉稀有度與販售形式,轉為產品代號,去重並依對照表順序
    p = tmp_path / "cards_ja.csv"
    write_csv(p, [{**MAMODO, "sets_ja": "TBB2　N|LEVEL:2　Rパック・自販機|LEVEL:2　Nスターター|RE　R"}])
    assert convert(p, expected=None)[0]["sets"] == ["level-2", "tbb2", "re"]


def test_unknown_product_aborts(tmp_path):
    p = tmp_path / "cards_ja.csv"
    write_csv(p, [{**MAMODO, "sets_ja": "LEVEL:9　N"}])
    with pytest.raises(SystemExit, match="M-048.*LEVEL:9"):
        convert(p, expected=None)


def test_every_card_has_a_product():
    cards = convert(CSV_PATH)
    assert all(c["sets"] for c in cards)
    assert {c["number"]: c["sets"] for c in cards}["P-018"] == ["level-2", "tbb2", "re"]


@pytest.mark.parametrize("sets_ja, sets", [
    ("拡張2　R|TBB2　N", ["ex-sheet-2", "tbb2"]),
    ("拡張1　R", ["ex-sheet-1"]),
    ("SPBOX|TBB1|RE", ["special-box", "tbb1", "re"]),
    ("LTD1", ["limited-1"]),
    ("プロモ", ["promo"]),
])
def test_season3_products(tmp_path, sets_ja, sets):
    p = tmp_path / "cards_ja.csv"
    write_csv(p, [{**MAMODO, "sets_ja": sets_ja}])
    assert convert(p, expected=None)[0]["sets"] == sets


def test_mahon_file_volumes_by_number(tmp_path):
    # atwiki 第1、2弾都寫「別売魔本」:M-059–M-061 是第2弾
    p = tmp_path / "cards_ja.csv"
    write_csv(p, [{**MAMODO, "number": n, "sets_ja": "別売魔本"} for n in ("M-032", "M-059", "M-060", "M-061")])
    assert {c["number"]: c["sets"] for c in convert(p, expected=None)} == {
        "M-032": ["mahon-file"], "M-059": ["mahon-file-2"], "M-060": ["mahon-file-2"], "M-061": ["mahon-file-2"]}
