"""第 4 賽季戰術第 2a 批(card-effects「第 4 賽季戰術第 2a 批」、game-engine「戰鬥中的禁止於宣告時生效」
「戰鬥戰術的使用條件」,season4-spells-2a)。依日文效果文。
"""
import pytest

from gash.api.views import snapshot
from gash.engine.cards import pending_cards
from gash.engine.engine import IllegalCommand, restricted, submit
from gash.engine.state import NO_EVENTS, NO_PARTNER_EFFECTS
from tests.test_level2 import HEADS, TAILS, Rng, book, mk, to_battle
from tests.test_level3 import ability, add_slot, attack, battle_in, choose, code, end_turn, finish_damage, pass_effects

BATCH = ("S-117", "S-125", "S-128", "S-129", "S-131", "S-133", "S-146", "Ex-063")


def setup(att, deff=("M-001",), coins=(), att_partner=None, def_partner=None, mp=10):
    g, _ = mk(book(*att), book(*deff))
    st = g.state
    g.rng = Rng(*coins)
    if att_partner:
        st.players[0].slots[0].partner = att_partner
    if def_partner:
        st.players[1].slots[0].partner = def_partner
    st.players[0].mp, st.players[1].mp = mp, mp
    to_battle(g, 0)
    return g


def resolve(g):
    pass_effects(g)
    finish_damage(g)
    return [e for e in g.events if e["type"] == "showdown"][-1]


def book_damage(g, pos_before, player=1):
    return (g.state.players[player].pos - pos_before) // 2


def restriction_sources(g, player):
    return [e["source"] for e in snapshot(g, 0)["effects"]
            if e["kind"] == "restriction" and e["target_player"] == player]


def test_batch_open():
    assert not set(BATCH) & pending_cards()


# ---------------------------------------------------------------- S-117 / S-131:このバトル中…使えない

def test_s117_blocks_opponent_events_from_declaration():
    # このバトル中、相手はイベントカードを使えない(宣告時起)
    g = setup(("M-037", "S-117"), ("M-001", "E-053"))
    attack(g, 2)
    # 戰鬥中使用魔書的事件卡要等 E-053 實作才有;此處驗證事件卡使用檢查所依據的限制
    assert "S-117" in restriction_sources(g, 1) and restricted(g, 1, NO_EVENTS) and not restricted(g, 0, NO_EVENTS)


def test_s117_lifted_when_attack_negated():
    # 攻擊被無效(防方 P-016)後,限制一起解除
    g = setup(("M-037", "S-117"), ("M-001", "E-053"), def_partner="P-016")
    st = g.state
    attack(g, 2)
    submit(g, {"type": "pass", "player": 0})
    submit(g, ability(1, st.players[1].slots[0], zone="partner"))
    assert st.battle.attack_negated
    assert "S-117" not in restriction_sources(g, 1) and not restricted(g, 1, NO_EVENTS)


def test_s117_defense_blocks_attacker_events():
    # 防禦に使ったときも、相手(攻擊方)はイベントカードを使えない
    g = setup(("M-001", "S-001"), ("M-037", "S-117"))
    attack(g, 2, defend_page=2)
    assert "S-117" in restriction_sources(g, 0) and "S-117" not in restriction_sources(g, 1)


def test_s117_restriction_ends_with_battle():
    g = setup(("M-037", "S-117"))
    attack(g, 2)
    resolve(g)
    assert "S-117" not in restriction_sources(g, 1)


def test_s131_blocks_both_partner_and_event_effects():
    # このバトル中、自分も相手も、パートナーの効果やイベントの効果を使えない
    g = setup(("M-042", "S-131"), ("M-001", "E-053"), def_partner="P-016")
    st = g.state
    attack(g, 2)
    submit(g, {"type": "pass", "player": 0})
    assert code(g, ability(1, st.players[1].slots[0], zone="partner")) == "ability.partner_restricted"
    assert all(restricted(g, p, f) for p in (0, 1) for f in (NO_EVENTS, NO_PARTNER_EFFECTS))
    assert restriction_sources(g, 0).count("S-131") == 2 and restriction_sources(g, 1).count("S-131") == 2


