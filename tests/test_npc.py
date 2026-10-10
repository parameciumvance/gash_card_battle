"""NPC 決策測試(npc-opponent spec)。

魔書頁面備忘(level1):P1=M-001 P2=S-025 P3=S-001 P4=P-001 P5=S-001 P6=M-014 P10=S-026
P12=S-003 P13=E-004 ... P32=S-005(最後一頁的戰術費用 0)
"""

import copy
import random

import pytest

from gash import npc
from gash.api.views import filter_events, snapshot
from gash.engine.awaiting import awaited_player, default_command
from gash.engine.cards import DATA_DIR, card_db
from gash.engine.deck import load_deck
from gash.engine.engine import new_game, submit
from gash.engine.state import BOOK_SIZE, GAME_OVER, Game
from gash.npc.candidates import candidates
from gash.npc.determinize import in_use_pages

PRESETS = ("level1", "level2")


def deck(name="level1"):
    return load_deck(DATA_DIR / f"decks/{name}.json", card_db()).pages


def mk(first=0, seed=1, decks=("level1", "level1")):
    g = new_game(deck(decks[0]), seed=seed, decks=(list(deck(decks[0])), list(deck(decks[1]))))
    g.state.turn_player = first
    return g


def top_choice(g, player, seed=0):
    return npc.decide(g, player, "normal", random.Random(seed))[0]


def decision_point(g):
    st = g.state
    if st.pending is not None:
        return "pending"
    if st.phase == "start":
        return "start"
    if st.battle_in is not None:
        return "battle_in"
    return st.battle.step if st.battle is not None else "action"


def play_out(levels, decks, seed, on_decision=None, log=None, max_commands=3000):
    """雙方都由 NPC 操作直到對局結束。on_decision(game, player) 在每個決策點(送出前)呼叫;
    log 收集 (難度, 決策點, 首選, 實際送出的指令)。"""
    g = new_game(deck(decks[0]), seed=seed, decks=(list(deck(decks[0])), list(deck(decks[1]))))
    rngs = [random.Random(f"{seed}:{p}") for p in (0, 1)]
    for _ in range(max_commands):
        if g.state.phase == GAME_OVER:
            return g
        p = awaited_player(g)
        if on_decision is not None:
            on_decision(g, p)
        point = decision_point(g)
        ranked = npc.decide(g, p, levels[p], rngs[p])
        result = npc.submit_ranked(g, p, ranked)
        assert result is not None
        if log is not None:
            log.append((levels[p], point, ranked[0], result[0]))
    pytest.fail("對局沒有在指令上限內結束")


LEVEL_PAIRS = (("normal", "normal"), ("normal", "dummy"), ("dummy", "normal"), ("dummy", "dummy"))


@pytest.fixture(scope="module")
def selfplay():
    """任一難度組合 × 各預組 × 多個 seed 的自我對戰:[(難度組合, 對局, 決策記錄)]。"""
    games = []
    for levels in LEVEL_PAIRS:
        for seed in (1, 2):
            for decks in (("level1", "level2"), ("level2", "level1")):
                log = []
                games.append((levels, play_out(levels, decks, seed, log=log), log))
    return games


# ---------------------------------------------------------------- 只依自己看得到的資訊決策

def _hide_variant(g: Game, viewer: int, rng: random.Random) -> Game:
    """換掉 viewer 看不到的一切:對手魔書未公開頁、對局 RNG、只給對手的事件內容。
    逐頁替換後確認 viewer 的快照不變,會改變快照的頁(例如本回合用過的戰術頁)則換回。"""
    v = Game(state=copy.deepcopy(g.state), rng=random.Random(rng.getrandbits(64)), db=g.db,
             events=copy.deepcopy(g.events), jammer=copy.deepcopy(g.jammer))
    opp = 1 - viewer
    base = snapshot(g, viewer)
    public = v.state.players[opp].consumed_pages | in_use_pages(v, opp)
    numbers = sorted(g.db)
    for page in range(1, BOOK_SIZE + 1):
        if page in public:
            continue
        book = v.state.players[opp].book
        old = book[page - 1]
        book[page - 1] = rng.choice(numbers)
        if snapshot(v, viewer) != base:
            book[page - 1] = old
        elif v.jammer is not None:
            v.jammer["snapshot"].players[opp].book[page - 1] = book[page - 1]
    for ev in v.events:
        if ev["type"] in ("book_revealed", "pages_peeked") and ev.get("viewer") != viewer:
            ev["cards"] = []
        if ev["type"] == "choice_required" and ev.get("player") != viewer:
            ev["options"] = []
    assert snapshot(v, viewer) == base
    assert filter_events(v.events, viewer) == filter_events(g.events, viewer)
    return v


