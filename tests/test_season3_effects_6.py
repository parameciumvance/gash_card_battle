"""第 3 賽季效果第 6 批:M-058(相手の捨て札のパートナーを借りる;この魔物の術を使えない)與場上卡片的持有者。"""

import pytest

from gash.engine.engine import submit
from gash.engine.state import NO_MAMODO_EFFECTS
from tests.test_level2 import HEADS, Rng, book, mk, to_battle
from tests.test_level3 import ability, add_slot, attack, choose, code, events_of, restrict

BATCH = ["M-058"]


def _m058(*extra, mp=10, opp_discard=("P-002", "P-041"), book1=("M-001",)):
    """玩家 0 場上 M-058;玩家 1 捨て札有搭檔卡。"""
    g, _ = mk(book("M-058", *extra), book(*book1))
    st = g.state
    st.players[0].mp = mp
    st.players[1].discard = list(opp_discard)
    to_battle(g, 0)
    return g


def umagon(g, player=0):
    return next(s for s in g.state.players[player].slots if s.top == "M-058")


def opp_pass(g, player=1):
    submit(g, {"type": "pass", "player": player})


def borrow(g, card="P-002", player=0):
    """以 M-058 使用《ポクポクポク》,選對手捨て札的 card。"""
    st = g.state
    events = submit(g, ability(player, umagon(g, player)))
    if st.pending is None:                                    # 只有一個選項時自動選
        assert umagon(g, player).partner == card
        return events
    assert st.pending.kind == "pick_partner_in_discard" and st.pending.player == player
    opt = next(o for o in st.pending.options if o.get("card") == card)
    return choose(g, opt["value"])


# ---------------------------------------------------------------- 《ポクポクポク》

def test_m058_attaches_opponent_discarded_partner():
    # MPを3へらす→相手の捨て札のパートナーカード1枚を選び、この魔物につける(「カフカ・サンビーム」でなくても)
    g = _m058()
    st = g.state
    submit(g, ability(0, umagon(g)))
    assert st.players[0].mp == 7
    assert {o.get("card") for o in st.pending.options if o["value"] is not None} == {"P-002", "P-041"}
    opt = next(o for o in st.pending.options if o.get("card") == "P-002")
    choose(g, opt["value"])
    assert umagon(g).partner == "P-002"                     # P-002 對應レイコム,不需對應魔物
    assert st.players[1].discard == ["P-041"]


def test_m058_rejected_with_partner():
    g = _m058()
    umagon(g).partner = "P-031"
    assert code(g, ability(0, umagon(g))) == "ability.condition"


def test_m058_rejected_without_opponent_partner():
    g = _m058(opp_discard=("S-001", "M-002"))
    assert code(g, ability(0, umagon(g))) == "ability.condition"


def test_m058_rejected_without_mp():
    g = _m058(mp=2)
    assert code(g, ability(0, umagon(g))) == "ability.mp"


def test_m058_rejected_in_battle():
    g = _m058("S-001")
    gash = add_slot(g, 0, "M-001")
    attack(g, 2, slot=gash)
    assert code(g, ability(0, umagon(g))) == "ability.timing"


def test_m058_once_per_turn():
    g = _m058()
    borrow(g)
    opp_pass(g)
    submit(g, ability(0, umagon(g), zone="partner"))       # 借來的 P-002 以代價棄掉,M-058 又沒有搭檔
    assert umagon(g).partner is None
    opp_pass(g)
    assert code(g, ability(0, umagon(g))) == "ability.used"


def test_m058_borrowed_partner_effect_is_own():
    # そのパートナーの効果は、自分のものとして使える:P-002「相手のMPを3へらす…自分のMPをふやす」
    g = _m058()
    st = g.state
    st.players[1].mp = 5
    borrow(g)
    opp_pass(g)
    submit(g, ability(0, umagon(g), zone="partner"))
    assert st.players[0].mp == 7 + 3 and st.players[1].mp == 2


# ---------------------------------------------------------------- 借來的搭檔進持有者的捨て札

def test_borrowed_partner_cost_discard_goes_to_owner():
    # そのパートナーは相手の捨て札に捨て
    g = _m058()
    st = g.state
    borrow(g)
    opp_pass(g)
    events = submit(g, ability(0, umagon(g), zone="partner"))
    assert "P-002" in st.players[1].discard and "P-002" not in st.players[0].discard
    assert "P-002" in st.players[1].discarded_this_turn
    ev = [e for e in events_of(events, "card_discarded") if e["card"] == "P-002"][0]
    assert ev["player"] == 0 and ev["owner"] == 1


def test_borrowed_partner_action_discard_goes_to_owner():
    # P-041「1アクションを使って、このカードを捨て札にできる」
    g = _m058()
    st = g.state
    borrow(g, "P-041")
    opp_pass(g)
    submit(g, {"type": "use_action_effect", "player": 0, "zone": "partner", "slot_uid": umagon(g).uid})
    assert "P-041" in st.players[1].discard and "P-041" not in st.players[0].discard


