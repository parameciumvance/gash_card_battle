"""規則頁的靜態檢查(battle-ui「規則頁」):段落齊全、連結都指到存在的段落。
各語言內容的檢查(不說明不存在的機制、A / D 圖示)見 test_i18n_languages.py。"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "frontend/i18n/rules.zh-TW.json"
I18N = ROOT / "frontend/i18n/zh-TW.json"
APP = ROOT / "frontend/app.js"

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




def test_every_timing_step_and_hint_links_to_an_existing_section():
    links, ids = rule_links(), set(section_ids())
    hints = {k for k in json.loads(I18N.read_text(encoding="utf-8")) if k.startswith("hint.")} - {"hint.pending"}
    required = {f"timing.{s}" for s in TIMING_STEPS} | hints
    assert required - links.keys() == set()
    assert {k: v for k, v in links.items() if v not in ids} == {}
