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


@pytest.mark.parametrize("sets_ja, sets", [
    ("LEVEL:4|TBB1|RE", ["level-4", "tbb1", "re"]),
    ("拡張3　R|TBB1　N", ["ex-sheet-3", "tbb1"]),
])
def test_season4_products(tmp_path, sets_ja, sets):
    p = tmp_path / "cards_ja.csv"
    write_csv(p, [{**MAMODO, "sets_ja": sets_ja}])
    assert convert(p, expected=None)[0]["sets"] == sets


def test_limited_expansion_by_number(tmp_path):
    # atwiki 把 DX赤い魔本 與 電撃フェスタ2004春の陣 的附錄卡都寫作「限定拡張」:依卡號區分
    p = tmp_path / "cards_ja.csv"
    numbers = ("Ex-100", "Ex-101", "Ex-000", "Ex-049", "Ex-050", "Ex-099")
    write_csv(p, [{**MAMODO, "number": n, "sets_ja": "限定拡張　N|TBB2　R"} for n in numbers])
    assert {c["number"]: c["sets"] for c in convert(p, expected=None)} == {
        "Ex-100": ["dx-red-book", "tbb2"], "Ex-101": ["dx-red-book", "tbb2"],
        **{n: ["festa-2004-spring", "tbb2"] for n in ("Ex-000", "Ex-049", "Ex-050", "Ex-099")}}


def test_unregistered_limited_expansion_aborts(tmp_path):
    p = tmp_path / "cards_ja.csv"
    write_csv(p, [{**MAMODO, "number": "Ex-075", "sets_ja": "限定拡張　N"}])
    with pytest.raises(SystemExit, match="Ex-075.*限定拡張"):
        convert(p, expected=None)


def test_stone_tablet_flag(tmp_path):
    # 石版魔物:type 仍為 mamodo,另設 stone_tablet: true;一般魔物沒有這個欄位
    p = tmp_path / "cards_ja.csv"
    write_csv(p, [{**MAMODO, "number": "Ex-056", "stone_tablet": "1", "sets_ja": "拡張3"},
                  {**MAMODO, "number": "Ex-051", "sets_ja": "拡張3"}])
    cards = {c["number"]: c for c in convert(p, expected=None)}
    assert cards["Ex-056"]["type"] == "mamodo" and cards["Ex-056"]["stone_tablet"] is True
    assert "stone_tablet" not in cards["Ex-051"]


def test_power_multiplier_letter_x(tmp_path):
    # Ex-050:atwiki 把乘號寫成英文字母 x(「1000x」),與「×」同樣是倍率
    p = tmp_path / "cards_ja.csv"
    write_csv(p, [{**SPELL, "number": "Ex-050", "power": "1000x", "damage": "?", "sets_ja": "TBB2"}])
    assert convert(p, expected=None)[0]["power"] == {"special": True, "per_heads": 1000}


def test_multiple_effect_icons(tmp_path):
    # M-080:兩個效果各有圖示(《乱入》ジャマー、《バトル乱入》バトル),依資料頭順序全部保留,不只取一個
    p = tmp_path / "cards_ja.csv"
    write_csv(p, [{**MAMODO, "number": "M-080", "effect_icon_ja": "ジャマー|バトル", "sets_ja": "LEVEL:4"},
                  {**MAMODO, "effect_icon_ja": "バトル", "sets_ja": "LEVEL:2"}])
    cards = {c["number"]: c for c in convert(p, expected=None)}
    assert cards["M-080"]["effect_icon"] is None and cards["M-080"]["effect_icons"] == ["jammer", "battle"]
    assert cards["M-048"]["effect_icon"] == "battle" and "effect_icons" not in cards["M-048"]
