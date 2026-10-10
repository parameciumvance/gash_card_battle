"""戰鬥開始的特性測試(refactor-battle-start):鎖定戰術攻擊與無戰術攻擊在各種「下一場戰鬥」待命下的
完整事件序列、戰鬥狀態與剩下的待命。期望值是重構前的實際結果(tests/golden/battle_start.json);
行為若要刻意改變,以 GOLDEN_UPDATE=1 重新產生並在 change 中說明。"""
import dataclasses
import json
import os
from pathlib import Path

import pytest

from gash.engine.cards import card_db
from gash.engine.effects.primitives import schedule_standby
from gash.engine.engine import new_game, submit
from gash.engine.state import MamodoSlot

DB = card_db()
GOLDEN = Path(__file__).parent / "golden" / "battle_start.json"

# 與各卡實際排程時相同的待命資料
STANDBYS = {
    "P-007": ("spell_bonus", {"mamodo": "フェイン", "power_delta": 4000, "cost_delta": 0, "expires": "next_battle"}),
    "ANY+1000": ("spell_bonus", {"mamodo": None, "power_delta": 1000, "cost_delta": 0, "expires": "next_battle"}),
    "M-008": ("spell_bonus", {"mamodo": "スギナ", "power_delta": -1000, "cost_delta": -1, "expires": "next_battle",
                              "optional": True}),
    "P-001": ("attack_undefendable", {"expires": "next_battle", "mamodo": "ガッシュ・ベル"}),
    "S-026": ("attack_undefendable", {"expires": "next_battle"}),
    "E-013": ("no_protect_book", {}),
    "S-057": ("injure_instead", {"expires": "next_battle"}),
}
ALL = list(STANDBYS)


def book(*pages):
    b = list(pages)
    while len(b) < 32:
        b.append("S-029")
    return b[:32]


def run(attacker_top, *, extra_slots=(), standbys=ALL, page=3, mamodo_attack=False, any_page=None, pages=(),
        discount=None):
    g = new_game(book(attacker_top, *pages), seed=0, db=DB,
                 decks=(book(attacker_top, *pages), book("M-001")))
    g.state.turn_player = 0
    ps = g.state.players[0]
    for top in extra_slots:
        ps.slots.append(MamodoSlot(uid=g.state.next_uid(), stack=[top]))
    ps.mp = 20
    submit(g, {"type": "flip_pages", "player": 0, "count": 0})
    for key in standbys:
        kind, data = STANDBYS[key]
        source = key if key[0] in "PMES" and "-" in key else "TEST"
        schedule_standby(g, [], kind=kind, source=source, owner=0, data=dict(data))
    if any_page:
        schedule_standby(g, [], kind="spell_any_page", source="P-015", owner=0, data={"spell_name": any_page})
    attacker = ps.slots[-1] if mamodo_attack or extra_slots else ps.slots[0]
    if mamodo_attack:
        cmd = {"type": "declare_attack", "player": 0, "mode": "mamodo", "slot_uid": attacker.uid}
    else:
        cmd = {"type": "declare_attack", "player": 0, "page": page, "slot_uid": attacker.uid}
    events = submit(g, cmd)
    if g.state.pending is not None:                       # M-008 的可選減費:依情境選擇使用或不使用
        assert g.state.pending.kind == "spell_discount" and discount is not None
        value = next(o["value"] for o in g.state.pending.options
                     if (o.get("label") == "spell_discount_use") == discount)
        events += submit(g, {"type": "choose", "player": 0, "value": value})
    events += submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    battle = dataclasses.asdict(g.state.battle)
    return {
        "events": [{k: v for k, v in e.items() if k != "seq"} for e in events],
        "battle": json.loads(json.dumps(battle, default=str)),
        "standby_left": [[sb.kind, sb.source] for sb in g.state.standby],
        "mp": ps.mp,
    }


SCENARIOS = {
    # 賈修以「ザケル」攻擊:限定ガッシュ・ベル的 P-001 與不限定的待命都消耗;限定其他魔物的 spell_bonus 留著
    "spell_gash": lambda: run("M-001", pages=("S-029", "S-001")),
    # ゼオン以自己的「ザケル」(S-058)攻擊:P-001 限ガッシュ・ベル,不消耗
    "spell_zeon": lambda: run("M-029", pages=("S-029", "S-058")),
    # スギナ攻擊:M-008 的可選減費待命(未選擇使用)不消耗
    "spell_sugina_optional_not_chosen": lambda: run("M-008", pages=("S-029", "S-014"), discount=False),
    # スギナ攻擊並選擇使用減費:M-008 的可選待命消耗
    "spell_sugina_optional_chosen": lambda: run("M-008", pages=("S-029", "S-014"), discount=True),
    # 無戰術攻擊(M-027):只消耗不限定魔物的 attack_undefendable 與 no_protect_book
    "mamodo_attack": lambda: run("M-028", extra_slots=("M-027",), mamodo_attack=True),
    # P-015:自任意頁使用ビライツ(第 20 頁)
    "any_page": lambda: run("M-024", page=20, any_page="ビライツ",
                            pages=tuple(["S-029"] * 18 + ["S-042"])),
    # 沒有任何待命
    "spell_plain": lambda: run("M-001", standbys=(), pages=("S-029", "S-001")),
}


def _actual():
    return {name: fn() for name, fn in SCENARIOS.items()}


def test_battle_start_matches_golden():
    actual = _actual()
    if os.environ.get("GOLDEN_UPDATE"):
        GOLDEN.parent.mkdir(exist_ok=True)
        GOLDEN.write_text(json.dumps(actual, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
        pytest.skip("golden updated")
    expected = json.loads(GOLDEN.read_text())
    for name in SCENARIOS:
        assert actual[name] == expected[name], name


def test_golden_covers_expected_consumption():
    # 對期望檔本身做幾項依效果文的檢查,避免把錯誤的行為鎖成期望值
    expected = json.loads(GOLDEN.read_text())
    left = {name: {tuple(x) for x in data["standby_left"]} for name, data in expected.items()}
    assert ("spell_bonus", "P-007") in left["spell_gash"]                 # フェイン限定,賈修攻擊不適用
    assert ("attack_undefendable", "P-001") not in left["spell_gash"]
    assert ("attack_undefendable", "P-001") in left["spell_zeon"]
    assert ("spell_bonus", "M-008") in left["spell_sugina_optional_not_chosen"]
    assert ("spell_bonus", "M-008") not in left["spell_sugina_optional_chosen"]
    mamodo = left["mamodo_attack"]
    assert {("spell_bonus", "TEST"), ("injure_instead", "S-057"), ("attack_undefendable", "P-001")} <= mamodo
    assert ("attack_undefendable", "S-026") not in mamodo and ("no_protect_book", "E-013") not in mamodo
    assert expected["mamodo_attack"]["battle"]["attack_undefendable"] is True
    assert expected["spell_gash"]["battle"]["data"].get("injure_instead") is True
    assert ("spell_any_page", "P-015") not in left["any_page"]
