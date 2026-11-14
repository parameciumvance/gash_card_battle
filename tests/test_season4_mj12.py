"""第 4 賽季 MJ12:獨立卡區的放出與效果(game-engine「獨立卡區與 MJ12」),
MJ-001~006 與 Ex-074 的效果(card-effects)。依日文效果文與 atwiki 規則頁、卡頁 FAQ。"""

import pytest

from gash.engine.cards import pending_cards
from gash.engine.engine import side_breakdown, submit
from gash.engine.state import DUR_TURN, NO_MAMODO_EFFECTS, NO_PARTNER_EFFECTS, FieldCard, Modifier
from tests.test_level2 import book, mk, to_battle
from tests.test_level3 import ability, add_slot, choose, code, finish_damage, restrict, use_event

BATCH = ("MJ-001", "MJ-002", "MJ-003", "MJ-004", "MJ-005", "MJ-006", "Ex-074")


def game(p0=(), p1=(), mp0=10, mp1=10):
    """玩家 0、1 的 P1 都是 M-001(準備階段上場),之後的頁依序為 p0 / p1;進入玩家 0 的戰鬥階段。"""
    g, _ = mk(book("M-001", *p0), book("M-001", *p1))
    st = g.state
    st.players[0].mp, st.players[1].mp = mp0, mp1
    to_battle(g, 0)
    return g


def play(g, player, page):
    return submit(g, {"type": "play_card", "player": player, "page": page})


def put(g, player, *cards):
    """直接把卡放進獨立卡區(測試用)。"""
    out = []
    for card in cards:
        fc = FieldCard(uid=g.state.next_uid(), card=card)
        g.state.players[player].field_cards.append(fc)
        out.append(fc)
    return out[0] if len(out) == 1 else out


def field(g, player):
    return [f.card for f in g.state.players[player].field_cards]


def use(g, player, card):
    fc = next(f for f in g.state.players[player].field_cards if f.card == card)
    return submit(g, {"type": "use_field_ability", "player": player, "zone": "field", "field_uid": fc.uid})


def use_code(g, player, card):
    fc = next(f for f in g.state.players[player].field_cards if f.card == card)
    return code(g, {"type": "use_field_ability", "player": player, "zone": "field", "field_uid": fc.uid})


def opp_pass(g):
    submit(g, {"type": "pass", "player": 1})


def test_batch_cards_are_open():
    assert not set(BATCH) & pending_cards()


# ---------------------------------------------------------------- 放出

def test_play_mj12_into_field_zone():
    g = game(("MJ-004",))
    st = g.state
    events = play(g, 0, 2)
    assert field(g, 0) == ["MJ-004"]
    assert 2 in st.players[0].consumed_pages                                   # 離開魔書
    assert len(st.players[0].slots) == 1                                       # 不佔魔物欄
    ev = next(e for e in events if e["type"] == "card_played")
    assert ev["zone"] == "field" and ev["field_uid"] == st.players[0].field_cards[0].uid


def test_play_mj12_in_opponent_turn():
    # 自分か相手のバトルフェイズに魔本から場に出せます
    g = game(p1=("MJ-004",))
    submit(g, {"type": "pass", "player": 0})
    play(g, 1, 2)
    assert field(g, 1) == ["MJ-004"]


def test_play_any_number_of_different_mj12():
    g = game(("MJ-001", "MJ-004"))
    play(g, 0, 2)
    opp_pass(g)
    play(g, 0, 3)
    assert field(g, 0) == ["MJ-001", "MJ-004"]


def test_same_name_mj12_rejected():
    g = game(("MJ-001",))
    put(g, 0, "MJ-001")
    assert code(g, {"type": "play_card", "player": 0, "page": 2}) == "play.same_name"


def test_mj12_cannot_be_played_in_battle():
    g = game(("S-001", "MJ-004"))
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    submit(g, {"type": "no_defense", "player": 1})
    assert code(g, {"type": "play_card", "player": 0, "page": 3}) == "battle.invalid"


