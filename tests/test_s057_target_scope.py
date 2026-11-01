"""S-057 只改變沒有指定對象的傷害效果(「相手の魔本にダメージ」)(card-effects「S-057 改變的傷害」)。"""

import pytest

from gash.engine.engine import spell_has_untargeted_damage, submit
from tests.test_level2 import DB, HEADS, TAILS, Rng, book, mk, to_battle
from tests.test_level3 import add_slot, battle_in, choose, finish_damage, pass_effects


def _after_s057(attacker_book, *coins, mp=20):
    """玩家 0 以第 2 頁的 S-057(擲出正面)排定待命;對手場上 M-001 與 M-002。回傳 (g, a, b)。"""
    g, _ = mk(book(attacker_book[0], "S-057", *attacker_book[1:]), book("M-001"))
    st = g.state
    st.players[0].mp = mp
    a = st.players[1].slots[0]
    b = add_slot(g, 1, "M-002")
    g.rng = Rng(HEADS, *coins)
    to_battle(g, 0)
    submit(g, {"type": "use_book_card", "player": 0, "page": 2, "slot_uid": st.players[0].slots[0].uid})
    submit(g, {"type": "pass", "player": 1})
    return g, a, b


@pytest.mark.parametrize("spell", ["S-036", "S-101"])
def test_all_mamodo_spells_not_changed(spell):
    # 「相手の魔本と、選んだ魔物すべてにダメージをあたえる」:已指定對象,S-057 不改變
    g, a, b = _after_s057(("M-005", spell))
    st = g.state
    pos = st.players[1].pos
    battle_in(g, 3)
    assert st.pending is None                                      # 不詢問 S-057 的對象
    submit(g, {"type": "no_defense", "player": 1})
    pass_effects(g)
    finish_damage(g)
    assert a.injured and b.injured and st.players[1].pos == pos + 2 * 3


def test_s070_book_choice_not_changed():
    # 「次の効果の1つを使う」:選擇效果時已明確選了魔書
    g, a, b = _after_s057(("M-038", "S-070"))
    st = g.state
    pos = st.players[1].pos
    battle_in(g, 3)
    assert st.pending.kind == "pick_effect"                        # 先選效果,不先詢問 S-057 的對象
    choose(g, "book")
    assert st.pending is None
    submit(g, {"type": "no_defense", "player": 1})
    pass_effects(g)
    finish_damage(g)
    assert st.players[1].pos == pos + 2 * 2 and not a.injured and not b.injured


def test_s070_mamodo_choice_asks_once():
    g, a, b = _after_s057(("M-038", "S-070"))
    st = g.state
    battle_in(g, 3)
    assert st.pending.kind == "pick_effect"
    choose(g, "mamodo")
    assert st.pending.kind == "pick_opponent_mamodo"
    choose(g, b.uid)
    assert st.pending is None
    submit(g, {"type": "no_defense", "player": 1})
    pass_effects(g)
    finish_damage(g)
    assert b.injured and not a.injured


@pytest.mark.parametrize("coin,damaged", [(HEADS, True), (TAILS, False)])
def test_s069_heads_damages_chosen_mamodo(coin, damaged):
    # 正面時「相手の魔本にダメージ」→ 改為傷害宣告時選定的魔物
    g, a, b = _after_s057(("M-038", "S-069"), coin)
    st = g.state
    pos = st.players[1].pos
    battle_in(g, 3)
    assert st.pending.kind == "injure_instead_target"
    choose(g, b.uid)
    submit(g, {"type": "no_defense", "player": 1})
    pass_effects(g)
    finish_damage(g)
    assert st.battle is None
    assert b.injured is damaged and not a.injured and st.players[1].pos == pos


def test_standby_used_up_by_unaffected_spell():
    # 「このターン中の次のバトル」:第一場不適用,第二場也不再改變
    g, a, b = _after_s057(("M-005", "S-036", "S-008"))
    st = g.state
    battle_in(g, 3)
    submit(g, {"type": "no_defense", "player": 1})
    pass_effects(g)
    finish_damage(g)
    pos = st.players[1].pos
    st.players[0].pos += 2                                         # 翻開第 4 頁的 S-008
    battle_in(g, 4)
    assert st.pending is None
    submit(g, {"type": "no_defense", "player": 1})
    pass_effects(g)
    finish_damage(g)
    assert st.players[1].pos == pos + 2 * 2


def test_unaffected_attack_spells_are_target_specified():
    # 有「ダメージ」的戰術中,S-057 不改變的只有已指定對象的(名單變動時要確認效果文)
    from gash.engine.effects import registry as reg
    unaffected = sorted(
        n for n, c in DB.items()
        if c.type == "spell" and "ダメージ" in (c.effect_ja or "") and "ダメージを" in (c.effect_ja or "")
        and not spell_has_untargeted_damage(c) and not c.is_command_spell
        and not (reg.SPELL_RIDERS.get(n) and reg.SPELL_RIDERS[n].no_book_damage)
        and ("あたえる" in c.effect_ja or "相手の魔本にダメージ" in c.effect_ja))
    assert unaffected == ["S-036", "S-058", "S-064", "S-070", "S-101"]