# ---------------------------------------------------------------- S-125

def _s125(coins):
    g = setup(("Ex-032", "S-125"), coins=coins, def_partner="P-001")
    a = g.state.players[1].slots[0]
    b = add_slot(g, 1, "M-002", partner="P-002")
    return g, a, b


@pytest.mark.parametrize("coins, a_kept, b_kept", [((HEADS, TAILS), False, True), ((TAILS, HEADS), True, False),
                                                   ((HEADS, HEADS), False, False), ((TAILS, TAILS), True, True)])
def test_s125_discards_partners_per_heads(coins, a_kept, b_kept):
    # 相手のパートナー1枚を選ぶ。コインを投げてオモテなら、そのパートナーを捨て札にする。これを相手のパートナーすべてについて
    g, a, b = _s125(coins)
    pos = g.state.players[1].pos
    battle_in(g, 2)
    flips = [e for e in g.events if e["type"] == "coin_flipped" and e.get("source") == "S-125"]
    assert len(flips) == 2                                                   # 宣告時,每張搭檔 1 次
    submit(g, {"type": "no_defense", "player": 1})
    assert resolve(g)["winner"] == "attacker"
    assert (a.partner == "P-001") is a_kept and (b.partner == "P-002") is b_kept
    assert book_damage(g, pos) == 0


def test_s125_no_discard_when_defender_wins():
    g = setup(("Ex-032", "S-125"), ("M-050", "S-022"), coins=(HEADS,), def_partner="P-001")
    battle_in(g, 2)
    submit(g, {"type": "declare_defense", "player": 1, "page": 2})
    assert resolve(g)["winner"] == "defender" and g.state.players[1].slots[0].partner == "P-001"


def test_s125_no_partners_no_coin():
    g = setup(("Ex-032", "S-125"))
    battle_in(g, 2)
    assert not [e for e in g.events if e["type"] == "coin_flipped" and e.get("source") == "S-125"]


# ---------------------------------------------------------------- S-128 / S-129

def test_s128_negates_thunder_attack_regardless():
    # 魔力勝負の勝敗にかかわらず、相手の「雷」属性の攻撃を無効にする(Ex-013 ザケル:雷)
    g = setup(("M-001", "S-005", "Ex-013"), ("Ex-031", "S-128"))
    st = g.state
    st.players[0].slots[0].stack = ["M-047"]                                 # 魔力 9000:防禦方落敗也無效
    pos = st.players[1].pos
    attack(g, 3, defend_page=2)
    assert not st.battle.attack_negated
    show = resolve(g)
    assert show["attack_negated"] and book_damage(g, pos) == 0


def test_s128_non_thunder_loses():
    g = setup(("M-017", "S-010"), ("Ex-031", "S-128"))                      # S-010 為重力屬性:5000 + 3000 > 3500 + 4000
    pos = g.state.players[1].pos
    attack(g, 2, defend_page=2)
    show = resolve(g)
    assert show["winner"] == "attacker" and not show["attack_negated"] and book_damage(g, pos) == 2


def test_s128_defense_win_negates():
    g = setup(("M-001", "S-001"), ("Ex-031", "S-128"))                      # 3500 + 4000 > 4000 + 2000
    pos = g.state.players[1].pos
    attack(g, 2, defend_page=2)
    assert resolve(g)["winner"] == "defender" and book_damage(g, pos) == 0


