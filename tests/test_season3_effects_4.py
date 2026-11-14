"""第 3 賽季效果第 4 批:Ex-026、P-039(硬幣)、P-037、Ex-037、PR-006(從任意頁使用)、PR-001(費用 0)、P-041(對手回翻時)。"""

import pytest

from gash.engine.engine import side_breakdown, submit
from gash.engine.state import NO_PARTNER_EFFECTS
from tests.test_level2 import HEADS, TAILS, Rng, book, mk, to_battle
from tests.test_level3 import (
    ability, add_slot, attack, battle_in, choose, code, pass_effects, restrict, use_event,
)


BATCH = ["Ex-026", "Ex-037", "P-037", "P-039", "P-041", "PR-001", "PR-006"]


def showdown(g):
    return [e for e in g.events if e["type"] == "showdown"][-1]


def option_values(g):
    return [o["value"] for o in g.state.pending.options]


def coin_flips(g, source):
    return [e for e in g.events if e["type"] == "coin_flipped" and e.get("source") == source]


# ---------------------------------------------------------------- Ex-026 / P-039

def _s094(first, mp=10, coins=(TAILS,)):
    """玩家 0 以 first 為第 1 頁魔物,使用第 2 頁的 S-094(キャンチョメ,擲 1 次)。"""
    g, _ = mk(book(first, "S-094"), book("M-001"))
    st = g.state
    st.players[0].mp = mp
    g.rng = Rng(*coins)
    to_battle(g, 0)
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    return g


def test_ex026_reflip_pays_mp_twice_per_turn():
    # 《お調子者》MPを1へらす→自分が投げたコイン1個をふりなおす。この効果は1ターンに2回まで使える
    g = _s094("Ex-026", coins=(TAILS, TAILS, TAILS))
    st = g.state
    assert st.pending.kind == "coin_confirm" and "reflip:Ex-026:0" in option_values(g)
    mp = st.players[0].mp
    choose(g, "reflip:Ex-026:0")
    assert st.players[0].mp == mp - 1
    choose(g, "reflip:Ex-026:0")                                   # 第 2 次
    assert st.players[0].mp == mp - 2
    assert st.pending is None                                      # 第 3 次不再提供
    assert len(coin_flips(g, "S-094")) == 3


def test_ex026_not_offered_without_mp():
    g = _s094("Ex-026", mp=1)                                      # S-094 費用 1 付完後 MP 0
    assert g.state.pending is None


def test_ex026_and_m012_both_offered():
    g, _ = mk(book("Ex-026", "S-094"), book("M-001"))
    st = g.state
    add_slot(g, 0, "M-012")
    st.players[0].mp = 10
    g.rng = Rng(TAILS)
    to_battle(g, 0)
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    values = option_values(g)
    assert 0 in values and "reflip:Ex-026:0" in values
    assert {o["card"] for o in st.pending.options if o["value"] is not None} == {"M-012", "Ex-026"}


def _with_p039(restricted=False):
    g, _ = mk(book("M-019", "S-094"), book("M-001"))
    st = g.state
    st.players[0].slots[0].partner = "P-039"
    st.players[0].mp = 10
    g.rng = Rng(TAILS)
    to_battle(g, 0)
    if restricted:
        restrict(g, 0, NO_PARTNER_EFFECTS)
    pos = st.players[1].pos
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    return g, pos


def test_p039_sets_own_coin_heads():
    # 《強運のパートナー》このカードを捨て札にする→自分が投げたコイン1個をオモテにする
    g, pos = _with_p039()
    st = g.state
    assert st.pending.kind == "coin_confirm" and "heads:P-039:0" in option_values(g)
    choose(g, "heads:P-039:0")
    assert st.players[0].slots[0].partner is None and "P-039" in st.players[0].discard
    while st.pending is not None and st.pending.kind == "protect":
        choose(g, None)
    assert st.players[1].pos == pos + 2                            # 正面:對手魔書受到 1 傷害


def test_p039_blocked_by_partner_restriction():
    g, _ = _with_p039(restricted=True)
    assert g.state.pending is None


# ---------------------------------------------------------------- P-037

def _p037(pos=32):
    """玩家 0 的ブラゴ(M-005)裝 P-037,魔書在 pos。第 8 頁 E-032、第 10 頁 S-008、第 12 頁 S-001、第 14 頁 S-057。"""
    g, _ = mk(book("M-005"), book("M-001"))
    st = g.state
    ps = st.players[0]
    for page, number in ((8, "E-032"), (10, "S-008"), (12, "S-001"), (14, "S-057"), (16, "E-038")):
        ps.book[page - 1] = number
    brago = ps.slots[0]
    brago.partner = "P-037"
    ps.mp = 20
    to_battle(g, 0)
    ps.pos = pos
    return g, brago


