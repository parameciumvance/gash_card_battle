"""第 4 賽季戰術第 2b 批(card-effects「第 4 賽季戰術第 2b 批」、game-engine「賦予的魔物效果」「不能被對手選擇的魔物」
「不需使用魔物的非戰鬥戰術」,season4-spells-2b)。依日文效果文。
"""
import pytest

from gash.engine.cards import pending_cards
from gash.engine.engine import submit
from tests.test_level2 import HEADS, TAILS, Rng, book, mk, to_battle
from tests.test_level3 import ability, add_slot, battle_in, choose, code, finish_damage, pass_effects

BATCH = ("S-113", "S-121", "S-136", "S-140", "S-144", "S-145")


def setup(b0, b1=("M-001",), coins=(), mp=10):
    g, _ = mk(book(*b0), book(*b1))
    st = g.state
    g.rng = Rng(*coins)
    st.players[0].mp, st.players[1].mp = mp, mp
    to_battle(g, 0)
    return g


def use(g, page, player=0, slot=None):
    """使用魔書的非戰鬥戰術,對手 pass(回應機會)。"""
    cmd = {"type": "use_book_card", "player": player, "page": page}
    if slot is not None:
        cmd["slot_uid"] = slot.uid
    events = submit(g, cmd)
    if g.state.pending is None and g.state.action_player != player:
        submit(g, {"type": "pass", "player": 1 - player})
    return events


def showdown(g):
    return [e for e in g.events if e["type"] == "showdown"][-1]


def next_turn(g):
    """目前的回合雙方 pass 到結束,下一回合停在戰鬥階段(回合玩家不翻頁)。"""
    st = g.state
    tp = st.turn_player
    while st.turn_player == tp:
        submit(g, {"type": "pass", "player": st.action_player})
    if st.phase == "start":
        to_battle(g, st.turn_player)


def opp_turn(g):
    """結束玩家 0 的回合,進入玩家 1 的戰鬥階段。"""
    next_turn(g)
    assert g.state.turn_player == 1


def test_batch_open():
    assert not set(BATCH) & pending_cards()


# ---------------------------------------------------------------- S-113《格闘》

def _s113():
    g = setup(("M-001", "S-113"), ("M-001", "S-001"))
    use(g, 2)
    return g


def fighting_attack(g, slot, player=0):
    submit(g, {"type": "declare_attack", "player": player, "mode": "mamodo", "slot_uid": slot.uid})
    submit(g, {"type": "battle_in_response", "player": 1 - player, "allow": True})


def test_s113_fighting_attack():
    # 《格闘》使用を宣言する→合計魔力10000で攻撃(相手の魔本に1ダメージ)
    g = _s113()
    st = g.state
    pos, mp = st.players[1].pos, st.players[0].mp
    fighting_attack(g, st.players[0].slots[0])
    submit(g, {"type": "no_defense", "player": 1})
    pass_effects(g)
    finish_damage(g)
    assert showdown(g)["attacker_total"] == 10000 and st.players[1].pos == pos + 2 and st.players[0].mp == mp


def test_s113_once_per_turn():
    g = _s113()
    st = g.state
    gash = st.players[0].slots[0]
    fighting_attack(g, gash)
    submit(g, {"type": "no_defense", "player": 1})
    pass_effects(g)
    finish_damage(g)
    assert code(g, {"type": "declare_attack", "player": 0, "mode": "mamodo", "slot_uid": gash.uid}) == "attack.used"


def test_s113_without_spell_no_fighting():
    g = setup(("M-001", "S-001"))
    st = g.state
    assert code(g, {"type": "declare_attack", "player": 0, "mode": "mamodo",
                    "slot_uid": st.players[0].slots[0].uid}) == "attack.no_mamodo_attack"


def test_s113_gash_deployed_later_also_has_it():
    g = _s113()
    st = g.state
    other = add_slot(g, 0, "M-002")                                          # 期間中上場的ガッシュ・ベル
    fighting_attack(g, other)
    assert st.battle is not None and st.battle.data.get("attack_fixed_power") == 10000