# ---------------------------------------------------------------- 場上效果的共通規則

def test_effect_once_per_turn():
    g = game()
    put(g, 0, "MJ-004")
    use(g, 0, "MJ-004")
    opp_pass(g)
    assert use_code(g, 0, "MJ-004") == "ability.used"


def test_effect_not_in_battle():
    g = game(("S-001",))
    put(g, 0, "MJ-004")
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    submit(g, {"type": "no_defense", "player": 1})
    assert use_code(g, 0, "MJ-004") == "ability.timing"


def test_effect_in_opponent_turn():
    g = game()
    put(g, 1, "MJ-004")
    submit(g, {"type": "pass", "player": 0})
    use(g, 1, "MJ-004")
    assert g.state.players[1].mp == 9


def test_effect_not_blocked_by_mamodo_or_partner_restrictions():
    g = game()
    put(g, 0, "MJ-004")
    restrict(g, 0, NO_MAMODO_EFFECTS)
    restrict(g, 0, NO_PARTNER_EFFECTS)
    use(g, 0, "MJ-004")
    assert g.state.players[0].mp == 9


def test_discard_cost_moves_card_to_discard():
    g = game()
    put(g, 0, "MJ-001")
    events = use(g, 0, "MJ-001")
    finish_damage(g)
    assert field(g, 0) == [] and g.state.players[0].discard[-1] == "MJ-001"
    ev = next(e for e in events if e["type"] == "card_discarded")
    assert ev["zone"] == "field" and "field_uid" in ev


def test_wrong_field_uid_rejected():
    g = game()
    assert code(g, {"type": "use_field_ability", "player": 0, "zone": "field", "field_uid": 999}) == "ability.target"


# ---------------------------------------------------------------- MJ-001

def test_mj001_damages_opponent_book():
    # このカードを捨て札にする→相手の魔本に1ダメージ(ダメージなので「かばう」ことができる)
    g = game()
    st = g.state
    put(g, 0, "MJ-001")
    pos = st.players[1].pos
    use(g, 0, "MJ-001")
    assert st.pending is not None and st.pending.kind == "protect" and st.pending.player == 1   # 可以保護
    finish_damage(g)
    assert st.players[1].pos == pos + 2


def test_mj001_once_per_turn_even_with_second_copy():
    # この効果は1ターンに1回しか使えない
    g = game(("MJ-001",))
    put(g, 0, "MJ-001")
    use(g, 0, "MJ-001")
    finish_damage(g)
    opp_pass(g)
    play(g, 0, 2)                                                              # 另一張 MJ-001
    opp_pass(g)
    assert use_code(g, 0, "MJ-001") == "ability.used"


# ---------------------------------------------------------------- MJ-002 / MJ-005

def _attack_total(g, page=None, mamodo_slot=None):
    st = g.state
    if mamodo_slot is not None:
        submit(g, {"type": "declare_attack", "player": 0, "mode": "mamodo", "slot_uid": mamodo_slot.uid})
    else:
        submit(g, {"type": "declare_attack", "player": 0, "page": page})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    submit(g, {"type": "no_defense", "player": 1})
    total, items = side_breakdown(g, st.battle, "attack")
    return total, items


def test_mj005_adds_to_spell_attack():
    # このカードを捨て札にする→【ステイ】このターン中、自分の攻撃すべての合計魔力を+2000する
    g = game(("S-001",))
    put(g, 0, "MJ-005")
    use(g, 0, "MJ-005")
    opp_pass(g)
    total, items = _attack_total(g, page=2)
    assert {"kind": "side_power", "source": "MJ-005", "amount": 2000} in items


def test_mj005_adds_to_mamodo_effect_attack():
    # FAQ:「魔物の効果」…等の格闘効果にも適用される
    g = game()
    put(g, 0, "MJ-005")
    danny = add_slot(g, 0, "M-039")
    use(g, 0, "MJ-005")
    opp_pass(g)
    total, items = _attack_total(g, mamodo_slot=danny)
    assert total == 6500 + 2000


