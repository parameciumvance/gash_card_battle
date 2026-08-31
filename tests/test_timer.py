"""回合計時器測試:等待者推導、逾時代打安全預設、deadline 管理。"""

import asyncio
import time

from gash.api.app import CreateRoom, _fire_due_timeouts, create_room, join_room, post_command, store
from gash.api.app import CommandBody
from gash.api.rooms import awaited_player, default_command
from gash.engine.cards import DATA_DIR, card_db
from gash.engine.deck import load_deck
from gash.engine.engine import new_game, submit
from gash.engine.state import GAME_OVER


def mk_engine():
    deck = load_deck(DATA_DIR / "decks/level1.json", card_db())
    g = new_game(deck.pages, seed=1)
    g.state.turn_player = 0
    return g


# ---------------------------------------------------------------- 等待者與預設指令

def test_awaited_and_default_through_states():
    g = mk_engine()
    # 開始階段 → 回合玩家、flip 0
    assert awaited_player(g) == 0
    assert default_command(g) == {"type": "flip_pages", "count": 0}
    submit(g, {"type": "flip_pages", "player": 0, "count": 0})
    # 非戰鬥 → action_player、pass
    assert awaited_player(g) == 0
    assert default_command(g) == {"type": "pass"}
    # 戰鬥開始確認 → 防方、迎戰
    submit(g, {"type": "declare_attack", "player": 0, "page": 3})
    assert awaited_player(g) == 1
    assert default_command(g) == {"type": "battle_in_response", "allow": True}
    submit(g, {"type": "battle_in_response", "player": 1, "allow": True})
    # 防禦步 → 防方、不防禦
    assert awaited_player(g) == 1
    assert default_command(g) == {"type": "no_defense"}
    submit(g, {"type": "no_defense", "player": 1})
    # 效果步 → effect_turn、pass
    assert awaited_player(g) == 0
    assert default_command(g) == {"type": "pass"}
    submit(g, {"type": "pass", "player": 0})
    submit(g, {"type": "pass", "player": 1})
    # 保護 pending → 受方、不保護
    assert g.state.pending.kind == "protect"
    assert awaited_player(g) == 1
    assert default_command(g) == {"type": "choose", "value": None}


def test_default_commands_can_finish_a_game():
    """只靠安全預設指令,對局必然推進到結束(不卡死)。"""
    g = mk_engine()
    for _ in range(3000):
        if g.state.phase == GAME_OVER:
            break
        p = awaited_player(g)
        c = default_command(g)
        c["player"] = p
        submit(g, c)
    assert g.state.phase == GAME_OVER


# ---------------------------------------------------------------- 逾時代打(API 層)

def test_timeout_fires_and_marks_events():
    async def run():
        r = await create_room(CreateRoom(mode="online", timer_seconds=30, seed=3))
        j = await join_room(r["code"])
        room = store.rooms[r["code"]]
        assert room.deadline is not None  # 開局即開始計時
        room.deadline = time.time() - 1   # 模擬逾時
        n_before = len(room.game.events)
        await _fire_due_timeouts()
        return room, n_before

    room, n_before = asyncio.run(run())
    new_events = room.game.events[n_before:]
    assert new_events, "逾時應代送指令產生事件"
    assert all(e.get("timeout") for e in new_events)
    assert room.game.state.phase == "battle"  # 開始階段被代打 flip 0
    assert room.deadline is not None and room.deadline > time.time()  # 期限已重置


def test_timer_disabled_no_deadline():
    async def run():
        r = await create_room(CreateRoom(mode="online", timer_seconds=None, seed=3))
        await join_room(r["code"])
        room = store.rooms[r["code"]]
        tp = room.game.state.turn_player
        token_tp = next(t for t, p in room.player_tokens.items() if p == tp)
        await post_command(r["code"], CommandBody(command={"type": "flip_pages", "count": 0}),
                           x_player_token=token_tp)
        return room

    room = asyncio.run(run())
    assert room.deadline is None
    n = len(room.game.events)
    asyncio.run(_fire_due_timeouts())
    assert len(room.game.events) == n  # 不代打


def test_deadline_resets_on_real_command():
    async def run():
        r = await create_room(CreateRoom(mode="online", timer_seconds=60, seed=3))
        await join_room(r["code"])
        room = store.rooms[r["code"]]
        first_deadline = room.deadline
        room.deadline -= 30  # 假裝時間流逝
        tp = room.game.state.turn_player
        token_tp = next(t for t, p in room.player_tokens.items() if p == tp)
        await post_command(r["code"], CommandBody(command={"type": "flip_pages", "count": 1}),
                           x_player_token=token_tp)
        return room

    room = asyncio.run(run())
    assert room.deadline >= time.time() + 55  # 出招後重置為完整時限
