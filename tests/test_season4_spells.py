"""第 4 賽季戰術第 1 批(card-effects「第 4 賽季的戰術(第 1 批)」等,season4-spells-basic)。

依日文效果文;防禦戰術於「効果の使用」的最後解決(defense-effects-timing)。
"""
import pytest

from gash.engine.cards import pending_cards
from gash.engine.engine import IllegalCommand, submit
from tests.test_level2 import HEADS, TAILS, Rng, book, mk, to_battle
from tests.test_level3 import ability, add_slot, attack, battle_in, choose, code, end_turn, finish_damage, pass_effects

BATCH = ("S-119", "S-122", "S-123", "S-124", "S-126", "S-127", "S-138", "Ex-062", "Ex-066", "Ex-067", "S-114",
         "S-116", "S-141", "Ex-068", "S-142", "S-134", "S-120", "Ex-065", "S-139", "Ex-064", "S-130",
         "S-132", "S-137", "Ex-050", "S-143", "S-115", "S-118")


def setup(att, deff=("M-001",), coins=(), att_partner=None):
    """玩家 0 的魔書 att(第 1 頁為場上魔物)、玩家 1 的魔書 deff;雙方 MP 10,進入玩家 0 的戰鬥階段。"""
    g, _ = mk(book(*att), book(*deff))
    st = g.state
    g.rng = Rng(*coins)
    if att_partner:
        st.players[0].slots[0].partner = att_partner
    st.players[0].mp, st.players[1].mp = 10, 10
    to_battle(g, 0)
    return g


def resolve(g):
    """戰鬥中效果雙方 pass,不保護,回傳魔力勝負事件。"""
    pass_effects(g)
    finish_damage(g)
    return [e for e in g.events if e["type"] == "showdown"][-1]


def book_damage(g, pos_before):
    return (g.state.players[1].pos - pos_before) // 2


def test_batch_open():
    assert not set(BATCH) & pending_cards()


# ---------------------------------------------------------------- 香草 / 資料驅動

@pytest.mark.parametrize("spell, mamodo, damage", [
    ("S-119", "M-076", 1), ("S-122", "M-076", 3), ("S-123", "Ex-032", 1), ("S-124", "Ex-032", 2),
    ("S-126", "Ex-032", 3), ("S-127", "Ex-031", 1), ("S-138", "Ex-002", 3), ("Ex-062", "M-001", 2),
    ("Ex-066", "Ex-056", 2), ("Ex-067", "Ex-057", 2),
])
def test_vanilla_damage(spell, mamodo, damage):
    g = setup((mamodo, spell))
    pos = g.state.players[1].pos
    attack(g, 2)
    assert resolve(g)["winner"] == "attacker" and book_damage(g, pos) == damage


def test_s114_defense_win_negates():
    # 魔力勝負で勝ったとき、相手の攻撃を無効にする(3500 + 5000 > 4000 + 2000)
    g = setup(("M-001", "S-001"), ("M-037", "S-114"))
    pos = g.state.players[1].pos
    attack(g, 2, defend_page=2)
    assert resolve(g)["winner"] == "defender" and book_damage(g, pos) == 0


# ---------------------------------------------------------------- 沿用既有寫法

def test_s116_win_blocks_opponent_until_end_of_next_turn():
    # 【ステイ】次のターンのエンドフェイズまで、相手は「魔物の効果」や術を使えない
    g = setup(("M-037", "S-116"), ("M-001", "S-001"))
    attack(g, 2)
    resolve(g)
    end_turn(g)
    assert g.state.turn_player == 1
    page = g.state.players[1].open_pages()[0]                                # 翻開頁的 S-029(ガッシュ・ベルの術)
    assert code(g, {"type": "declare_attack", "player": 1, "page": page}) == "spell.restricted"


def test_s141_damage_blocks_opponent_spells():
    # 相手の魔本か魔物にダメージをあたえたとき、次のターンのエンドフェイズまで、相手は術を使えない
    g = setup(("Ex-003", "S-141"), ("M-001", "S-001"))
    pos = g.state.players[1].pos
    attack(g, 2)
    resolve(g)
    assert book_damage(g, pos) == 1
    end_turn(g)
    page = g.state.players[1].open_pages()[0]                                # 翻開頁的 S-029(ガッシュ・ベルの術)
    assert code(g, {"type": "declare_attack", "player": 1, "page": page}) == "spell.restricted"


def test_ex068_defense_bonus():
    # この術を防御で使ったとき、この術の魔力を+2000する(4500 + 2000 + 2000)
    g = setup(("M-001", "S-001"), ("Ex-058", "Ex-068"))
    attack(g, 2, defend_page=2)
    assert resolve(g)["defender_total"] == 8500