def test_mj005_not_on_defense_and_ends_with_turn():
    g = game(p1=("S-001",))
    put(g, 0, "MJ-005")
    use(g, 0, "MJ-005")
    opp_pass(g)
    submit(g, {"type": "pass", "player": 0})                                   # 回合結束
    st = g.state
    assert not any(m.kind == "side_power" for m in st.modifiers)


def test_mj002_adds_to_defense_only():
    # 【ステイ】このターン中、自分の防御すべての合計魔力を+4000する(相手のターンの防御)
    g = game(("S-001",), ("S-029",))
    st = g.state
    put(g, 1, "MJ-002")
    submit(g, {"type": "pass", "player": 0})
    use(g, 1, "MJ-002")
    submit(g, {"type": "declare_attack", "player": 0, "page": 2})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    submit(g, {"type": "declare_defense", "player": 1, "page": 2})
    _, d_items = side_breakdown(g, st.battle, "defense")
    _, a_items = side_breakdown(g, st.battle, "attack")
    assert {"kind": "side_power", "source": "MJ-002", "amount": 4000} in d_items
    assert not any(i["kind"] == "side_power" for i in a_items)


# ---------------------------------------------------------------- MJ-003

def test_mj003_deploys_mamodo_from_any_page():
    # このカードを捨て札にする→自分の魔本の好きなページから、魔物カードかパートナーカード1枚を選び、場に出す
    g = game(("S-029", "S-029", "S-029", "S-029", "M-004", "M-008"))
    st = g.state
    put(g, 0, "MJ-003")
    use(g, 0, "MJ-003")
    assert field(g, 0) == [] and st.players[0].discard[-1] == "MJ-003"
    assert st.pending.player == 0 and st.pending.kind == "pick_card_in_own_book"
    pages = {o["page"] for o in st.pending.options}
    assert 6 in pages                                                          # M-004
    choose(g, next(o["value"] for o in st.pending.options if o["page"] == 6))
    assert [s.top for s in st.players[0].slots] == ["M-001", "M-004"]
    assert 6 in st.players[0].consumed_pages


def test_mj003_attaches_partner():
    g = game(("S-029", "S-029", "S-029", "S-029", "P-001", "M-004"))           # P-001 對應 M-001 (ガッシュ)
    st = g.state
    put(g, 0, "MJ-003")
    use(g, 0, "MJ-003")
    assert {o["page"] for o in st.pending.options} == {6, 7}                   # 魔物與搭檔一起列出,由使用者選
    choose(g, 6)                                                               # 裝備對象只有 1 隻:自動
    assert st.players[0].slots[0].partner == "P-001" and 6 in st.players[0].consumed_pages


def test_mj003_rejected_without_candidates():
    g = game()
    put(g, 0, "MJ-003")
    assert use_code(g, 0, "MJ-003") == "ability.condition"
    assert field(g, 0) == ["MJ-003"]


def test_mj003_illegal_choice_keeps_pending():
    g = game(("S-029", "S-029", "S-029", "S-029", "M-004", "M-008"))
    st = g.state
    put(g, 0, "MJ-003")
    use(g, 0, "MJ-003")
    assert code(g, {"type": "choose", "player": 0, "value": 999}) == "choose.invalid"
    assert st.pending is not None and st.pending.kind == "pick_card_in_own_book"


# ---------------------------------------------------------------- MJ-004

def test_mj004_peeks_opponent_pages():
    # MPを1へらす→相手の魔本の今のページを見る
    g = game(p1=("E-003", "S-029"))
    put(g, 0, "MJ-004")
    events = use(g, 0, "MJ-004")
    assert g.state.players[0].mp == 9
    peek = next(e for e in events if e["type"] == "pages_peeked")
    assert peek["viewer"] == 0 and [c["card"] for c in peek["cards"]] == ["E-003", "S-029"]
    assert field(g, 0) == ["MJ-004"]                                           # 不棄掉


