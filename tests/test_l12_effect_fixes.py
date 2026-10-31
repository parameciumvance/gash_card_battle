"""第 1、2 彈依日文效果文 / 卡頁 FAQ 修正的行為(l12-effect-fixes)。"""

import pytest

from gash.engine.effects import registry as reg
from gash.engine.effects.primitives import add_modifier
from gash.engine.engine import side_breakdown, submit
from gash.engine.state import DUR_BATTLE
from tests.test_level2 import HEADS, TAILS, Rng, book, mk, to_battle
from tests.test_level3 import (
    _protectors, ability, add_slot, attack, battle_in, choose, code, no_protect, pass_effects, use_event,
)


def showdown(g):
    return [e for e in g.events if e["type"] == "showdown"][-1]


# ---------------------------------------------------------------- M-001 / M-010 / M-017

def test_m017_usable_when_other_mamodo_attacks():
    # 《黒き魔物》MPを2へらす→【ステイ】自分が攻撃するバトル中、この魔物の魔力を+2000する
    g, _ = mk(book("M-001", "S-001"), book("M-001"))
    st = g.state
    st.players[0].mp = 10
    m017 = add_slot(g, 0, "M-017")
    to_battle(g, 0)
    attack(g, 2)                                                   # ガッシュ・ベル 以 ザケル 攻擊
    mp = st.players[0].mp
    submit(g, ability(0, m017))
    assert st.players[0].mp == mp - 2
    pass_effects(g)
    assert showdown(g)["attacker_total"] == 6000                   # M-017 沒有參與魔力勝負


def test_m001_rejected_in_opponent_attack():
    # 自分が攻撃するバトル中:對手攻擊的戰鬥不能使用
    g, _ = mk(book("M-001", "S-001"), book("M-001"))
    st = g.state
    st.players[0].mp = st.players[1].mp = 10
    to_battle(g, 0)
    attack(g, 2)
    submit(g, {"type": "pass", "player": 0})
    assert code(g, ability(1, st.players[1].slots[0])) == "ability.condition"


def test_m010_usable_when_other_mamodo_defends():
    # 《狂戦士》MPを1へらす→【ステイ】自分が防御するバトル中、この魔物の魔力を+1000する
    g, _ = mk(book("M-001", "S-001"), book("M-001", "S-003"))
    st = g.state
    st.players[0].mp = st.players[1].mp = 10
    korulu = add_slot(g, 1, "M-009", "M-010")
    to_battle(g, 0)
    attack(g, 2, defend_page=2)                                    # 對手以 ガッシュ・ベル 防禦
    submit(g, {"type": "pass", "player": 0})
    mp = st.players[1].mp
    submit(g, ability(1, korulu))
    assert st.players[1].mp == mp - 1
    pass_effects(g)
    assert showdown(g)["defender_total"] == 8000                   # 4000 + S-003 4000,M-010 沒有參與


# ---------------------------------------------------------------- M-005

def _m005_defending(book1):
    """玩家 0 以 ガッシュ・ベル 的ザケル(6000)攻擊,玩家 1 以第 2 頁的 S-003 防禦;停在玩家 1 的效果時機。"""
    g, _ = mk(book("M-001", "S-001"), book1)
    st = g.state
    st.players[0].mp = st.players[1].mp = 10
    to_battle(g, 0)
    attack(g, 2, defend_page=2)
    submit(g, {"type": "pass", "player": 0})
    return g


def _counter_damage(g):
    """雙方 pass 到魔力勝負,玩家 0 不保護;回傳玩家 0 的魔書被翻的張數。"""
    pos = g.state.players[0].pos
    pass_effects(g)
    no_protect(g)
    return g.state.players[0].pos - pos


def test_m005_usable_when_defending_with_other_spell():
    # 《孤高の戦士》MPを2へらす→【ステイ】このバトル中、この魔物の「魔物の効果」や術のダメージを1ふやす
    g = _m005_defending(book("M-001", "S-003"))
    st = g.state
    m005 = add_slot(g, 1, "M-005")
    mp = st.players[1].mp
    submit(g, ability(1, m005))
    assert st.players[1].mp == mp - 2
    assert _counter_damage(g) == 2 * 1                             # ガッシュ・ベル 的戰術:反擊傷害不變


def test_m005_counter_damage_plus_one(monkeypatch):
    # 名稱與 M-005 相同的魔物使用的反擊戰術:反擊傷害 +1。目前沒有 ブラゴ 的反擊戰術,
    # 以「視為ガッシュ・ベル」讓 M-005 能使用 S-003
    monkeypatch.setitem(reg.TREATED_AS, "M-005", "ガッシュ・ベル")
    g = _m005_defending(book("M-005", "S-003"))
    submit(g, ability(1, g.state.players[1].slots[0]))
    assert _counter_damage(g) == 2 * 2


