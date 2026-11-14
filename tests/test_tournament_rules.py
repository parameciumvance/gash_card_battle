"""大會規則(atwiki「ルール」pages/87「大会ルール」):先攻第 1 回合開始階段翻頁不增加 MP;PR 卡同編號限 1 張。"""

import pytest
from fastapi.testclient import TestClient

from gash.api.app import app
from gash.engine.cards import DATA_DIR, card_db
from gash.engine.deck import DeckError, load_deck, validate_deck
from gash.engine.engine import submit
from gash.engine.state import BATTLE
from tests.test_level2 import book, mk
from tests.test_level3 import ability, events_of

LEVEL1 = list(load_deck(DATA_DIR / "decks/level1.json", card_db()).pages)


def flip(g, player, count):
    return submit(g, {"type": "flip_pages", "player": player, "count": count})


def end_turn(g):
    """非戰鬥中雙方連續 pass,結束目前的回合(含結束階段的強制翻頁)。"""
    st = g.state
    submit(g, {"type": "pass", "player": st.action_player})
    submit(g, {"type": "pass", "player": st.action_player})


# ---------------------------------------------------------------- 先攻の1ターン目はスタートフェイズにページをめくってもMPを増やせない

def test_first_player_first_turn_flip_gains_no_mp():
    g, tp = mk(book("M-001"), book("M-001"))
    st = g.state
    assert st.turn_no == 1 and st.players[tp].mp == 2
    pos = st.players[tp].pos
    events = flip(g, tp, 2)
    assert st.players[tp].pos == pos + 4                    # 頁照翻
    assert st.players[tp].mp == 2                           # MP 不增加
    assert [e["mp_gained"] for e in events_of(events, "pages_flipped")] == [0]
    assert st.phase == BATTLE


def test_first_turn_forced_end_flip_still_gains_mp():
    g, tp = mk(book("M-001"), book("M-001"))
    st = g.state
    flip(g, tp, 1)
    end_turn(g)
    assert st.turn_no == 2 and st.players[tp].mp == 2 + 2   # 結束階段的強制翻頁照常 +2


def test_second_player_first_turn_flip_gains_mp():
    g, tp = mk(book("M-001"), book("M-001"))
    st = g.state
    flip(g, tp, 0)
    end_turn(g)
    opp = 1 - tp
    assert st.turn_player == opp and st.players[opp].mp == 2
    events = flip(g, opp, 2)
    assert st.players[opp].mp == 2 + 4                      # 後攻的第 1 回合(遊戲第 2 回合)照常
    assert [e["mp_gained"] for e in events_of(events, "pages_flipped")] == [4]


def test_third_turn_flip_gains_mp():
    g, tp = mk(book("M-001"), book("M-001"))
    st = g.state
    flip(g, tp, 0)
    end_turn(g)
    flip(g, 1 - tp, 0)
    end_turn(g)
    assert st.turn_no == 3 and st.turn_player == tp
    mp = st.players[tp].mp
    flip(g, tp, 3)
    assert st.players[tp].mp == mp + 6


def test_p035_counts_zero_on_first_turn():
    # P-035「相手がこのターンのスタートフェイズにふやしたＭＰの数×２だけ、相手のＭＰをへらす」:
    # 先攻第 1 回合翻頁沒有增加 MP,對手的 MP 不減少
    g, tp = mk(book("M-001"), book("M-001"))
    st = g.state
    opp = 1 - tp
    st.players[opp].slots[0].partner = "P-035"
    flip(g, tp, 3)
    assert st.players[tp].start_phase_mp_total == 0
    submit(g, {"type": "pass", "player": tp})
    submit(g, ability(opp, st.players[opp].slots[0], zone="partner"))
    assert st.players[tp].mp == 2


# ---------------------------------------------------------------- プロモーションカードは1種類につき1枚まで入れられる

def with_pages(**repl):
    pages = list(LEVEL1)
    for page, number in repl.items():
        pages[int(page[1:]) - 1] = number
    return pages


def test_duplicate_pr_card_rejected():
    pages = with_pages(p2="PR-001", p3="PR-001")
    with pytest.raises(DeckError) as exc:
        validate_deck(pages, card_db())
    assert exc.value.code == "deck.pr_copies"


def test_different_pr_cards_allowed():
    validate_deck(with_pages(p2="PR-001", p12="PR-006"), card_db())


def test_ex_card_not_limited():
    validate_deck(with_pages(p7="Ex-013", p9="Ex-013", p10="Ex-013", p13="Ex-013"), card_db())


def test_create_room_with_duplicate_pr_card_rejected():
    client = TestClient(app)
    res = client.post("/api/rooms", json={"mode": "online", "deck": {"pages": with_pages(p2="PR-001", p3="PR-001")}})
    assert res.status_code == 422 and "deck.pr_copies" in res.text


def test_builder_shows_pr_copies_violation(page):
    # deck-builder「即時合法性提示」:同一張 PR 卡放 2 張顯示違規,移掉後消失
    page.locator("#entry-builder").click()
    page.wait_for_function("document.getElementById('builder-validation').textContent")
    pages = with_pages(p2="PR-001", p3="PR-001")
    msg = page.evaluate("t('deck.err.pr_copies', {card: 'PR-001', n: 2})")
    assert msg != "deck.err.pr_copies"
    page.evaluate("(pages) => { B.deck.pages = pages; renderValidation(); }", pages)
    assert msg in page.locator("#builder-validation").text_content()
    page.evaluate("(pages) => { B.deck.pages = pages; renderValidation(); }", with_pages(p2="PR-001"))
    assert page.locator("#builder-validation .err").count() == 0