def test_p037_needs_last_page():
    # この効果は、自分の魔本が最後のページのとき使える
    g, brago = _p037(pos=20)
    assert code(g, ability(0, brago, zone="partner")) == "ability.condition"


def test_p037_event_from_other_page_once():
    # このターン中に１回、…最後のページ以外の好きなページにある「ブラゴ」の術1つか、イベントカード1枚を使うことができる
    g, brago = _p037()
    st = g.state
    assert code(g, {"type": "use_book_card", "player": 0, "page": 8}) == "page.not_open"
    submit(g, ability(0, brago, zone="partner"))
    submit(g, {"type": "pass", "player": 1})
    mp = st.players[0].mp
    submit(g, {"type": "use_book_card", "player": 0, "page": 8})
    assert st.players[0].mp == mp - 2 + 5
    submit(g, {"type": "pass", "player": 1})
    assert code(g, {"type": "use_book_card", "player": 0, "page": 16}) == "page.not_open"   # 合計 1 次


def test_p037_brago_spell_attack_from_other_page():
    g, brago = _p037()
    submit(g, ability(0, brago, zone="partner"))
    submit(g, {"type": "pass", "player": 1})
    battle_in(g, 10, slot=brago)
    assert g.state.battle is not None and g.state.battle.attack_spell == "S-008"


def test_p037_not_other_mamodo_spell():
    g, brago = _p037()
    add_slot(g, 0, "M-001")
    submit(g, ability(0, brago, zone="partner"))
    submit(g, {"type": "pass", "player": 1})
    assert code(g, {"type": "declare_attack", "player": 0, "page": 12}) == "page.not_open"


def test_p037_command_spell_not_brago_spell():
    # 「X の術」= 對應魔物為 X 的戰術(spell-ownership-literal):指令戰術不是「ブラゴ」の術,不能從其他頁使用
    g, brago = _p037()
    submit(g, ability(0, brago, zone="partner"))
    submit(g, {"type": "pass", "player": 1})
    g.rng = Rng(HEADS)
    assert code(g, {"type": "use_book_card", "player": 0, "page": 14, "slot_uid": brago.uid}) == "page.not_open"


# ---------------------------------------------------------------- Ex-037

def _ex037():
    g, _ = mk(book("M-001", "E-038"), book("M-001"))
    st = g.state
    ps = st.players[0]
    ps.book[9] = "E-032"
    kid = ps.slots[0]
    kid.partner = "Ex-037"
    ps.mp = 10
    to_battle(g, 0)
    return g, kid


def test_ex037_event_from_chosen_page_costs_one_more():
    # 自分の魔本の好きなページのイベントカード1枚を選ぶ。このターン中、自分はそのイベントカードを本来より1高いコストで使えるようになる
    g, kid = _ex037()
    st = g.state
    submit(g, ability(0, kid, zone="partner"))
    assert st.pending.kind == "pick_event_in_own_book" and st.pending.player == 0
    choose(g, 10)
    submit(g, {"type": "pass", "player": 1})
    mp = st.players[0].mp
    submit(g, {"type": "use_book_card", "player": 0, "page": 10})
    assert st.players[0].mp == mp - 3 + 5


def test_ex037_chosen_event_on_open_page_normal_cost():
    g, kid = _ex037()
    st = g.state
    submit(g, ability(0, kid, zone="partner"))
    choose(g, 2)                                                   # 翻開的頁上的 E-038(費用 0)
    submit(g, {"type": "pass", "player": 1})
    mp = st.players[0].mp
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    assert st.players[0].mp == mp


# ---------------------------------------------------------------- PR-001

def _pr001(*pages):
    g, _ = mk(book("PR-001", *pages), book("M-001"))
    st = g.state
    st.players[0].mp = 20
    to_battle(g, 0)
    pr001 = st.players[0].slots[0]
    submit(g, ability(0, pr001))
    submit(g, {"type": "pass", "player": 1})
    return g, pr001


def test_pr001_free_spell_when_chosen():
    # 《威風堂々》使用を宣言する→【スタンバイ】このターン中に1回、この魔物のコスト3までの術1つを、コスト0で使える
    g, pr001 = _pr001("S-029")                                     # S-029 費用 3
    st = g.state
    mp = st.players[0].mp
    submit(g, {"type": "declare_attack", "player": 0, "page": 2, "slot_uid": pr001.uid})
    assert st.pending.kind == "spell_free" and st.pending.source == "PR-001"   # 對話框的來源卡是 PR-001
    assert {o["label"] for o in st.pending.options} == {"spell_free_use", "skip"}
    choose(g, True)
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    assert st.players[0].mp == mp