def test_ex068_attack_no_bonus():
    g = setup(("Ex-058", "Ex-068"))
    attack(g, 2)
    assert resolve(g)["attacker_total"] == 6500


@pytest.mark.parametrize("coin, damage", [(HEADS, 2), (TAILS, 1)])
def test_s142_coin_damage(coin, damage):
    # コインを投げてオモテなら、この術のダメージを+1する。相手の魔本にダメージ
    g = setup(("Ex-003", "S-142"), coins=(coin,))
    pos = g.state.players[1].pos
    attack(g, 2)
    resolve(g)
    assert book_damage(g, pos) == damage


@pytest.mark.parametrize("coin, damage", [(HEADS, 2), (TAILS, 1)])
def test_s134_fixed_total_and_coin(coin, damage):
    # この術の合計魔力は7000になる。コインを投げてオモテなら、この術のダメージを+1する
    g = setup(("M-045", "S-134"), coins=(coin,))
    pos = g.state.players[1].pos
    attack(g, 2)
    assert resolve(g)["attacker_total"] == 7000 and book_damage(g, pos) == damage


def test_s134_defense_fixed_total():
    g = setup(("M-001", "S-001"), ("M-045", "S-134"))
    attack(g, 2, defend_page=2)
    assert resolve(g)["defender_total"] == 7000


# ---------------------------------------------------------------- 防禦戰術

@pytest.mark.parametrize("spell, mamodo", [("S-120", "M-076"), ("Ex-065", "Ex-032")])
@pytest.mark.parametrize("coins, negated", [((TAILS, HEADS), True), ((TAILS, TAILS), False)])
def test_coin_negate_defense(spell, mamodo, coins, negated):
    # 魔力勝負の勝敗にかかわらず、コインを2回投げて、オモテが1回以上出れば、相手の攻撃を無効にする
    g = setup(("M-001", "S-005"), (mamodo, spell), coins=coins)
    pos = g.state.players[1].pos
    attack(g, 2, defend_page=2)
    assert not g.state.battle.attack_negated                                 # 「効果の使用」的最後才解決
    show = resolve(g)
    assert show["attack_negated"] is negated and book_damage(g, pos) == (0 if negated else 3)


@pytest.mark.parametrize("spell, mamodo", [("S-120", "M-076"), ("Ex-065", "Ex-032")])
def test_coin_negate_defense_negated(spell, mamodo):
    g = setup(("M-001", "S-005"), (mamodo, spell), coins=(HEADS, HEADS), att_partner="P-017")
    pos = g.state.players[1].pos
    attack(g, 2, defend_page=2)
    submit(g, ability(0, g.state.players[0].slots[0], zone="partner"))      # 防禦被無效
    show = resolve(g)
    assert not show["attack_negated"] and book_damage(g, pos) == 3


@pytest.mark.parametrize("spell, mamodo, damage", [("S-139", "Ex-002", 1), ("Ex-064", "Ex-031", 2),
                                                   ("S-130", "Ex-031", 1)])
def test_defense_damage_reduction(spell, mamodo, damage):
    # 魔力勝負の勝敗にかかわらず、相手の攻撃のダメージを2(1)へらす;S-130 は防御に使ったとき
    g = setup(("M-001", "S-005"), (mamodo, spell))
    pos = g.state.players[1].pos
    attack(g, 2, defend_page=2)
    assert resolve(g)["winner"] == "attacker" and book_damage(g, pos) == damage


def test_s139_negated_defense_no_reduction():
    g = setup(("M-001", "S-005"), ("Ex-002", "S-139"), att_partner="P-017")
    pos = g.state.players[1].pos
    attack(g, 2, defend_page=2)
    submit(g, ability(0, g.state.players[0].slots[0], zone="partner"))
    resolve(g)
    assert book_damage(g, pos) == 3


def test_s130_attack_is_normal_damage():
    g = setup(("Ex-031", "S-130"))
    pos = g.state.players[1].pos
    attack(g, 2)
    resolve(g)
    assert book_damage(g, pos) == 3


# ---------------------------------------------------------------- 依條件或計數

def test_s132_no_defense_plus_one():
    # このバトル中に相手が防御していなければ、この術のダメージを+1する
    g = setup(("M-042", "S-132"))
    pos = g.state.players[1].pos
    attack(g, 2)
    resolve(g)
    assert book_damage(g, pos) == 3