# ---------------------------------------------------------------- M-031

@pytest.mark.parametrize("delta,immune", [(-1000, True), (0, False)])
def test_m031_counter_damage_by_defender_total(delta, immune):
    # 合計魔力6000以下の術のダメージを受けない:反擊以防禦方的合計魔力判斷
    g, _ = mk(book("M-009", "S-016"), book("M-037", "S-066"))
    st = g.state
    st.players[0].mp = st.players[1].mp = 10
    kyclops = add_slot(g, 0, "M-031")
    to_battle(g, 0)
    attack(g, 2, slot=st.players[0].slots[0], defend_page=2)       # コルル 3000 vs エシュロス 3500 + S-066 3000
    eshros = st.players[1].slots[0]
    add_modifier(g, [], kind="power", source="TEST", owner=1, duration=DUR_BATTLE,
                 target_player=1, target_slot=eshros.uid, amount=delta)
    pass_effects(g)
    assert showdown(g)["defender_total"] == 6500 + delta and showdown(g)["winner"] == "defender"
    assert st.pending.kind == "protect" and st.pending.player == 0
    choose(g, kyclops.uid)                                         # 以 M-031 保護魔書受到的反擊傷害
    assert kyclops.injured is (not immune)


# ---------------------------------------------------------------- 不能保護的範圍

def test_e013_mamodo_damage_cannot_be_protected():
    # 【スタンバイ】このターン中の次のバトル中、相手はダメージを魔物で「かばう」ことができない
    g, _ = mk(book("M-029", "E-013", "S-058"), book("M-001"))
    st = g.state
    st.players[0].mp = 10
    a = add_slot(g, 1, "M-002")
    to_battle(g, 0)
    use_event(g, 2)
    submit(g, {"type": "pass", "player": 1})
    battle_in(g, 3)
    assert st.pending.kind == "injure_instead_target"
    choose(g, a.uid)
    submit(g, {"type": "no_defense", "player": 1})
    pass_effects(g)
    assert st.pending is None and a.injured


def test_e013_user_can_protect_counter_damage():
    # 限制的是「相手」:使用者自己受到的反擊傷害可以保護
    g, _ = mk(book("M-001", "E-013", "S-001"), book("M-001", "S-003"))
    st = g.state
    st.players[0].mp = st.players[1].mp = 10
    add_slot(g, 0, "M-002")
    to_battle(g, 0)
    use_event(g, 2)
    submit(g, {"type": "pass", "player": 1})
    battle_in(g, 3)
    submit(g, {"type": "declare_defense", "player": 1, "page": 2})
    pass_effects(g)
    assert st.pending.kind == "protect" and st.pending.player == 0


def test_s035_damage_redirected_to_mamodo_cannot_be_protected():
    # この術のダメージを「かばう」ことができない:S-057 把傷害轉到魔物時也一樣
    g, _ = mk(book("M-005", "S-057", "S-035"), book("M-001"))
    st = g.state
    st.players[0].mp = 10
    a = add_slot(g, 1, "M-002")
    g.rng = Rng(HEADS, HEADS, HEADS)                               # S-057 正面;S-035 2 次正面
    to_battle(g, 0)
    submit(g, {"type": "use_book_card", "player": 0, "page": 2, "slot_uid": st.players[0].slots[0].uid})
    submit(g, {"type": "pass", "player": 1})
    battle_in(g, 3)
    assert st.pending.kind == "injure_instead_target"
    choose(g, a.uid)
    submit(g, {"type": "no_defense", "player": 1})
    pass_effects(g)
    assert st.pending is None and a.injured


def _hige_under(restrict_first):
    """玩家 1 的ゾボロン裝 P-027;玩家 0 先做 restrict_first(g),再以ザケル攻擊,
    玩家 1 使用 P-027 指定玩家 0 的 ガッシュ・ベル,雙方 pass 到傷害。"""
    g, _ = mk(book("M-001", "E-013", "S-001"), book("M-041"))
    st = g.state
    st.players[0].mp = st.players[1].mp = 10
    zoboron = st.players[1].slots[0]
    zoboron.partner = "P-027"
    to_battle(g, 0)
    restrict_first(g)
    battle_in(g, 3)
    submit(g, {"type": "no_defense", "player": 1})
    submit(g, {"type": "pass", "player": 0})
    submit(g, ability(1, zoboron, zone="partner"))                 # 只有一個對象:自動選擇
    pass_effects(g)
    return g


def test_p027_protector_blocked_by_e013():
    # 以對手的魔物保護也是「かばう」
    def use_e013(g):
        use_event(g, 2)
        submit(g, {"type": "pass", "player": 1})
    g = _hige_under(use_e013)
    assert g.state.pending is None