def _turn_player_lends(event, mamodo="M-001"):
    """玩家 1 場上 M-058,借走回合玩家 0 捨て札的 P-002;玩家 0 第 2 頁為 event。"""
    g, _ = mk(book(mamodo, event), book("M-058"))
    st = g.state
    st.players[0].mp = st.players[1].mp = 10
    st.players[0].discard = ["P-002"]
    to_battle(g, 0)
    opp_pass(g, 0)
    borrow(g, player=1)
    return g


def test_borrowed_partner_discarded_by_effect_goes_to_owner():
    # 回合玩家以 E-030(相手の場のパートナー1枚を選び、捨て札にする)棄掉被借走的搭檔 → 回到自己的捨て札
    g = _turn_player_lends("E-030")
    st = g.state
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    if st.pending is not None:
        choose(g, umagon(g, 1).uid)
    assert umagon(g, 1).partner is None
    assert "P-002" in st.players[0].discard and "P-002" not in st.players[1].discard


def test_borrowed_partner_follows_mamodo_to_owner_discard():
    from gash.engine.engine import _discard_slot
    g = _m058()
    st = g.state
    borrow(g)
    _discard_slot(g, [], 0, umagon(g), reason="test")
    assert "M-058" in st.players[0].discard and "P-002" not in st.players[0].discard
    assert "P-002" in st.players[1].discard


def test_owner_can_retrieve_with_e022():
    # 算持有者本回合入墓:借用者以代價棄掉後,持有者 E-022 擲得正面可以取回(持有者場上有對應的レイコム)
    g = _turn_player_lends("E-022", mamodo="M-004")
    st = g.state
    opp_pass(g, 0)
    submit(g, ability(1, umagon(g, 1), zone="partner"))
    assert "P-002" in st.players[0].discarded_this_turn
    g.rng = Rng(HEADS)
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    while st.pending is not None:
        opt = next(o for o in st.pending.options if o["value"] is not None)
        choose(g, opt["value"])
    assert st.players[0].slots[0].partner == "P-002"


def test_snapshot_shows_partner_owner():
    # battle-ui「借來的搭檔標記」:快照帶持有者,雙方看到的相同
    from gash.api.views import snapshot
    g = _m058()
    borrow(g)
    for viewer in (0, 1):
        slot = snapshot(g, viewer)["players"][0]["slots"][0]
        assert slot["partner"] == "P-002" and slot["partner_owner"] == 1


# ---------------------------------------------------------------- 自分は、この魔物の術を使えない

def test_m058_cannot_use_umagon_spell():
    g = _m058("S-087")
    assert code(g, {"type": "declare_attack", "player": 0, "page": 2, "slot_uid": umagon(g).uid}) == "spell.restricted"


def _defend_with(m058_defends):
    """玩家 1 場上 M-058 與 M-001;玩家 0 以 S-001 攻擊,玩家 1 以 S-028(指令戰術)防禦。"""
    g, _ = mk(book("M-001", "S-001"), book("M-058", "S-028"))
    st = g.state
    st.players[0].mp = st.players[1].mp = 10
    gash = add_slot(g, 1, "M-001")
    to_battle(g, 0)
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    slot = umagon(g, 1) if m058_defends else gash
    return g, {"type": "declare_defense", "player": 1, "page": 2, "slot_uid": slot.uid}


def test_m058_can_use_command_spell():
    # 「この魔物の術」= ウマゴン的戰術;指令戰術不屬於任何魔物,M-058 可以使用(spell-ownership-literal;
    # 與 atwiki 卡頁評論「コマンドの術は、使用することができる」一致)
    g, cmd = _defend_with(True)
    submit(g, cmd)
    assert g.state.battle.defense_spell == "S-028"


def test_other_mamodo_can_use_command_spell():
    g, cmd = _defend_with(False)
    submit(g, cmd)
    assert g.state.battle.defense_spell == "S-028"


def test_m058_rule_survives_mamodo_effect_block():
    # 卡片規則:「魔物の効果を使えない」時仍不能使用ウマゴン的戰術
    g = _m058("S-087")
    restrict(g, 0, NO_MAMODO_EFFECTS)
    assert code(g, {"type": "declare_attack", "player": 0, "page": 2, "slot_uid": umagon(g).uid}) == "spell.restricted"


# ---------------------------------------------------------------- NPC 自我對戰

SELFPLAY_BOOKS = (
    ("M-058", "P-002", "S-001", "E-030", "M-001", "S-028", "P-001", "S-002", "E-032", "S-001", "P-008",
     "S-029", "E-018", "S-002", "S-001", "E-032", "S-029", "S-002", "E-018", "S-001", "S-029", "E-032",
     "S-002", "S-001", "S-029", "E-018", "S-002", "S-001", "E-032", "S-029", "S-002", "S-005"),
    ("M-004", "P-002", "S-001", "P-008", "M-001", "P-001", "E-030", "S-002", "E-032", "S-001", "P-001",
     "S-029", "E-018", "S-002", "S-001", "E-032", "S-029", "S-002", "E-018", "S-001", "S-029", "E-032",
     "S-002", "S-001", "S-029", "E-018", "S-002", "S-001", "E-032", "S-029", "S-002", "S-005"),
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