def test_s132_negated_defense_counts_as_defended():
    g = setup(("M-042", "S-132"), ("M-050", "S-022"), att_partner="P-017")
    pos = g.state.players[1].pos
    attack(g, 2, defend_page=2)
    submit(g, ability(0, g.state.players[0].slots[0], zone="partner"))
    assert resolve(g)["winner"] == "attacker" and book_damage(g, pos) == 2


@pytest.mark.parametrize("coins, damage", [((HEADS, HEADS), 2), ((HEADS, TAILS), 1), ((TAILS, TAILS), 0)])
def test_s137_damage_is_heads(coins, damage):
    # この術のダメージは、コインを2回投げて、オモテの数×1になる
    g = setup(("Ex-002", "S-137"), coins=coins)
    pos = g.state.players[1].pos
    attack(g, 2)
    assert resolve(g)["winner"] == "attacker" and book_damage(g, pos) == damage


def test_s137_defense_no_coin():
    g = setup(("M-001", "S-001"), ("Ex-002", "S-137"))
    attack(g, 2, defend_page=2)
    assert not [e for e in g.events if e["type"] == "coin_flipped" and e.get("source") == "S-137"]


def test_ex050_power_and_damage_per_heads():
    # コインを5回投げる。この術の魔力はオモテの数×1000、ダメージはオモテの数×1になる
    g = setup(("M-001", "Ex-050"), coins=(HEADS, HEADS, TAILS, HEADS, TAILS))
    pos = g.state.players[1].pos
    attack(g, 2)
    show = resolve(g)
    assert show["attacker_total"] == 4000 + 3000 and book_damage(g, pos) == 3


def test_s143_power_counts_discarded_mamodo_at_showdown():
    # この術の魔力は、自分の捨て札の魔物カードの数×2000になる(魔力勝負時計算)
    g = setup(("Ex-003", "S-143"))
    ps = g.state.players[0]
    ps.discard += ["M-001", "M-002", "S-001", "P-001", "M-003"]               # 魔物卡 3 張
    attack(g, 2)
    ps.discard.append("M-004")                                               # 戰鬥中多 1 張
    assert resolve(g)["attacker_total"] == 1500 + 4 * 2000


def test_s143_preview_uses_current_count():
    from gash.engine.engine import spell_power_preview
    g = setup(("Ex-003", "S-143"))
    ps = g.state.players[0]
    ps.discard += ["M-001", "M-002"]
    total, _ = spell_power_preview(g, 0, ps.slots[0], "S-143", "attack")
    assert total == 1500 + 2 * 2000


# ---------------------------------------------------------------- S-115

def test_s115_heads_damages_chosen_mamodo():
    # 次の効果の両方を、この順で使う。●相手の魔本にダメージ。●コインを投げてオモテなら、相手の魔物1体を選び、ダメージ
    g = setup(("M-037", "S-115"), coins=(HEADS,))
    st = g.state
    a = st.players[1].slots[0]
    b = add_slot(g, 1, "M-002")
    pos = st.players[1].pos
    battle_in(g, 2)
    assert st.pending.kind == "pick_opponent_mamodo" and st.pending.player == 0   # 宣告時由攻擊方選
    with pytest.raises(IllegalCommand) as exc:
        choose(g, 9999)
    assert exc.value.code == "choose.invalid" and st.pending.kind == "pick_opponent_mamodo"
    choose(g, b.uid)
    submit(g, {"type": "no_defense", "player": 1})
    resolve(g)
    assert book_damage(g, pos) == 1 and b.injured and not a.injured


def test_s115_tails_book_only():
    g = setup(("M-037", "S-115"), coins=(TAILS,))
    st = g.state
    a = st.players[1].slots[0]
    add_slot(g, 1, "M-002")
    pos = st.players[1].pos
    battle_in(g, 2)
    assert st.pending is None
    submit(g, {"type": "no_defense", "player": 1})
    resolve(g)
    assert book_damage(g, pos) == 1 and not any(s.injured for s in st.players[1].slots) and a in st.players[1].slots


def test_s115_heads_target_gone():
    g = setup(("M-037", "S-115"), coins=(HEADS,))
    st = g.state
    b = add_slot(g, 1, "M-002")
    battle_in(g, 2)
    choose(g, b.uid)
    submit(g, {"type": "no_defense", "player": 1})
    st.players[1].slots.remove(b)                                            # 結算前離場
    pos = st.players[1].pos
    resolve(g)
    assert book_damage(g, pos) == 1 and not any(s.injured for s in st.players[1].slots)