def test_s113_fighting_defense_on_opponent_turn():
    # または防御する(合計魔力10000)
    g = _s113()
    st = g.state
    opp_turn(g)
    pos = st.players[0].pos
    battle_in(g, 2, player=1)
    submit(g, {"type": "declare_defense", "player": 0, "mode": "mamodo", "slot_uid": st.players[0].slots[0].uid})
    pass_effects(g)
    assert showdown(g)["defender_total"] == 10000 and st.players[0].pos == pos


def test_s113_twice_not_stacked():
    # 同じ魔物の能力は重複して持つことはできません(atwiki FAQ A2)
    g = setup(("M-001", "S-113", "S-113"))
    st = g.state
    use(g, 2)
    use(g, 3)
    gash = st.players[0].slots[0]
    fighting_attack(g, gash)
    submit(g, {"type": "no_defense", "player": 1})
    pass_effects(g)
    finish_damage(g)
    assert code(g, {"type": "declare_attack", "player": 0, "mode": "mamodo", "slot_uid": gash.uid}) == "attack.used"


def test_s113_expires_after_own_next_turn():
    g = _s113()
    st = g.state
    opp_turn(g)
    next_turn(g)                                                             # 自己的下一回合
    assert st.turn_player == 0
    next_turn(g)
    next_turn(g)                                                             # 再下一個自己的回合
    assert st.turn_player == 0
    assert code(g, {"type": "declare_attack", "player": 0, "mode": "mamodo",
                    "slot_uid": st.players[0].slots[0].uid}) == "attack.no_mamodo_attack"


# ---------------------------------------------------------------- S-121

def _s121(opp_book=("M-017", "S-036")):
    g = setup(("M-076", "S-121"), opp_book)
    use(g, 2)
    return g


def test_s121_balancia_takes_no_damage_when_protecting():
    # 自分の「バランシャ」はダメージを受けず
    g = _s121(("M-001", "S-001"))
    st = g.state
    bal = st.players[0].slots[0]
    opp_turn(g)
    battle_in(g, 2, player=1)
    submit(g, {"type": "no_defense", "player": 0})
    pass_effects(g)
    assert st.pending.kind == "protect" and st.pending.player == 0
    choose(g, bal.uid)
    assert not bal.injured


def test_s121_s036_cannot_choose_balancia():
    # 相手は、「カードを選ぶ」とき、自分の「バランシャ」を選ぶことができない(「すべてを選ぶ」も)
    g = _s121()
    st = g.state
    bal = st.players[0].slots[0]
    other = add_slot(g, 0, "M-001")
    opp_turn(g)
    battle_in(g, 2, player=1)
    submit(g, {"type": "no_defense", "player": 0})
    pass_effects(g)
    finish_damage(g)
    assert other.injured and not bal.injured
    assert not [e for e in g.events if e["type"] == "damage_prevented" and e.get("slot") == bal.uid]


def test_s121_s058_target_excludes_balancia():
    # S-058「相手の魔物1体を選び、ダメージ」:宣告時的對象只剩バランシャ以外的那隻,自動選定
    g = _s121(("M-051", "S-058"))
    st = g.state
    bal = st.players[0].slots[0]
    other = add_slot(g, 0, "M-001")
    opp_turn(g)
    battle_in(g, 2, player=1)
    assert st.pending is None or st.pending.kind != "injure_instead_target"
    submit(g, {"type": "no_defense", "player": 0})
    pass_effects(g)
    finish_damage(g)
    assert other.injured and not bal.injured


def test_s121_event_target_excludes_balancia():
    # E-024(相手の魔物1體を選ぶ):只剩バランシャ時選不到,不能使用
    g = _s121(("M-001", "E-024"))
    opp_turn(g)
    assert code(g, {"type": "use_book_card", "player": 1, "page": 2}) == "event.condition"


def test_s121_balancia_deployed_later_protected():
    g = _s121(("M-001", "E-024"))
    st = g.state
    st.players[0].slots.clear()
    later = add_slot(g, 0, "M-076")                                          # 期間中上場的バランシャ
    opp_turn(g)
    assert code(g, {"type": "use_book_card", "player": 1, "page": 2}) == "event.condition"
    assert later in st.players[0].slots


# ---------------------------------------------------------------- S-136