def test_s129_after_using_aschild_last_turn():
    # 直前のターンに、自分が術カード「アシルド」を使っていれば、この術の魔力を+4000、ダメージを+2する
    g, _ = mk(book("M-001", "S-001"), book("Ex-031", "S-128", "S-129"))
    st = g.state
    st.players[0].mp, st.players[1].mp = 10, 10
    to_battle(g, 0)
    attack(g, 2, defend_page=2)                                              # 玩家 1 在對手的回合用アシルド
    resolve(g)
    end_turn(g)
    assert st.turn_player == 1
    page = 3 if 3 in st.players[1].open_pages() else None
    assert page is not None
    pos = st.players[0].pos
    submit(g, {"type": "declare_attack", "player": 1, "page": page})
    submit(g, {"type": "battle_in_response", "player": 0, "allow": True})
    submit(g, {"type": "no_defense", "player": 0})
    show = resolve(g)
    assert show["attacker_total"] == 3500 + 2000 + 4000 and book_damage(g, pos, player=0) == 3


def test_s129_without_aschild():
    g = setup(("Ex-031", "S-129"))
    pos = g.state.players[1].pos
    attack(g, 2)
    show = resolve(g)
    assert show["attacker_total"] == 3500 + 2000 and book_damage(g, pos) == 1


# ---------------------------------------------------------------- S-133

def test_s133_steals_mp_on_damage():
    # 相手の魔本か魔物にダメージをあたえたとき、相手のMPを3へらし、へらした数だけ自分のMPをふやす
    g = setup(("M-042", "S-133"), mp=10)
    st = g.state
    st.players[1].mp = 2
    attack(g, 2)
    mp0 = st.players[0].mp
    resolve(g)
    assert st.players[1].mp == 0 and st.players[0].mp == mp0 + 2


# ---------------------------------------------------------------- S-146

def _s146(att_mamodo="M-047", opp=("Ex-003",)):
    g = setup((att_mamodo, "S-146"), opp)
    return g


def test_s146_condition_power_gap():
    # この術を使う魔物の魔力が、相手のどの魔物の魔力より5000以上、上回っているとき使える
    g = _s146("M-001")                                                       # 4000 < 1500 + 5000
    assert code(g, {"type": "declare_attack", "player": 0, "page": 2}) == "spell.condition"


def test_s146_condition_checks_every_opponent_mamodo():
    g = _s146()                                                              # 9000 vs 1500 / 4500
    add_slot(g, 1, "M-017")                                                  # 5000:9000 < 10000
    assert code(g, {"type": "declare_attack", "player": 0, "page": 2}) == "spell.condition"


def test_s146_no_opponent_mamodo_unusable():
    g = _s146()
    g.state.players[1].slots.clear()
    assert code(g, {"type": "declare_attack", "player": 0, "page": 2}) == "spell.condition"


def test_s146_returns_whole_stack_and_discards_partner():
    # 相手は相手の魔物1体を選び、相手の魔本の空いているページにもどす
    g = _s146()
    st = g.state
    ps = st.players[1]
    a = ps.slots[0]
    b = add_slot(g, 1, "M-002", partner="P-002")
    b.stack = ["M-001", "M-002"]
    ps.consumed_pages |= {10, 11, 12}
    battle_in(g, 2)
    submit(g, {"type": "no_defense", "player": 1})
    pass_effects(g)
    assert st.pending.kind == "pick_own_mamodo" and st.pending.player == 1   # 對手選
    with pytest.raises(IllegalCommand) as exc:
        choose(g, 9999)
    assert exc.value.code == "choose.invalid"
    choose(g, b.uid)
    assert st.pending.kind == "pick_own_empty_page" and st.pending.player == 1
    assert sorted(o["value"] for o in st.pending.options) == [1, 10, 11, 12]  # 第 1 頁:開局放出魔物後的空頁
    choose(g, 12)                                                            # 最上面的 M-002
    choose(g, 10)                                                            # M-001
    assert st.pending is None and st.battle is None
    assert b not in ps.slots and a in ps.slots
    assert ps.book[11] == "M-002" and ps.book[9] == "M-001" and ps.consumed_pages == {1, 11}
    assert "P-002" in ps.discard