def _after_s057(att, coins):
    """玩家 0 以第 2 頁的 S-057(擲出正面)排定待命;對手場上 M-001 與 M-002。"""
    g = setup((att, "S-057", "S-115"), coins=(HEADS, *coins))
    st = g.state
    st.players[0].mp = 20
    a = st.players[1].slots[0]
    b = add_slot(g, 1, "M-002")
    submit(g, {"type": "use_book_card", "player": 0, "page": 2, "slot_uid": st.players[0].slots[0].uid})
    submit(g, {"type": "pass", "player": 1})
    return g, a, b


def test_s115_with_s057_changes_book_damage_only():
    # S-057 只改變「相手の魔本にダメージ」:魔書傷害改給 S-057 選的魔物;擲幣的魔物傷害照舊
    g, a, b = _after_s057("M-037", (HEADS,))
    st = g.state
    pos = st.players[1].pos
    battle_in(g, 3)
    assert st.pending.kind == "injure_instead_target"
    choose(g, a.uid)
    assert st.pending.kind == "pick_opponent_mamodo"
    choose(g, b.uid)
    submit(g, {"type": "no_defense", "player": 1})
    resolve(g)
    assert book_damage(g, pos) == 0 and a.injured and b.injured


# ---------------------------------------------------------------- S-118

def _s118(*partners):
    g = setup(("M-076", "S-118"))
    st = g.state
    a = st.players[1].slots[0]
    a.partner = partners[0] if partners else None
    b = add_slot(g, 1, "M-002", partner=partners[1]) if len(partners) > 1 else None
    return g, a, b


def test_s118_discard_chosen_partner():
    # 次の効果の1つを使う。●相手の魔本にダメージ。●相手のパートナー1枚を選び、捨て札にする
    g, a, b = _s118("P-001", "P-002")
    st = g.state
    pos = st.players[1].pos
    battle_in(g, 2)
    assert st.pending.kind == "pick_effect" and st.pending.player == 0
    assert [o["value"] for o in st.pending.options] == ["book", "partner"]
    choose(g, "partner")
    assert st.pending.kind == "pick_opponent_partner" and st.pending.player == 0
    with pytest.raises(IllegalCommand) as exc:
        choose(g, 9999)
    assert exc.value.code == "choose.invalid" and st.pending.kind == "pick_opponent_partner"
    choose(g, b.uid)
    submit(g, {"type": "no_defense", "player": 1})
    resolve(g)
    assert book_damage(g, pos) == 0 and b.partner is None and a.partner == "P-001"
    assert "P-002" in st.players[1].discard


def test_s118_book_damage():
    g, a, b = _s118("P-001", "P-002")
    st = g.state
    pos = st.players[1].pos
    battle_in(g, 2)
    choose(g, "book")
    assert st.pending is None
    submit(g, {"type": "no_defense", "player": 1})
    resolve(g)
    assert book_damage(g, pos) == 1 and a.partner == "P-001" and b.partner == "P-002"


def test_s118_no_partner_only_book():
    g, a, _ = _s118()
    st = g.state
    pos = st.players[1].pos
    battle_in(g, 2)
    assert st.pending is None                                                # 只有魔書一個選項,自動
    submit(g, {"type": "no_defense", "player": 1})
    resolve(g)
    assert book_damage(g, pos) == 1


def test_s118_defender_wins_no_discard():
    g = setup(("M-076", "S-118"), ("M-050", "S-022"))
    st = g.state
    a = st.players[1].slots[0]
    a.partner = "P-001"
    battle_in(g, 2)
    choose(g, "partner")
    submit(g, {"type": "declare_defense", "player": 1, "page": 2})
    assert resolve(g)["winner"] == "defender" and a.partner == "P-001"


# ---------------------------------------------------------------- NPC 自我對戰

SELFPLAY_BOOKS = (
    ("M-076", "S-119", "S-122", "S-120", "S-118", "Ex-032", "S-123", "S-124", "S-126", "Ex-065", "Ex-031",
     "S-127", "Ex-064", "S-130", "Ex-002", "S-138", "S-139", "S-137", "M-001", "Ex-062", "Ex-050", "S-001",
     "P-001", "S-002", "M-002", "S-003", "S-005", "P-002", "S-022", "S-001", "M-003", "S-004"),
    ("M-037", "S-114", "S-116", "S-115", "Ex-003", "S-141", "S-142", "S-143", "M-045", "S-134", "M-042",
     "S-132", "Ex-056", "Ex-066", "Ex-057", "Ex-067", "Ex-058", "Ex-068", "M-001", "S-001", "P-001", "S-022",
     "M-002", "S-005", "P-002", "S-003", "M-003", "S-004", "S-002", "M-005", "S-009", "S-001"),
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
