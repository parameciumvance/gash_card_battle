"""對戰資訊的可見性:魔力勝負明細(game-engine)、決策與戰鬥的公開脈絡(battle-api)。

魔本頁面備忘(level1):P1=M-001 P2=S-025 P3=S-001(ガッシュ 2000) P32=S-005
"""

import random

from gash import npc
from gash.api.views import snapshot
from gash.engine.awaiting import awaited_player
from gash.engine.engine import submit
from gash.engine.state import GAME_OVER
from tests.test_cards import HEADS, TAILS, book, both_pass, game, give, showdown_of, slot0, start_attack

VIEWERS = (0, 1, "spectator")


def total(items):
    return sum(i["amount"] for i in items)


def item(items, kind):
    found = [i for i in items if i["kind"] == kind]
    assert len(found) == 1, (kind, items)
    return found[0]


# ================================================================ 魔力勝負明細

def test_breakdown_sums_to_totals_in_self_play():
    """NPC 自我對戰(預組)的每一場魔力勝負:雙方明細加總等於合計。"""
    from tests.test_npc import play_out
    showdowns = []
    for seed, decks in ((1, ("level1", "level2")), (2, ("level2", "level1"))):
        g = play_out(("normal", "normal"), decks, seed)
        showdowns += [e for e in g.events if e["type"] == "showdown"]
    assert len(showdowns) >= 10
    for ev in showdowns:
        assert total(ev["attacker_breakdown"]) == ev["attacker_total"]
        assert total(ev["defender_breakdown"]) == ev["defender_total"]


def test_breakdown_lists_mamodo_and_spell_and_empty_no_defense():
    g = game(turn=0)
    start_attack(g, 3)                                                  # ガッシュ 4000 + S-001 2000
    submit(g, {"type": "no_defense", "player": 1})
    ev = showdown_of(both_pass(g))
    att = ev["attacker_breakdown"]
    assert item(att, "mamodo") == {"kind": "mamodo", "source": "M-001", "amount": 4000}
    assert item(att, "spell") == {"kind": "spell", "source": "S-001", "amount": 2000}
    assert ev["attacker_total"] == 6000
    assert ev["defender_breakdown"] == [] and ev["defender_total"] == 0   # 不防禦:明細為空


def test_breakdown_names_standby_spell_bonus_source():
    """P-007 的待命提供術加成:攻方明細有一項來源為 P-007 的術加成。"""
    g = game(book0=book(first="M-011", p3="S-019"), turn=0)              # フェイン 3000 + S-019 3000
    slot0(g, 0).partner = "P-007"
    submit(g, {"type": "flip_pages", "player": 0, "count": 0})
    submit(g, {"type": "use_field_ability", "player": 0, "zone": "partner", "slot_uid": slot0(g, 0).uid})
    submit(g, {"type": "pass", "player": 1})
    submit(g, {"type": "declare_attack", "player": 0, "page": 3})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    submit(g, {"type": "no_defense", "player": 1})
    ev = showdown_of(both_pass(g))
    att = ev["attacker_breakdown"]
    assert item(att, "spell_bonus") == {"kind": "spell_bonus", "source": "P-007", "amount": 4000}
    assert total(att) == ev["attacker_total"] == 10000


def test_breakdown_names_negation_source():
    """防方以 P-009 使攻擊無效:攻方合計 0,明細的無效化來源為 P-009。"""
    g = game(turn=0)
    tio = give(g, 1, "M-014", partner="P-009")
    start_attack(g, 3)
    submit(g, {"type": "no_defense", "player": 1})
    submit(g, {"type": "pass", "player": 0})
    submit(g, {"type": "use_field_ability", "player": 1, "zone": "partner", "slot_uid": tio.uid})
    assert g.state.battle.attack_negated
    ev = showdown_of(both_pass(g))
    att = ev["attacker_breakdown"]
    assert item(att, "negated")["source"] == "P-009"
    assert ev["attacker_total"] == 0 and total(att) == 0