def test_mj004_needs_mp():
    g = game(mp0=0)
    put(g, 0, "MJ-004")
    assert use_code(g, 0, "MJ-004") == "ability.mp"


# ---------------------------------------------------------------- MJ-006

def p002(g, player=0):
    return add_slot(g, player, "M-001", partner="P-002")


def test_mj006_reduces_opponent_mp_back():
    # このカードが場にある→相手の効果によって自分のMPがへらされたとき、へらされたMPの数だけ、相手のMPをへらす
    g = game(mp0=10, mp1=10)
    st = g.state
    put(g, 1, "MJ-006")
    slot = p002(g)
    events = use_field(g, slot)
    assert st.players[1].mp == 7                                               # P-002 -3
    assert st.players[0].mp == 10                                              # MJ-006 -3,P-002 +3
    assert any(e["type"] == "mp_changed" and e["player"] == 0 and e["reason"] == "MJ-006" for e in events)


def use_field(g, slot):
    return submit(g, ability(0, slot, zone="partner"))


def test_mj006_mirror_applies_once_each():
    # ※相手の場にも「ワンダフル・トゥ・ザ・フューチャー」があるとき、この効果はたがいに1回ずつ適用される
    g = game(mp0=20, mp1=20)
    st = g.state
    put(g, 0, "MJ-006")
    put(g, 1, "MJ-006")
    slot = p002(g)
    use_field(g, slot)
    assert st.players[1].mp == 20 - 3 - 3                                      # P-002、對方 MJ-006 的回應
    assert st.players[0].mp == 20 - 3 + 3                                      # 對手的 MJ-006、P-002 的增加


def test_mj006_respects_mp_guard():
    g = game(mp0=10, mp1=10)
    st = g.state
    put(g, 1, "MJ-006")
    st.modifiers.append(Modifier(kind="mp_guard", source="TEST", owner=0, duration=DUR_TURN,
                                 created_turn=st.turn_no, target_player=0))
    slot = p002(g)
    use_field(g, slot)
    assert st.players[0].mp == 13                                              # MJ-006 被擋,P-002 +3


def test_mj006_not_triggered_by_own_costs():
    g = game(mp0=10, mp1=10)
    put(g, 0, "MJ-006", "MJ-004")
    use(g, 0, "MJ-004")
    assert g.state.players[1].mp == 10


def test_mj006_triggers_on_e004_zeroing():
    # E-004 的歸零也算被對手的效果減少
    g = game(("E-004",), mp0=10, mp1=4)
    put(g, 1, "MJ-006")
    events = use_event(g)
    assert any(e["type"] == "field_card_effect" and e["card"] == "MJ-006" and e["player"] == 1
               and e["amount"] == 4 for e in events)


# ---------------------------------------------------------------- Ex-074

def test_ex074_discards_chosen_opponent_mj12():
    # 相手の場のMJ12カード1枚を選び、捨て札にする
    g = game(("Ex-074",))
    st = g.state
    put(g, 1, "MJ-001", "MJ-006")
    use_event(g)
    assert st.pending.player == 0 and st.pending.kind == "pick_opponent_field_card"
    opts = st.pending.options
    assert {o["card"] for o in opts} == {"MJ-001", "MJ-006"} and all(o["zone"] == "field" for o in opts)
    choose(g, next(o["value"] for o in opts if o["card"] == "MJ-006"))
    assert field(g, 1) == ["MJ-001"] and st.players[1].discard[-1] == "MJ-006"


def test_ex074_rejected_without_opponent_mj12():
    g = game(("Ex-074",))
    assert code(g, {"type": "use_book_card", "player": 0, "page": 2}) == "event.condition"


def test_ex074_illegal_choice_keeps_pending():
    g = game(("Ex-074",))
    st = g.state
    put(g, 1, "MJ-001", "MJ-002")
    put(g, 0, "MJ-004")
    use_event(g)
    own = st.players[0].field_cards[0].uid
    assert st.pending is not None and st.pending.kind == "pick_opponent_field_card"
    assert code(g, {"type": "choose", "player": 0, "value": own}) == "choose.invalid"   # 自己的 MJ12 不能選
    assert st.pending is not None and field(g, 0) == ["MJ-004"]