def test_s136_locks_both():
    # ●相手の魔物1体を選ぶ。…相手はその魔物の「魔物の効果」や術を使えない。
    # ●自分は、この術を使うのに使った「ニャルラト」の、「魔物の効果」や術を使えない。
    g = setup(("Ex-002", "S-136", "S-138"), ("M-001", "S-001"))
    st = g.state
    a = st.players[1].slots[0]
    add_slot(g, 1, "M-002")
    nyar = st.players[0].slots[0]
    use(g, 2, slot=nyar)
    assert st.pending.kind == "pick_opponent_mamodo" and st.pending.player == 0
    choose(g, a.uid)
    if st.action_player == 1:
        submit(g, {"type": "pass", "player": 1})
    assert code(g, {"type": "declare_attack", "player": 0, "page": 3}) == "spell.mamodo_locked"
    opp_turn(g)
    assert code(g, {"type": "declare_attack", "player": 1, "page": 2, "slot_uid": a.uid}) == "spell.mamodo_locked"


def test_s136_no_opponent_mamodo_unusable():
    g = setup(("Ex-002", "S-136"))
    g.state.players[1].slots.clear()
    assert code(g, {"type": "use_book_card", "player": 0, "page": 2}) == "spell.condition"


# ---------------------------------------------------------------- S-140

def _s140_book(*rest):
    return ("M-001", "S-140", "S-001", "S-001", "Ex-003", *rest)


def test_s140_deploys_noritoh_without_noritoh_on_field():
    # この術は、自分の場に「ノリトー・ハッサミー」がいなくても使える。魔本の好きなページから1枚を選び、場に出す
    g = setup(_s140_book())
    st = g.state
    use(g, 2)
    assert [s.top for s in st.players[0].slots] == ["M-001", "Ex-003"]
    assert 5 in st.players[0].consumed_pages


def test_s140_no_noritoh_in_book_unusable():
    g = setup(("M-001", "S-140"))
    assert code(g, {"type": "use_book_card", "player": 0, "page": 2}) == "spell.condition"


def test_s140_field_full_unusable():
    g = setup(_s140_book())
    add_slot(g, 0, "M-002")
    add_slot(g, 0, "M-003")
    assert code(g, {"type": "use_book_card", "player": 0, "page": 2}) == "spell.condition"


def test_s140_on_opponent_turn():
    # 自分のターン 相手のターン 非バトル
    g = setup(("M-001", "S-001"), _s140_book())
    st = g.state
    submit(g, {"type": "pass", "player": 0})
    assert st.action_player == 1
    use(g, 2, player=1)
    assert [s.top for s in st.players[1].slots] == ["M-001", "Ex-003"]


# ---------------------------------------------------------------- S-144

def test_s144_blocks_opponent_discard_cost_partner():
    # 相手は「このカードを捨て札にする→」効果のカードの効果を使えない(P-016)
    g = setup(("Ex-003", "S-144", "S-141"), ("M-001",))
    st = g.state
    st.players[1].slots[0].partner = "P-016"
    use(g, 2)
    battle_in(g, 3)
    submit(g, {"type": "no_defense", "player": 1})
    submit(g, {"type": "pass", "player": 0})
    assert code(g, ability(1, st.players[1].slots[0], zone="partner")) == "ability.discard_cost_restricted"


def test_s144_blocks_opponent_mj12_and_not_self():
    from gash.engine.state import FieldCard
    g = setup(("Ex-003", "S-144"))
    st = g.state
    st.players[0].field_cards.append(FieldCard(uid=st.next_uid(), card="MJ-001"))
    st.players[1].field_cards.append(FieldCard(uid=st.next_uid(), card="MJ-001"))
    use(g, 2)
    mine = st.players[0].field_cards[0]
    submit(g, {"type": "use_field_ability", "player": 0, "zone": "field", "field_uid": mine.uid})   # 自己不受限
    if st.pending is not None:
        finish_damage(g)
    assert "MJ-001" in st.players[0].discard
    while st.action_player != 1:
        submit(g, {"type": "pass", "player": st.action_player})
    theirs = st.players[1].field_cards[0]
    assert code(g, {"type": "use_field_ability", "player": 1, "zone": "field",
                    "field_uid": theirs.uid}) == "ability.discard_cost_restricted"