def test_breakdown_power_zero():
    """對手以 P-011 使攻方魔物魔力視為 0:魔物部分加總為 0,調整項來源為 P-011。"""
    g = game(turn=0)
    haido = give(g, 1, "M-021", partner="P-011")
    submit(g, {"type": "flip_pages", "player": 0, "count": 0})
    submit(g, {"type": "pass", "player": 0})
    submit(g, {"type": "use_field_ability", "player": 1, "zone": "partner", "slot_uid": haido.uid})
    submit(g, {"type": "declare_attack", "player": 0, "page": 3})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    submit(g, {"type": "no_defense", "player": 1})
    ev = showdown_of(both_pass(g))
    att = ev["attacker_breakdown"]
    zero = item(att, "power_zero")
    assert zero["source"] == "P-011" and zero["amount"] == -4000
    assert ev["attacker_total"] == 2000 and total(att) == 2000           # 只剩術魔力


# ================================================================ 擲幣詢問的公開脈絡

def test_m012_prompt_carries_results_for_every_viewer():
    g = game(coins=(TAILS, TAILS, HEADS))
    dp = 1 - g.state.turn_player
    give(g, dp, "M-012")
    start_attack(g, 3)
    g.state.players[dp].book[1] = "S-027"                               # 擲 2 枚
    submit(g, {"type": "declare_defense", "player": dp, "page": 2, "slot_uid": slot0(g, dp).uid})
    assert g.state.pending.kind == "coin_confirm"
    assert g.state.pending.info == {"results": ["tails", "tails"]}
    for viewer in VIEWERS:
        assert snapshot(g, viewer)["pending"]["info"] == {"results": ["tails", "tails"]}


def test_m019_prompt_carries_results():
    from tests.test_cards import _e020_use
    g, _ = _e020_use((HEADS, TAILS), p0="M-019")
    assert g.state.pending.kind == "opp_coin_redo"
    assert g.state.pending.info == {"results": ["heads"]}


def test_e011_paid_reflip_prompt_carries_results():
    g = game(book0=book(p2="E-011"), coins=(TAILS, TAILS, HEADS))
    g.state.players[0].discard.append("P-001")
    g.state.players[0].mp = 9
    submit(g, {"type": "flip_pages", "player": 0, "count": 0})
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    assert g.state.pending.kind == "paid_reflip"
    assert snapshot(g, 1)["pending"]["info"] == {"results": ["tails"]}
    submit(g, {"type": "choose", "player": 0, "value": True})         # 重擲仍是反面 → 再問一次
    assert g.state.pending.kind == "paid_reflip"
    assert snapshot(g, "spectator")["pending"]["info"] == {"results": ["tails"]}


# ================================================================ 快照:戰鬥明細與作用中效果

def test_snapshot_battle_breakdown_matches_totals():
    g = game(turn=0)
    start_attack(g, 3)
    submit(g, {"type": "declare_defense", "player": 1, "page": 3})      # 防方也用 S-001
    for viewer in VIEWERS:
        b = snapshot(g, viewer)["battle"]
        assert total(b["attacker_breakdown"]) == b["attacker_total"] == 6000
        assert total(b["defender_breakdown"]) == b["defender_total"] == 6000


def test_snapshot_lists_active_effects_without_internal_data():
    g = game(book0=book(first="M-011", p3="S-019"), turn=0)
    slot0(g, 0).partner = "P-007"
    haido = give(g, 1, "M-021", partner="P-011")
    submit(g, {"type": "flip_pages", "player": 0, "count": 0})
    submit(g, {"type": "use_field_ability", "player": 0, "zone": "partner", "slot_uid": slot0(g, 0).uid})
    submit(g, {"type": "use_field_ability", "player": 1, "zone": "partner", "slot_uid": haido.uid})
    effects = [snapshot(g, v)["effects"] for v in VIEWERS]
    assert effects[0] == effects[1] == effects[2]                       # 所有視角相同
    standby = next(e for e in effects[0] if e["type"] == "standby")
    assert standby["kind"] == "spell_bonus" and standby["source"] == "P-007" and standby["owner"] == 0
    assert standby["expires"] == "next_battle"
    modifier = next(e for e in effects[0] if e["type"] == "modifier")
    assert modifier["kind"] == "power_zero" and modifier["source"] == "P-011" and modifier["owner"] == 1
    assert modifier["target_player"] == 0 and modifier["target_slot"] == slot0(g, 0).uid
    assert modifier["duration"] == "turn"
    for e in effects[0]:
        assert "data" not in e and "tree_cont" not in str(e)


