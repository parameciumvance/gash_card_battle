"""具有限制效果的卡(card-effects「具有限制效果的卡」,E-045 的對象)。

守門:效果文含限制字樣的已開放卡,必須能由實作推導出限制種類,或列在排除名單並附理由。
新增卡片時,實作沒有使用限制旗標、也沒有標示 `restricts` 時,這裡會失敗並列出卡號。
"""

import re

from gash.engine.cards import pending_cards
from gash.engine.effects.tree import restriction_kinds
from tests.test_level2 import DB

# 「術」「かばう」「魔物の効果」「攻撃」+「使えない / できない」;「防御できない」不是這三種限制
RESTRICTION_TEXT = re.compile(r"(術|かば|魔物の効果|攻撃)[^。、●]{0,15}?(使えない|使えず|できない|できず)")

EXCLUDED = {
    "E-031": "解除限制:「かばうことができない」ときにも「かばう」ことができる",
    "E-036": "移除限制的效果",
    "M-038": "無視限制:「術を使えない」ときにも、この魔物の術が使える",
    "M-042": "無視限制:「かばうことができない」ときにでも「かばう」ことができる",
    "M-051": "卡片規則:この魔物は「かばう」ことができない(不是效果)",
    "M-058": "卡片規則:自分は、この魔物の術を使えない(使用者 2026-10-31)",
    "E-045": "以限制效果為對象的效果,本身不限制",
}

# atwiki E-045 卡頁 FAQ 列出的卡(2004-01-28),加上同類的 Ex-044、P-031(使用者 2026-10-31)
FAQ = ("M-006", "P-014", "P-026", "P-033", "P-043", "S-004", "S-009", "S-011", "S-014", "S-035", "S-068",
       "S-074", "S-075", "S-081", "S-110", "S-111", "Ex-015", "E-002", "E-013", "E-024", "E-025", "E-039",
       "E-043", "E-047", "PR-005", "PR-009", "Ex-044", "P-031")


def restriction_text(number):
    return [m.group(0) for m in RESTRICTION_TEXT.finditer(DB[number].effect_ja or "")
            if "防御" not in m.group(0)]


def test_cards_with_restriction_text_are_derived_or_excluded():
    missing = [n for n in DB if n not in pending_cards() and n not in EXCLUDED
               and restriction_text(n) and not restriction_kinds(n)]
    assert missing == [], "效果文有限制字樣,但實作沒有標示限制種類(或加進排除名單並附理由)"


def test_excluded_cards_are_not_derived():
    assert [n for n in EXCLUDED if restriction_kinds(n)] == []


def test_faq_cards_have_restriction_effects():
    assert [n for n in FAQ if not restriction_kinds(n)] == []


def test_kinds_follow_effect_text():
    assert restriction_kinds("E-025") == {"mamodo_effects"}
    assert restriction_kinds("P-026") == {"protect"}
    assert restriction_kinds("E-002") == {"spells"}
    assert restriction_kinds("E-008") == frozenset()                       # 「パートナーの効果を使えない」不算