@pytest.mark.parametrize("with_s144", [True, False])
def test_s144_blocks_opponent_coin_set_heads(with_s144):
    # M-034《サーカスの特訓》このカードを捨て札にする→自分が投げたコイン1個をオモテにする:不提供
    first = ("Ex-003", "S-144", "S-001") if with_s144 else ("Ex-003", "S-001", "S-001")
    g = setup(("M-001",) + first[1:], ("M-001", "S-025"), coins=(TAILS,))
    st = g.state
    add_slot(g, 1, "M-034")
    if with_s144:
        st.players[0].slots[0].stack = ["Ex-003"]
        use(g, 2)
        st.players[0].slots[0].stack = ["M-001"]
    battle_in(g, 3)
    submit(g, {"type": "declare_defense", "player": 1, "page": 2, "slot_uid": st.players[1].slots[0].uid})
    offered = st.pending is not None and st.pending.kind == "coin_confirm" and \
        "set_heads" in [o["label"] for o in st.pending.options]
    assert offered is (not with_s144)


@pytest.mark.parametrize("with_s144", [True, False])
def test_s144_blocks_opponent_discard_jammer(with_s144):
    # M-032《おでかけガッシュ》このカードを捨て札にする→相手が直前に使ったイベントカード1つを無効:不提供
    from tests.test_level3 import use_event
    g = setup(("Ex-003", "S-144" if with_s144 else "S-001", "E-049"), ("M-001",))
    st = g.state
    add_slot(g, 1, "M-032")
    if with_s144:
        use(g, 2)
    use_event(g, 3)
    if st.pending is not None and st.pending.kind == "pick_effect":
        choose(g, st.pending.options[0]["value"])
    offered = st.pending is not None and st.pending.kind == "jammer_negate"
    assert offered is (not with_s144)


def test_s144_expires_after_next_turn():
    g = setup(("Ex-003", "S-144"), ("M-001",))
    st = g.state
    st.players[1].slots[0].partner = "P-001"
    use(g, 2)
    opp_turn(g)
    next_turn(g)
    assert st.turn_player == 0
    from gash.engine.engine import restricted
    from gash.engine.state import NO_DISCARD_COST_EFFECTS
    assert not restricted(g, 1, NO_DISCARD_COST_EFFECTS)


# ---------------------------------------------------------------- S-145

def _s145(coin):
    pages = ["S-001"] * 12
    pages[7] = "S-005"                                                       # 第 10 頁
    pages[10] = "S-002"                                                      # 第 13 頁
    g, _ = mk(book("M-001", "S-145", *pages), book("M-001"))
    st = g.state
    g.rng = Rng(coin)
    st.players[0].mp, st.players[1].mp = 10, 10
    to_battle(g, 0)
    use(g, 2)
    return g


def test_s145_heads_spell_from_four_spreads_ahead():
    # 今のページより4枚後ろまでの好きなページの術を使える(翻開頁之後 4 個對頁:第 4〜11 頁)
    g = _s145(HEADS)
    st = g.state
    assert code(g, {"type": "declare_attack", "player": 0, "page": 13}) == "page.not_open"
    submit(g, {"type": "declare_attack", "player": 0, "page": 10})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    assert st.battle is not None and st.battle.attack_spell == "S-005"


def test_s145_tails_nothing():
    g = _s145(TAILS)
    assert code(g, {"type": "declare_attack", "player": 0, "page": 10}) == "page.not_open"
    assert not [sb for sb in g.state.standby if sb.source == "S-145"]


# ---------------------------------------------------------------- NPC 自我對戰

SELFPLAY_BOOKS = (
    ("M-001", "S-113", "M-076", "S-121", "Ex-002", "S-136", "S-138", "Ex-003", "S-140", "S-144", "S-145",
     "S-001", "P-001", "S-002", "M-002", "S-003", "S-005", "P-002", "S-022", "S-001", "M-003", "S-004",
     "S-001", "S-002", "S-003", "M-005", "S-009", "S-001", "S-002", "S-003", "S-141", "S-142"),
    ("M-017", "S-036", "S-009", "M-001", "S-001", "E-024", "P-016", "M-034", "S-025", "S-005", "P-017",
     "S-022", "M-002", "S-003", "M-003", "S-004", "S-002", "M-005", "S-010", "S-001", "S-002", "S-003",
     "S-001", "S-002", "S-003", "S-001", "S-002", "S-003", "S-001", "S-002", "S-003", "S-008"),
)


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