def test_consumed_standby_is_not_listed():
    g = game(book0=book(first="M-011", p3="S-019"), turn=0)
    slot0(g, 0).partner = "P-007"
    submit(g, {"type": "flip_pages", "player": 0, "count": 0})
    submit(g, {"type": "use_field_ability", "player": 0, "zone": "partner", "slot_uid": slot0(g, 0).uid})
    assert any(e["source"] == "P-007" for e in snapshot(g, 0)["effects"])
    submit(g, {"type": "pass", "player": 1})
    submit(g, {"type": "declare_attack", "player": 0, "page": 3})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})   # 戰鬥開始:待命被消耗
    assert not any(e["source"] == "P-007" for e in snapshot(g, 0)["effects"])


def test_effects_expire_from_the_list():
    g = game(turn=0)
    haido = give(g, 1, "M-021", partner="P-011")
    submit(g, {"type": "flip_pages", "player": 0, "count": 0})
    submit(g, {"type": "pass", "player": 0})
    submit(g, {"type": "use_field_ability", "player": 1, "zone": "partner", "slot_uid": haido.uid})
    assert [e["kind"] for e in snapshot(g, 0)["effects"]] == ["power_zero"]
    submit(g, {"type": "pass", "player": 0})
    submit(g, {"type": "pass", "player": 1})                             # 回合結束:本回合的效果到期
    assert g.state.turn_no == 2
    assert snapshot(g, 0)["effects"] == []


# ================================================================ i18n 說明文字齊全

def _i18n():
    import json
    from pathlib import Path
    return json.loads((Path(__file__).resolve().parents[1] / "frontend/i18n/zh-TW.json").read_text(encoding="utf-8"))


def _engine_source():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "src/gash/engine"
    return "\n".join(p.read_text(encoding="utf-8") for p in root.rglob("*.py"))


def test_every_effect_kind_and_flag_has_i18n_text():
    """作用中效果清單的說明:程式中出現的待命 / 持續效果種類與限制旗標都有 i18n 文字。"""
    import re
    src, d = _engine_source(), _i18n()
    standby = set(re.findall(r'schedule_standby\([^)]*?kind="([a-z_]+)"', src, re.S))
    standby |= set(re.findall(r'kind: ClassVar\[str\] = "([a-z_]+)"', src))
    modifier = set(re.findall(r'add_modifier\([^)]*?kind="([a-z_]+)"', src, re.S))
    modifier |= {"power", "restriction"}                               # add_power / add_restriction
    flags = set(re.findall(r'^(?:NO_[A-Z_]+|MAMODO_LOCKED) = "([a-z_]+)"', src, re.M))
    assert len(standby) >= 8 and len(modifier) >= 11 and len(flags) >= 7
    missing = ([f"effect.standby.{k}" for k in standby] + [f"effect.modifier.{k}" for k in modifier - {"restriction"}]
               + [f"effect.restriction.{f}" for f in flags])
    assert [k for k in missing if k not in d] == []


def test_every_breakdown_kind_has_i18n_text():
    import re
    src = _engine_source()
    kinds = set(re.findall(r'_item\("([a-z_]+)"', src))
    kinds |= set(re.findall(r'add_spell_power\([^)]*?kind="([a-z_]+)"', src, re.S)) | {"spell_bonus"}  # 預設種類
    assert len(kinds) >= 12
    assert [k for k in kinds if f"breakdown.{k}" not in _i18n()] == []