def test_hidden_information_never_changes_decisions():
    """自我對戰的決策點(每 3 個取 1 個):換掉 NPC 看不到的資訊,NPC 的決定(整個排序)不變。"""
    seen, checked = [], []
    rng = random.Random(7)

    def check(g, p):
        seen.append(p)
        if len(seen) % 3:
            return
        v = _hide_variant(g, p, rng)
        assert npc.decide(v, p, "normal", random.Random(1)) == npc.decide(g, p, "normal", random.Random(1))
        checked.append(decision_point(g))

    for seed, decks in ((1, ("level1", "level2")), (2, ("level2", "level1"))):
        play_out(("normal", "normal"), decks, seed, on_decision=check)
    assert {"start", "action", "defense", "pending"} <= set(checked)


def test_opponent_open_pages_do_not_change_decision():
    """NPC 的回合、可以攻擊時:對手翻開頁是防禦戰術或不是,NPC 的決定相同。"""
    variants = []
    for opp_pages in (("S-003", "S-003"), ("E-004", "M-012")):
        g = mk(first=0)
        submit(g, {"type": "flip_pages", "player": 0, "count": 1})     # 翻開 P4=P-001、P5=S-001
        opp = g.state.players[1]
        opp.book[1], opp.book[2] = opp_pages                            # 對手翻開頁 P2、P3
        assert g.state.action_player == 0
        variants.append(npc.decide(g, 0, "normal", random.Random(3)))
    assert variants[0] == variants[1]


def test_coin_result_does_not_change_decision():
    """NPC 可使用 E-005(擲 2 次:正正退回魔書、反反前翻魔書)時:接下來的擲幣是正正或反反,決定相同。"""
    def next_flips(seed):
        rng = random.Random(seed)
        return rng.random() < 0.5, rng.random() < 0.5
    both_heads = next(s for s in range(100) if next_flips(s) == (True, True))
    both_tails = next(s for s in range(100) if next_flips(s) == (False, False))
    decisions = []
    for seed in (both_heads, both_tails):
        g = mk(first=0)
        submit(g, {"type": "flip_pages", "player": 0, "count": 0})
        g.state.players[0].pos = 10
        g.state.players[0].book[9] = "E-005"                            # 翻開 P10=E-005、P11=S-001
        g.rng = random.Random(seed)
        assert {"type": "use_book_card", "page": 10} in candidates(g, 0)
        decisions.append(npc.decide(g, 0, "normal", random.Random(5)))
    assert decisions[0] == decisions[1]


# ---------------------------------------------------------------- 不會卡住對局

def test_all_level_pairs_finish_every_game(selfplay):
    """每局都以勝負結束;引擎沒有拋出拒絕以外的例外(否則 fixture 本身失敗)。"""
    assert len(selfplay) == 16
    assert all(g.state.winner in (0, 1) for _, g, _ in selfplay)


def test_every_decision_point_gets_an_accepted_command(selfplay):
    """開始階段、行動權、戰鬥開始確認、防禦、戰鬥中效果與中途決策都出現過,且首選都被引擎接受。"""
    log = [entry for _, _, game_log in selfplay for entry in game_log]
    assert {point for _, point, _, _ in log} >= {"start", "action", "battle_in", "defense", "effects", "pending"}
    assert [entry for entry in log if entry[2] != entry[3]] == []


def test_rejected_first_choice_falls_back_to_next_and_default():
    g = mk(first=0)
    illegal = {"type": "play_card", "page": 99, "player": 0}
    cmd, events = npc.submit_ranked(g, 0, [illegal, {"type": "flip_pages", "count": 2, "player": 0}])
    assert cmd["count"] == 2 and g.state.players[0].pos == 6
    cmd, events = npc.submit_ranked(g, 0, [illegal])                    # 全部被拒 → 安全預設
    assert cmd == {"type": "pass", "player": 0}
    assert events[-1]["type"] == "passed"


# ---------------------------------------------------------------- 難度

def test_dummy_sends_the_timeout_default():
    g = mk(first=0)
    for _ in range(40):
        if g.state.phase == GAME_OVER:
            break
        p = awaited_player(g)
        ranked = npc.decide(g, p, "dummy", random.Random(0))
        assert ranked == [{**default_command(g), "player": p}]
        npc.submit_ranked(g, p, ranked)


