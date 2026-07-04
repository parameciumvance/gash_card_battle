"""全流程劇本測試(tasks 6.2):雙方使用 level1 預組魔本,
以合法指令串完整走過:放卡、夥伴待命(P-001 不可防禦)、庇護、
最後一頁バオウ・ザケルガ費用 0、魔本耗盡勝負判定。

魔本頁面備忘:P1=M-001 P2=S-025 P3=S-001 P4=P-001 P5=S-001 P6=M-014 ... P32=S-005
"""

from gash.engine.cards import DATA_DIR, card_db
from gash.engine.deck import load_deck
from gash.engine.engine import IllegalCommand, new_game, spell_cost, submit
from gash.engine.state import GAME_OVER

import pytest


def test_story_full_game():
    deck = load_deck(DATA_DIR / "decks/level1.json", card_db())
    g = new_game(deck.pages, seed=1)
    g.state.turn_player = 0

    # ---- 第 1 回合(玩家0):放夥伴 → P-001 待命 → 不可防禦的攻擊 → 對手庇護
    submit(g, {"type": "flip_pages", "player": 0, "count": 1})   # pos=4, mp=4
    submit(g, {"type": "play_card", "player": 0, "page": 4})     # P-001 裝到賈修
    submit(g, {"type": "pass", "player": 1})
    submit(g, {"type": "use_field_ability", "player": 0, "zone": "partner",
               "slot_uid": g.state.players[0].slots[0].uid})     # 棄掉 → 待命
    assert "P-001" in g.state.players[0].discard
    submit(g, {"type": "pass", "player": 1})
    submit(g, {"type": "declare_attack", "player": 0, "page": 5})  # S-001
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    assert g.state.battle.attack_undefendable is True
    with pytest.raises(IllegalCommand) as exc:                   # 防禦被拒
        submit(g, {"type": "declare_defense", "player": 1, "page": 2})
    assert exc.value.code == "defense.undefendable"
    submit(g, {"type": "no_defense", "player": 1})
    submit(g, {"type": "pass", "player": 0})
    submit(g, {"type": "pass", "player": 1})
    zatch1 = g.state.players[1].slots[0]
    submit(g, {"type": "choose", "player": 1, "value": zatch1.uid})  # 以賈修庇護
    assert zatch1.injured and g.state.players[1].pos == 2         # 魔本無傷
    submit(g, {"type": "pass", "player": 0})
    submit(g, {"type": "pass", "player": 1})                      # 結束階段
    assert g.state.turn_no == 2 and g.state.turn_player == 1
    assert g.state.players[0].pos == 6                            # 強制翻頁

    # ---- 第 2 回合(玩家1):放出蒂歐
    submit(g, {"type": "flip_pages", "player": 1, "count": 2})    # pos=6
    submit(g, {"type": "play_card", "player": 1, "page": 6})      # M-014
    assert len(g.state.players[1].slots) == 2
    submit(g, {"type": "pass", "player": 0})
    submit(g, {"type": "pass", "player": 1})
    with pytest.raises(IllegalCommand):
        submit(g, {"type": "pass", "player": 1})                  # 已換回合:非法
    assert g.state.turn_no == 3 and g.state.turn_player == 0

    # ---- 第 3 回合(玩家0):快轉至魔本末頁,驗證最後一頁費用 0 與致勝斬殺
    g.state.players[0].pos = 30                                   # 測試快轉
    g.state.players[1].pos = 28
    submit(g, {"type": "flip_pages", "player": 0, "count": 1})    # pos=32(最後一頁)
    assert spell_cost(g, 0, 32, g.db["S-005"]) == 0               # バオウ費 6 → 0
    mp_before = g.state.players[0].mp
    submit(g, {"type": "declare_attack", "player": 0, "page": 32})
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    assert g.state.players[0].mp == mp_before                     # 未扣 MP
    submit(g, {"type": "no_defense", "player": 1})
    submit(g, {"type": "pass", "player": 0})
    submit(g, {"type": "pass", "player": 1})
    # 巴歐 10000 vs 0,傷害 3:對手不庇護 → pos 28+6=34 → 魔本耗盡
    submit(g, {"type": "choose", "player": 1, "value": None})
    assert g.state.phase == GAME_OVER
    assert g.state.winner == 0
    assert g.state.end_reason == "book_out"
    ended = g.events[-1]
    assert ended["type"] == "game_ended" and ended["winner"] == 0