def test_s146_unreturnable_mamodo_not_offered():
    g = _s146()
    st = g.state
    ps = st.players[1]
    b = add_slot(g, 1, "M-002")
    b.stack = ["M-001", "M-002"]
    ps.consumed_pages = {10}                                                 # 只有 1 個空頁:2 張的不能選
    battle_in(g, 2)
    submit(g, {"type": "no_defense", "player": 1})
    pass_effects(g)
    assert st.pending is None                                                # 只剩 Ex-003 可選、只有 1 個空頁:自動
    assert ps.book[9] == "Ex-003" and b in ps.slots and st.battle is None


def test_s146_once_per_turn():
    g = setup(("M-047", "S-146", "S-146"), ("Ex-003",))
    st = g.state
    st.players[1].consumed_pages |= set()                                    # 沒有空頁:放回沒有效果
    battle_in(g, 2)
    submit(g, {"type": "no_defense", "player": 1})
    pass_effects(g)
    assert st.battle is None
    assert code(g, {"type": "declare_attack", "player": 0, "page": 3}) == "spell.used"


# ---------------------------------------------------------------- Ex-063

def _ex063(att_spell, extra):
    g = setup(("M-001", att_spell), ("M-042", "Ex-063"))
    st = g.state
    battle_in(g, 2)
    submit(g, {"type": "declare_defense", "player": 1, "page": 2})
    assert st.pending.kind == "spell_extra_cost" and st.pending.player == 1
    choose(g, extra)
    return g


@pytest.mark.parametrize("spell, extra, negated", [
    ("S-001", 0, True), ("S-001", 2, True),                                  # 傷害 1
    ("Ex-062", 0, False), ("Ex-062", 2, True),                               # 傷害 2
    ("S-005", 2, False),                                                     # 傷害 3
])
def test_ex063_negates_by_damage(spell, extra, negated):
    # 相手の1ダメージの攻撃を無効にする。この術のコストを2ふやすことで、相手の2ダメージの攻撃も無効にできる
    g = _ex063(spell, extra)
    assert not g.state.battle.attack_negated
    assert resolve(g)["attack_negated"] is negated


def test_ex063_uses_current_damage():
    # 當下傷害(含 +N 加成)剛好 1 才無效:S-082 擲出正面 → 傷害 2
    g, _ = mk(book("M-044", "S-082"), book("M-042", "Ex-063"))
    st = g.state
    g.rng = Rng(HEADS)
    st.players[0].mp, st.players[1].mp = 10, 10
    to_battle(g, 0)
    battle_in(g, 2)
    submit(g, {"type": "declare_defense", "player": 1, "page": 2})
    choose(g, 0)
    assert not resolve(g)["attack_negated"]


def test_ex063_extra_cost_paid():
    g = _ex063("S-001", 2)
    assert g.state.players[1].mp == 10 - 1 - 2


# ---------------------------------------------------------------- NPC 自我對戰

SELFPLAY_BOOKS = (
    ("M-037", "S-117", "Ex-032", "S-125", "Ex-031", "S-128", "S-129", "M-042", "S-131", "S-133", "Ex-063",
     "M-001", "S-146", "S-001", "P-001", "S-002", "M-002", "S-003", "S-005", "P-002", "S-022", "S-001",
     "M-003", "S-004", "S-001", "S-002", "S-003", "M-005", "S-009", "S-001", "S-002", "S-003"),
    ("M-001", "S-001", "Ex-013", "Ex-062", "P-016", "M-042", "Ex-063", "S-133", "Ex-031", "S-128", "S-129",
     "M-037", "S-117", "S-005", "P-017", "S-022", "M-002", "S-003", "M-003", "S-004", "S-002", "M-005",
     "S-009", "S-001", "S-002", "S-003", "S-001", "S-002", "S-003", "S-001", "S-002", "S-003"),
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