def test_dummy_never_acts(selfplay):
    """木人樁:翻 0 張、pass;對手攻擊時迎戰且不防禦。"""
    sent = [cmd for _, _, log in selfplay for level, _, _, cmd in log if level == "dummy"]
    assert {c["type"] for c in sent} <= {"flip_pages", "pass", "battle_in_response", "no_defense", "choose"}
    assert all(c["count"] == 0 for c in sent if c["type"] == "flip_pages")
    assert {"battle_in_response", "no_defense"} <= {c["type"] for c in sent}


def test_normal_acts_and_beats_dummy(selfplay):
    sent = [cmd for _, _, log in selfplay for level, _, _, cmd in log if level == "normal"]
    assert {"play_card", "declare_attack", "declare_defense"} <= {c["type"] for c in sent}
    assert any(c["type"] == "flip_pages" and c["count"] > 0 for c in sent)
    results = [(levels[g.state.winner] == "normal") for levels, g, _ in selfplay
               if set(levels) == {"normal", "dummy"}]
    assert sum(results) > len(results) / 2


# ---------------------------------------------------------------- 一般難度的基本判斷

def _attack_on(npc_player_pos, *, no_protect_book=False):
    """玩家 0 以 S-001(ガッシュ 4000 + 2000)攻擊 NPC(玩家 1);停在 NPC 的防禦宣告。"""
    g = mk(first=0)
    g.state.players[1].pos = npc_player_pos
    submit(g, {"type": "flip_pages", "player": 0, "count": 1})
    submit(g, {"type": "declare_attack", "player": 0, "page": 5})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    if no_protect_book:
        g.state.battle.data["no_protect_book"] = True
    assert g.state.battle.step == "defense" and awaited_player(g) == 1
    return g


def test_protects_against_lethal_book_damage():
    g = _attack_on(32)                                                  # 再受 1 點魔書傷害即耗盡
    submit(g, {"type": "no_defense", "player": 1})
    submit(g, {"type": "pass", "player": 0})
    submit(g, {"type": "pass", "player": 1})
    assert g.state.pending.kind == "protect" and g.state.pending.player == 1
    gash = g.state.players[1].slots[0].uid
    assert top_choice(g, 1) == {"type": "choose", "value": gash, "player": 1}


def test_defends_when_no_defense_loses():
    g = _attack_on(32, no_protect_book=True)                            # P32=S-005 費用 0,合計 10000
    choice = top_choice(g, 1)
    assert choice["type"] == "declare_defense" and choice["page"] == 32
    submit(g, choice)
    submit(g, {"type": "pass", "player": 0})
    submit(g, {"type": "pass", "player": 1})
    assert g.state.phase != GAME_OVER


def test_attacks_when_it_can_win():
    g = mk(first=0)
    submit(g, {"type": "flip_pages", "player": 0, "count": 1})         # 翻開 P5=S-001(傷害 1)
    opp = g.state.players[1]
    opp.pos, opp.mp = 32, 0                                             # 再受 1 點魔書傷害即耗盡
    opp.slots[0].injured = True
    assert g.state.action_player == 0
    choice = top_choice(g, 0)
    assert choice["type"] == "declare_attack" and choice["page"] == 5


# ---------------------------------------------------------------- 可重現

def test_same_seed_same_game():
    runs = [play_out(("normal", "normal"), ("level1", "level2"), 4).events for _ in range(2)]
    assert runs[0] == runs[1]


def test_npc_considers_borrowed_partner_effect():
    # E-010 借用後,NPC 的候選含 use_borrowed_effect 且引擎接受;用過之後不再列出
    from gash.engine.state import MamodoSlot
    g = mk(first=0)
    st = g.state
    st.players[0].book[1] = "E-010"
    st.players[0].mp = 6
    st.players[1].mp = 5
    st.players[1].slots.append(MamodoSlot(uid=st.next_uid(), stack=["M-004"], partner="P-002"))
    submit(g, {"type": "flip_pages", "player": 0, "count": 0})
    submit(g, {"type": "use_book_card", "player": 0, "page": 2})
    submit(g, {"type": "pass", "player": 1})
    assert {"type": "use_borrowed_effect"} in candidates(g, 0)
    assert top_choice(g, 0)["type"] == "use_borrowed_effect"        # P-002:MP 轉移對自己有利
    submit(g, {"type": "use_borrowed_effect", "player": 0})
    submit(g, {"type": "pass", "player": 1})
    assert {"type": "use_borrowed_effect"} not in candidates(g, 0)
