"""防禦效果於「効果の使用」的最後解決(game-engine「戰鬥流程五步驟」、card-effects「攻防效果的宣告時確定」)。

規則頁「バトル」:②防御「防御の効果はここではまだ解決しません」;「攻撃や防御の無効化」
「攻撃や防御のタイミングで使われた効果は無効になります」。擲幣在宣告時(※重要),效果在雙方都 pass、
魔力勝負前才解決;防禦已被無效時不解決。
"""
import pytest

from gash.api.views import snapshot
from gash.engine.engine import submit
from tests.test_level2 import HEADS, TAILS, Rng, book, mk, to_battle
from tests.test_level3 import ability, add_slot, attack, no_protect, pass_effects

# (防禦戰術, 防方魔物, 硬幣)
NEGATORS = [("S-025", "M-001", (HEADS,)), ("S-069", "M-038", (HEADS,)), ("S-106", "M-052", ())]


def _battle(spell, mamodo, coins, attacker_partner=None, defender_partner=None):
    """玩家 0 以 S-005(+6000 / 傷害 3)攻擊,玩家 1 以 spell 防禦;停在戰鬥中效果的時機。"""
    g, _ = mk(book("M-001", "S-005"), book(mamodo, spell))
    st = g.state
    g.rng = Rng(*coins)
    if attacker_partner:
        st.players[0].slots[0].partner = attacker_partner
    if defender_partner:
        st.players[1].slots[0].partner = defender_partner
    st.players[0].mp, st.players[1].mp = 10, 10
    to_battle(g, 0)
    attack(g, 2, defend_page=2)
    assert st.pending is None and st.battle.step == "effects"
    return g


def negations(g, source):
    return [e for e in g.events if e["type"] == "attack_negated" and e.get("source") == source]


def own_page_turns(g, source):
    return [e for e in g.events if e["type"] == "pages_turned" and e.get("source") == source]


def negate_defense(g):
    """攻方以 P-017 使防禦無效。"""
    submit(g, ability(0, g.state.players[0].slots[0], zone="partner"))
    assert g.state.battle.defense_negated


@pytest.mark.parametrize("spell, mamodo, coins", NEGATORS)
def test_attack_negated_only_at_end_of_effects_step(spell, mamodo, coins):
    g = _battle(spell, mamodo, coins)
    st = g.state
    pos1 = st.players[1].pos
    assert not st.battle.attack_negated and not negations(g, spell)          # 戰鬥中效果的時機期間仍有效
    assert not own_page_turns(g, spell) and st.players[1].pos == pos1        # S-106 還沒翻
    assert not st.standby and not [e for e in snapshot(g, 0)["effects"] if e["source"] == spell]   # 不是【スタンバイ】
    pass_effects(g)
    assert negations(g, spell) and st.battle is None
    if spell == "S-106":
        assert st.players[1].pos == pos1 + 2                                 # 自分の魔本を1枚めくる


@pytest.mark.parametrize("spell, mamodo, coins", NEGATORS)
def test_negated_defense_does_not_negate_attack(spell, mamodo, coins):
    g = _battle(spell, mamodo, coins, attacker_partner="P-017")
    st = g.state
    pos1 = st.players[1].pos
    negate_defense(g)
    pass_effects(g)
    no_protect(g)
    assert not negations(g, spell) and not own_page_turns(g, spell)
    assert st.players[1].pos == pos1 + 2 * 3                                 # 攻擊成功,傷害 3


def test_s027_negated_defense_does_not_reduce_damage():
    g = _battle("S-027", "M-001", (HEADS, HEADS), attacker_partner="P-017")
    st = g.state
    pos1 = st.players[1].pos
    negate_defense(g)
    pass_effects(g)
    no_protect(g)
    assert st.players[1].pos == pos1 + 2 * 3


def test_s027_reduces_damage_at_end_of_effects_step():
    g = _battle("S-027", "M-001", (HEADS, TAILS))
    st = g.state
    pos1 = st.players[1].pos
    assert not st.standby                                                    # 不是【スタンバイ】
    pass_effects(g)
    no_protect(g)
    assert st.players[1].pos == pos1 + 2 * 2                                 # 3 - 1


def test_s027_tails_no_reduction():
    g = _battle("S-027", "M-001", (TAILS, TAILS))
    st = g.state
    pos1 = st.players[1].pos
    pass_effects(g)
    no_protect(g)
    assert st.players[1].pos == pos1 + 2 * 3


def test_s079_negated_defense_wonrei_takes_damage():
    g = _battle("S-079", "M-042", (), attacker_partner="P-017")
    st = g.state
    wonrei = st.players[1].slots[0]
    add_slot(g, 1, "M-002")
    negate_defense(g)
    pass_effects(g)
    submit(g, {"type": "choose", "player": 1, "value": wonrei.uid})
    assert wonrei.injured


def test_s106_no_page_turn_when_attack_already_negated():
    # 「そうしたなら」:攻擊在「効果の使用」中已被防方的 P-016 無效,S-106 沒有使它無效,不翻魔書
    g = _battle("S-106", "M-052", (), defender_partner="P-016")
    st = g.state
    pos1 = st.players[1].pos
    submit(g, {"type": "pass", "player": 0})
    submit(g, ability(1, st.players[1].slots[0], zone="partner"))
    assert st.battle.attack_negated and negations(g, "P-016")
    pass_effects(g)
    assert st.battle is None and not negations(g, "S-106") and not own_page_turns(g, "S-106")
    assert st.players[1].pos == pos1