# ---------------------------------------------------------------- 快照(battle-api「獨立卡區快照」)

def test_snapshot_field_cards():
    from gash.api.views import snapshot
    g = game(("MJ-004",))
    put(g, 0, "MJ-004")
    use(g, 0, "MJ-004")
    mine, theirs = snapshot(g, 0), snapshot(g, 1)
    fc = mine["players"][0]["field_cards"][0]
    assert fc["card"] == "MJ-004" and fc["ability_used"] and fc["ability_block"] == "used"
    assert fc["ability"]["mode"] == "mp" and fc["ability"]["mp_cost"] == 1
    other = theirs["players"][0]["field_cards"][0]
    assert other["card"] == "MJ-004" and other["ability_used"] and "ability_block" not in other   # 使用可否只給持有者
    page = next(e for e in mine["players"][0]["open_pages"] if e["page"] == 2)
    assert page["play_block"] == "same_name"                                   # 翻開頁的 MJ12 附放出可否
    assert theirs["players"][1]["field_cards"] == []


# ---------------------------------------------------------------- NPC

def test_npc_candidates_include_mj12():
    from gash.npc.candidates import candidates
    g = game(("MJ-004",))
    put(g, 0, "MJ-001")
    cands = candidates(g, 0)
    assert {"type": "play_card", "page": 2} in cands
    uid = g.state.players[0].field_cards[0].uid
    assert {"type": "use_field_ability", "zone": "field", "field_uid": uid} in cands


SELFPLAY_BOOKS = (
    ("M-001", "MJ-001", "S-001", "MJ-002", "P-001", "MJ-003", "S-002", "MJ-004", "S-001", "MJ-005", "M-004",
     "MJ-006", "S-029", "Ex-074", "S-002", "S-001", "P-002", "S-029", "S-002", "S-001", "E-018", "S-029",
     "S-002", "S-001", "S-029", "E-018", "S-002", "S-001", "M-002", "S-029", "S-002", "S-005"),
    ("M-004", "MJ-006", "S-001", "Ex-074", "M-001", "MJ-001", "P-001", "S-002", "MJ-004", "S-001", "P-002",
     "S-029", "MJ-005", "S-002", "S-001", "E-018", "S-029", "MJ-002", "E-018", "S-001", "S-029", "MJ-003",
     "S-002", "S-001", "S-029", "E-018", "S-002", "S-001", "E-032", "S-029", "S-002", "S-005"),
)


def test_selfplay_books_cover_batch():
    assert all(len(b) == 32 for b in SELFPLAY_BOOKS)
    assert set(BATCH) <= set(SELFPLAY_BOOKS[0]) | set(SELFPLAY_BOOKS[1])


@pytest.mark.slow
@pytest.mark.parametrize("levels", [("normal", "normal"), ("normal", "dummy"), ("dummy", "normal")])
@pytest.mark.parametrize("seed", [1, 2, 3])
def test_npc_selfplay_with_mj12(levels, seed):
    import random

    from gash import npc
    from gash.engine.awaiting import awaited_player
    from gash.engine.engine import new_game
    from gash.engine.state import GAME_OVER
    books = [list(b) for b in SELFPLAY_BOOKS]
    g = new_game(books[0], seed=seed, decks=(books[0], books[1]))
    rngs = [random.Random(f"{seed}:{p}") for p in (0, 1)]
    played = False
    for _ in range(3000):
        if g.state.phase == GAME_OVER:
            break
        p = awaited_player(g)
        assert npc.submit_ranked(g, p, npc.decide(g, p, levels[p], rngs[p])) is not None
        played = played or any(ps.field_cards for ps in g.state.players)
    assert g.state.phase == GAME_OVER
    if levels == ("normal", "normal"):                                         # 一般 NPC 會放出 MJ12
        assert played