def test_pr001_skip_keeps_standby():
    g, pr001 = _pr001("S-001", "S-002")
    st = g.state
    mp = st.players[0].mp
    submit(g, {"type": "declare_attack", "player": 0, "page": 2, "slot_uid": pr001.uid})
    choose(g, None)
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    assert st.players[0].mp == mp - 1
    submit(g, {"type": "no_defense", "player": 1})
    pass_effects(g)
    while st.pending is not None:
        choose(g, None)
    submit(g, {"type": "declare_attack", "player": 0, "page": 3, "slot_uid": pr001.uid})
    assert st.pending.kind == "spell_free"                     # 下一個符合條件的戰術再詢問


def test_pr001_cost_over_three_not_offered():
    g, pr001 = _pr001("S-005")                                     # 費用 6
    submit(g, {"type": "declare_attack", "player": 0, "page": 2, "slot_uid": pr001.uid})
    assert g.state.pending is None


def test_pr001_applies_to_another_gash_after_leaving():
    # 「この魔物の術」依名稱:PR-001 離場後,另一隻ガッシュ・ベル也適用
    g, pr001 = _pr001("S-001")
    st = g.state
    other = add_slot(g, 0, "M-001")
    st.players[0].slots.remove(pr001)
    submit(g, {"type": "declare_attack", "player": 0, "page": 2, "slot_uid": other.uid})
    assert st.pending.kind == "spell_free"


def test_pr001_nonbattle_spell():
    # 術1つ:非戰鬥戰術也算(PR-009 為ガッシュ・ベル的非戰鬥戰術,費用 3)
    g, pr001 = _pr001("PR-009")
    st = g.state
    mp = st.players[0].mp
    submit(g, {"type": "use_book_card", "player": 0, "page": 2, "slot_uid": pr001.uid})
    assert st.pending.kind == "spell_free"
    choose(g, True)
    assert st.players[0].mp == mp
    assert any(e["type"] == "book_card_used" and e["card"] == "PR-009" for e in g.events)


def test_pr001_once_per_game():
    g, pr001 = _pr001("S-001")
    st = g.state
    st.players[0].used_abilities.clear()
    assert code(g, ability(0, pr001)) == "ability.per_game"


# ---------------------------------------------------------------- PR-006

def _pr006():
    g, _ = mk(book("M-001", "PR-006"), book("M-001"))
    st = g.state
    ps = st.players[0]
    ps.book[11] = "S-001"
    ps.mp = 10
    to_battle(g, 0)
    submit(g, {"type": "use_book_card", "player": 0, "page": 2, "slot_uid": ps.slots[0].uid})
    submit(g, {"type": "pass", "player": 1})
    return g


def test_pr006_attack_from_any_page_with_bonus():
    # 次のバトルで、自分の魔本の好きなページから術を使うことができ、そのバトル中、その術の魔力は+3000、ダメージは+1
    g = _pr006()
    st = g.state
    pos = st.players[1].pos
    battle_in(g, 12)
    submit(g, {"type": "no_defense", "player": 1})
    pass_effects(g)
    assert showdown(g)["attacker_total"] == 4000 + 2000 + 3000
    while st.pending is not None:
        choose(g, None)
    assert st.players[1].pos == pos + 2 * 2


def test_pr006_open_page_also_boosted():
    g = _pr006()
    g.state.players[0].book[2] = "S-001"
    battle_in(g, 3)
    total, _ = side_breakdown(g, g.state.battle, "attack")
    assert total == 4000 + 2000 + 3000


def test_pr006_not_usable_for_nonbattle_spell():
    g = _pr006()
    g.state.players[0].book[11] = "PR-009"
    assert code(g, {"type": "use_book_card", "player": 0, "page": 12,
                    "slot_uid": g.state.players[0].slots[0].uid}) == "page.not_open"


# ---------------------------------------------------------------- P-041

def _p041(opp_pos=6):
    """玩家 0 的魔物裝 P-041;玩家 1 的魔物裝 P-018(回翻自己的魔書 1 張),魔書在 opp_pos。"""
    g, _ = mk(book("M-045"), book("M-001"))
    st = g.state
    st.players[0].slots[0].partner = "P-041"
    holder = st.players[1].slots[0]
    holder.partner = "P-018"
    other = add_slot(g, 1, "M-002")
    to_battle(g, 0)
    st.players[1].pos = opp_pos
    submit(g, {"type": "pass", "player": 0})
    return g, holder, other


