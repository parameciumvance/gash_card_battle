"""規則頁的靜態檢查(battle-ui「規則頁」):內容不說明不存在的機制、連結都指到存在的段落。"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "frontend/i18n/rules.zh-TW.json"
I18N = ROOT / "frontend/i18n/zh-TW.json"
APP = ROOT / "frontend/app.js"

# 規則書中有、但本遊戲(第一、二彈卡池)不存在的機制
ABSENT = ("石版", "W魔物", "VS魔物", "S魔物", "H魔物", "MJ12", "巴爾肯", "飛行")
TIMING_STEPS = ("start", "nonbattle", "battle_in", "defense", "effects", "end")


def rules():
    return json.loads(RULES.read_text(encoding="utf-8"))


def section_ids():
    return [s["id"] for s in rules()["sections"]]


def rule_links():
    src = APP.read_text(encoding="utf-8")
    block = re.search(r"const RULE_LINKS = \{(.*?)\};", src, re.S).group(1)
    return dict(re.findall(r'"((?:timing|hint)\.[a-z_]+)": "([a-z_]+)"', block))


def test_sections_are_unique_and_cover_the_rules():
    ids = section_ids()
    assert len(ids) == len(set(ids))
    assert set(ids) >= {"goal", "cards", "icons", "setup", "turn", "actions", "battle", "damage",
                        "effects", "coins", "advanced"}


def test_no_mechanics_absent_from_this_game():
    text = RULES.read_text(encoding="utf-8")
    assert [w for w in ABSENT if w in text] == []


def test_icons_section_explains_both_meanings_of_a_and_d():
    icons = next(s for s in rules()["sections"] if s["id"] == "icons")
    text = json.dumps(icons, ensure_ascii=False)
    assert "攻(A)" in text and "防(D)" in text
    assert "攻擊時" in text and "防禦時" in text                        # 攻防用的術
    assert "回合玩家" in text                                          # 事件卡與非戰鬥術


def test_every_timing_step_and_hint_links_to_an_existing_section():
    links, ids = rule_links(), set(section_ids())
    hints = {k for k in json.loads(I18N.read_text(encoding="utf-8")) if k.startswith("hint.")} - {"hint.pending"}
    required = {f"timing.{s}" for s in TIMING_STEPS} | hints
    assert required - links.keys() == set()
    assert {k: v for k, v in links.items() if v not in ids} == {}


def test_hints_name_card_icons_as_printed():
    d = json.loads(I18N.read_text(encoding="utf-8"))
    hints = " ".join(v for k, v in d.items() if k.startswith("hint."))
    assert "自己的回合」圖示" not in hints and "對手的回合」圖示" not in hints
    assert "攻(A)" in d["hint.own_turn_cards"] and "防(D)" in d["hint.opp_turn_cards"]