def test_p027_protector_blocked_by_p026():
    # P-026:その魔物以外の魔物で、ダメージを「かばう」ことができない
    def use_p026(g):
        st = g.state
        st.players[0].slots[0].partner = "P-026"
        submit(g, ability(0, st.players[0].slots[0], zone="partner"))   # 對手只有ゾボロン:自動選擇
        submit(g, {"type": "pass", "player": 1})
    g = _hige_under(use_p026)
    assert _protectors(g) == [g.state.players[1].slots[0].uid]


def test_p027_protector_allowed_by_e031():
    # E-031:自分は「かばうことができない」ときにも「かばう」ことができる
    g, _ = mk(book("M-043", "S-081"), book("M-041", "E-031"))
    st = g.state
    g.rng = Rng(HEADS)
    st.players[0].mp = st.players[1].mp = 10
    zoboron = st.players[1].slots[0]
    zoboron.partner = "P-027"
    to_battle(g, 0)
    submit(g, {"type": "pass", "player": 0})
    submit(g, {"type": "use_book_card", "player": 1, "page": 2})
    attack(g, 2)
    submit(g, {"type": "pass", "player": 0})
    submit(g, ability(1, zoboron, zone="partner"))
    pass_effects(g)
    assert set(_protectors(g)) == {zoboron.uid, st.players[0].slots[0].uid}


# ---------------------------------------------------------------- E-027

def test_e027_opponent_guarded_partner_not_discarded():
    # 卡頁 FAQ:「高貴なる魂」等で相手の効果によって捨て札にされないパートナーは捨て札にならない
    g, _ = mk(book("M-001", "E-027"), book("M-001"))
    st = g.state
    st.players[0].mp = 10
    keep = st.players[1].slots[0]
    keep.partner = "P-001"
    guarded = add_slot(g, 1, "M-049", partner="P-032")
    other = add_slot(g, 1, "M-002", partner="P-002")
    to_battle(g, 0)
    use_event(g, 2)
    assert st.pending.kind == "pick_partner_to_keep" and st.pending.player == 1
    choose(g, keep.uid)
    assert keep.partner == "P-001" and guarded.partner == "P-032" and other.partner is None


def test_e027_own_guarded_partner_discarded():
    # 自己的 E-027 是自己的效果:M-049 不阻止
    g, _ = mk(book("M-001", "E-027"), book("M-001"))
    st = g.state
    st.players[0].mp = 10
    keep = st.players[0].slots[0]
    keep.partner = "P-001"
    guarded = add_slot(g, 0, "M-049", partner="P-032")
    to_battle(g, 0)
    use_event(g, 2)
    assert st.pending.kind == "pick_partner_to_keep" and st.pending.player == 0
    choose(g, keep.uid)
    assert keep.partner == "P-001" and guarded.partner is None


# ---------------------------------------------------------------- S-040

@pytest.mark.parametrize("coins,power", [((HEADS, HEADS, TAILS), 4000), ((TAILS, TAILS, TAILS), 0)])
def test_s040_defense_power_per_heads(coins, power):
    # この術の魔力は、コインを3回投げて、オモテの数×2000となる
    g, _ = mk(book("M-001", "S-001"), book("M-023", "S-040"))
    st = g.state
    st.players[0].mp = st.players[1].mp = 10
    g.rng = Rng(*coins)
    to_battle(g, 0)
    attack(g, 2, defend_page=2)
    flips = [e for e in g.events if e["type"] == "coin_flipped" and e.get("source") == "S-040"]
    assert len(flips) == 3
    total, _ = side_breakdown(g, st.battle, "defense")
    assert total == 3000 + power


# ---------------------------------------------------------------- S-057

def test_s057_no_damage_spell_not_changed():
    # 卡頁 FAQ A2:本来相手にダメージを与える術でなければ、ダメージは与えられません
    g, _ = mk(book("M-019", "S-057", "S-020"), book("M-009"))
    st = g.state
    st.players[0].mp = 10
    st.players[1].mp = 5
    add_slot(g, 1, "M-002")
    g.rng = Rng(HEADS)
    to_battle(g, 0)
    submit(g, {"type": "use_book_card", "player": 0, "page": 2, "slot_uid": st.players[0].slots[0].uid})
    submit(g, {"type": "pass", "player": 1})
    battle_in(g, 3)
    assert st.pending is None                                      # 不詢問改傷害的對象
    submit(g, {"type": "no_defense", "player": 1})
    pass_effects(g)
    assert showdown(g)["winner"] == "attacker"
    assert st.pending is None and st.battle is None
    assert st.players[1].mp == 2
    assert not any(s.injured for s in st.players[1].slots)