def test_p041_choose_mamodo_damage_after_turn_back():
    # 相手が相手自身の魔本をもどす効果をつかうたびに、次の効果の１つを使う(ダメージなので、「かばう」ことができる)
    g, holder, other = _p041()
    st = g.state
    submit(g, ability(1, holder, zone="partner"))
    assert st.players[1].pos == 4
    assert st.pending.kind == "pick_effect" and st.pending.player == 0
    choose(g, "mamodo")
    choose(g, other.uid)
    assert st.pending.kind == "protect" and st.pending.player == 1   # 可以保護
    choose(g, None)
    assert other.injured


def test_p041_book_damage():
    g, holder, _ = _p041()
    st = g.state
    submit(g, ability(1, holder, zone="partner"))
    choose(g, "book")
    while st.pending is not None and st.pending.kind == "protect":
        choose(g, None)
    assert st.players[1].pos == 4 + 2


def test_p041_no_trigger_when_nothing_turned_back():
    g, holder, _ = _p041(opp_pos=0)                                # 第 1 頁:回翻 0 張
    submit(g, ability(1, holder, zone="partner"))
    assert g.state.pending is None


def test_p041_action_discard():
    # ※１アクションを使って、このカードを捨て札にできる
    g, _ = mk(book("M-045"), book("M-001"))
    st = g.state
    slot = st.players[0].slots[0]
    slot.partner = "P-041"
    to_battle(g, 0)
    submit(g, {"type": "use_action_effect", "player": 0, "zone": "partner", "slot_uid": slot.uid})
    assert slot.partner is None and "P-041" in st.players[0].discard


# ---------------------------------------------------------------- NPC 自我對戰

SELFPLAY_BOOKS = (
    ("Ex-026", "S-094", "P-039", "PR-001", "S-001", "S-093", "E-005", "PR-006", "M-012", "S-002", "PR-007",
     "S-029", "E-032", "S-094", "M-001", "S-001", "P-001", "S-002", "E-005", "S-029", "PR-007", "S-093",
     "E-038", "S-001", "PR-006", "S-002", "E-032", "S-029", "S-001", "S-094", "S-002", "S-005"),
    ("M-005", "S-008", "P-037", "M-045", "P-041", "Ex-032", "Ex-037", "S-009", "E-032", "S-010", "M-033",
     "E-005", "S-008", "PR-007", "S-034", "E-038", "S-009", "S-008", "S-033", "E-032", "S-010", "S-032",
     "S-009", "E-005", "S-034", "S-008", "S-033", "S-011", "S-035", "E-038", "S-009", "S-101"),
)


def test_selfplay_books_cover_batch():
    assert all(len(b) == 32 for b in SELFPLAY_BOOKS)
    assert set(BATCH) <= set(SELFPLAY_BOOKS[0]) | set(SELFPLAY_BOOKS[1])


@pytest.mark.slow
@pytest.mark.parametrize("levels", [("normal", "normal"), ("normal", "dummy"), ("dummy", "normal")])
@pytest.mark.parametrize("seed", [1, 2, 3])
def test_npc_selfplay_with_batch_cards(levels, seed):
    import random

    from gash import npc
    from gash.engine.awaiting import awaited_player
    from gash.engine.engine import new_game
    from gash.engine.state import GAME_OVER
    books = [list(b) for b in SELFPLAY_BOOKS]
    g = new_game(books[0], seed=seed, decks=(books[0], books[1]))
    rngs = [random.Random(f"{seed}:{p}") for p in (0, 1)]
    for _ in range(3000):
        if g.state.phase == GAME_OVER:
            break
        p = awaited_player(g)
        assert npc.submit_ranked(g, p, npc.decide(g, p, levels[p], rngs[p])) is not None
    assert g.state.phase == GAME_OVER


def test_p037_any_page_list_only_brago_spells_and_events():
    # 畫面列出的可用卡:「ブラゴ」の術(只看所屬,不含指令戰術)與事件卡;其他魔物的戰術不列
    from gash.api.views import _any_page_spells
    g, brago = _p037()
    submit(g, ability(0, brago, zone="partner"))
    listed = {e["card"] for e in _any_page_spells(g, 0)}
    assert {"E-032", "S-008", "E-038"} <= listed
    assert "S-001" not in listed and "S-057" not in listed
