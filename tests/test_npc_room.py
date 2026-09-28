"""NPC 房測試(online-room「建立房間」「NPC 房」「NPC 座位的驅動」、local-test-mode 金手指)。

端點以函式直接呼叫並在同一個 event loop 中等待 NPC 驅動 task;NPC 送出前的等待設為 0。
"""

import asyncio

import pytest
from fastapi import HTTPException

from gash.api import app as api
from gash.api.app import (CommandBody, CreateRoom, DebugStateBody, JoinBody, create_room, get_debug_state,
                          get_state, join_room, post_command, post_debug_state, store)
from gash.engine.awaiting import awaited_player, default_command
from gash.engine.cards import DATA_DIR, card_db
from gash.engine.deck import load_deck
from gash.engine.engine import _game_over, new_game
from gash.engine.state import GAME_OVER

LEVEL1 = list(load_deck(DATA_DIR / "decks/level1.json", card_db()).pages)
LEVEL2 = list(load_deck(DATA_DIR / "decks/level2.json", card_db()).pages)


@pytest.fixture(autouse=True)
def no_npc_delay(monkeypatch):
    monkeypatch.setattr(api, "NPC_QUIET_DELAY", 0)
    monkeypatch.setattr(api, "NPC_ACTION_DELAY", 0)


def first_player(seed):
    return new_game(LEVEL1, seed=seed).state.turn_player


SEED_PLAYER_FIRST = next(s for s in range(50) if first_player(s) == 0)
SEED_NPC_FIRST = next(s for s in range(50) if first_player(s) == 1)


async def npc_idle(room):
    """等 NPC 驅動跑完(輪到玩家或對局結束)。"""
    while room.npc.task is not None and not room.npc.task.done():
        await room.npc.task


async def new_npc_room(**kw):
    kw.setdefault("seed", SEED_PLAYER_FIRST)
    body = await create_room(CreateRoom(mode="npc", **kw))
    room = store.rooms[body["code"]]
    await npc_idle(room)
    return body, room


async def send(room, token, command):
    return await post_command(room.code, CommandBody(command=command), x_player_token=token)


def rejected(coro_fn, status=422):
    async def run():
        with pytest.raises(HTTPException) as exc:
            await coro_fn()
        return exc.value
    exc = asyncio.run(run())
    assert exc.status_code == status
    return exc.detail["code"]


class FakeWS:
    def __init__(self):
        self.sent = []

    async def send_json(self, data):
        self.sent.append(data)


# ---------------------------------------------------------------- 建立 NPC 房

def test_npc_room_starts_immediately_with_one_token():
    body, room = asyncio.run(new_npc_room(timer_seconds=60))
    assert set(body) >= {"code", "player_token", "spectate_url", "state", "room"}
    assert "join_url" not in body and "player_tokens" not in body
    assert body["room"]["started"] is True
    assert body["room"]["npc"] == {"seat": 1, "level": "normal", "deck": None}
    assert room.timer_seconds is None and room.deadline is None            # 不計時
    assert list(room.player_tokens.values()) == [0]


def test_npc_level_and_validation():
    _, room = asyncio.run(new_npc_room(npc_level="dummy"))
    assert room.npc.level == "dummy"
    before = len(store.rooms)
    assert rejected(lambda: create_room(CreateRoom(mode="npc", npc_level="hard"))) == "npc.bad_level"
    assert rejected(lambda: create_room(CreateRoom(
        mode="npc", npc_deck={"preset": "level1"}, npc_decks=[{"preset": "level2"}]))) == "npc.deck_conflict"
    assert rejected(lambda: create_room(CreateRoom(mode="npc", npc_decks=[]))) == "npc.bad_decks"
    bad = LEVEL1[:2] + ["S-005"] + LEVEL1[3:]                               # 上級卡在第 3 頁
    assert rejected(lambda: create_room(CreateRoom(
        mode="npc", npc_deck={"pages": bad}))) == "deck.superior_page"
    assert rejected(lambda: create_room(CreateRoom(
        mode="npc", npc_decks=[{"preset": "level2"}, {"pages": bad}]))) == "deck.superior_page"
    assert len(store.rooms) == before


def test_specified_npc_deck():
    _, room = asyncio.run(new_npc_room(npc_deck={"preset": "level2"}))
    assert room.game.state.players[1].book == LEVEL2
    _, room = asyncio.run(new_npc_room(npc_deck={"pages": LEVEL2}, deck={"preset": "level2"}))
    assert room.game.state.players[1].book == LEVEL2


def test_random_npc_deck_is_drawn_from_candidates_by_seed():
    candidates = [{"preset": "level1"}, {"preset": "level2"}, {"pages": LEVEL1}]

    def drawn(seed):
        _, room = asyncio.run(new_npc_room(seed=seed, npc_decks=candidates, npc_level="dummy"))
        return room.game.state.players[1].book, room.npc.deck

    assert drawn(3) == drawn(3)                                             # 相同 seed 抽到同一副
    draws = [drawn(s) for s in range(12)]
    assert all(label in candidates for _, label in draws)
    assert all(book == (LEVEL2 if label == {"preset": "level2"} else LEVEL1) for book, label in draws)
    assert len({str(label) for _, label in draws}) >= 2


def test_npc_deck_hidden_until_game_over():
    body, room = asyncio.run(new_npc_room(npc_decks=[{"preset": "level2"}]))
    token = body["player_token"]
    state = asyncio.run(get_state(room.code, x_player_token=token))
    assert state["room"]["npc"]["deck"] is None
    assert all("card" not in p for p in state["state"]["players"][1]["open_pages"])
    _game_over(room.game, [], 0, "book_out")
    state = asyncio.run(get_state(room.code, x_player_token=token))
    assert state["room"]["npc"]["deck"] == {"preset": "level2"}


def test_npc_room_not_joinable():
    body, room = asyncio.run(new_npc_room())
    assert rejected(lambda: join_room(room.code, JoinBody()), status=409) == "room.not_joinable"


# ---------------------------------------------------------------- NPC 驅動

def test_npc_takes_over_after_player_command():
    async def run():
        body, room = await new_npc_room(seed=SEED_PLAYER_FIRST)
        token = body["player_token"]
        assert awaited_player(room.game) == 0
        ws = FakeWS()
        room.sockets.append((ws, 0))
        await send(room, token, {"type": "flip_pages", "count": 0})
        await send(room, token, {"type": "pass"})
        await npc_idle(room)
        return room, ws

    room, ws = asyncio.run(run())
    npc_events = [e for m in ws.sent for e in m["events"] if e.get("player") == 1]
    assert npc_events, "NPC 的行動應推送給玩家"
    assert room.game.state.phase == GAME_OVER or awaited_player(room.game) == 0


def test_npc_moving_first_plays_until_player_turn():
    _, room = asyncio.run(new_npc_room(seed=SEED_NPC_FIRST))
    assert {"type": "phase_changed", "phase": "battle", "turn": 1} in [
        {k: e.get(k) for k in ("type", "phase", "turn")} for e in room.game.events]   # NPC 走完開始階段
    assert room.game.state.phase == GAME_OVER or awaited_player(room.game) == 0


def play_player_defaults(room, token, until=lambda room: False, max_commands=2000):
    """玩家一律送安全預設,直到對局結束或 until 成立;每步之後等 NPC 跑完。"""
    async def run():
        await npc_idle(room)
        for _ in range(max_commands):
            if room.game.state.phase == GAME_OVER or until(room):
                return
            assert awaited_player(room.game) == 0
            await send(room, token, default_command(room.game))
            await npc_idle(room)
        pytest.fail("對局沒有在指令上限內結束")
    asyncio.run(run())


def test_npc_pauses_longer_before_actions(monkeypatch):
    pauses, sent = [], []
    monkeypatch.setattr(api, "NPC_QUIET_DELAY", 0.001)
    monkeypatch.setattr(api, "NPC_ACTION_DELAY", 0.002)

    async def pause(seconds):
        pauses.append(seconds)

    def submit_ranked(game, player, ranked):
        result = api_submit_ranked(game, player, ranked)
        sent.append(result[0]["type"])
        return result

    api_submit_ranked = api.submit_ranked
    monkeypatch.setattr(api, "_npc_pause", pause)
    monkeypatch.setattr(api, "submit_ranked", submit_ranked)
    body, room = asyncio.run(new_npc_room())
    play_player_defaults(room, body["player_token"],
                         until=lambda room: "declare_attack" in sent and "pass" in sent)
    pairs = list(zip(pauses, sent))
    assert (0.001, "pass") in pairs and (0.002, "declare_attack") in pairs
    assert all(delay == 0.001 for delay, kind in pairs if kind in ("pass", "battle_in_response", "no_defense"))


def test_npc_redecides_when_cheat_applied_during_pause(monkeypatch):
    seen_mp = []
    rooms = []

    def decide(game, player, level, rng):
        seen_mp.append(game.state.players[1].mp)
        return api_decide(game, player, level, rng)

    async def pause(seconds):
        if len(seen_mp) == 1:                                               # 第一次等待中套用金手指
            room, token = rooms[0]
            players = (await get_debug_state(room.code, x_player_token=token))["players"]
            players[1]["mp"] = 20
            await post_debug_state(room.code, DebugStateBody(players=players), x_player_token=token)

    async def run():
        body = await create_room(CreateRoom(mode="npc", seed=SEED_NPC_FIRST, npc_level="dummy"))
        room = store.rooms[body["code"]]
        rooms.append((room, body["player_token"]))
        await npc_idle(room)
        return room

    api_decide = api.decide
    monkeypatch.setattr(api, "decide", decide)
    monkeypatch.setattr(api, "_npc_pause", pause)
    room = asyncio.run(run())
    assert seen_mp[:2] == [2, 20]                                           # 套用後以新局面重新決定
    assert any(e["type"] == "cheat_applied" for e in room.game.events)


def test_single_driver_per_room():
    async def run():
        body = await create_room(CreateRoom(mode="npc", seed=SEED_NPC_FIRST))
        room = store.rooms[body["code"]]
        task = room.npc.task
        api._kick_npc(room)
        api._kick_npc(room)
        assert room.npc.task is task
        await npc_idle(room)
        return room
    room = asyncio.run(run())
    assert room.game.state.phase == GAME_OVER or awaited_player(room.game) == 0


def test_same_seed_and_player_commands_give_same_game():
    runs = []
    for _ in range(2):
        body, room = asyncio.run(new_npc_room(seed=11, npc_deck={"preset": "level2"}))
        play_player_defaults(room, body["player_token"])
        runs.append(room.game.events)
    assert runs[0] == runs[1]


# ---------------------------------------------------------------- 金手指

def test_cheat_in_npc_room_reads_and_writes_npc_book():
    body, room = asyncio.run(new_npc_room())
    token = body["player_token"]
    players = asyncio.run(get_debug_state(room.code, x_player_token=token))["players"]
    assert players[1]["book"] == LEVEL1
    players[1]["book"][20] = "S-017"
    asyncio.run(post_debug_state(room.code, DebugStateBody(players=players), x_player_token=token))
    assert room.game.state.players[1].book[20] == "S-017"


def test_spectators_cannot_use_cheat():
    local = asyncio.run(create_room(CreateRoom(mode="local")))
    npc_body, npc_room = asyncio.run(new_npc_room())
    for code in (local["code"], npc_body["code"]):
        spectator = store.rooms[code].spectator_token
        assert rejected(lambda: get_debug_state(code, x_player_token=spectator), status=403) == "room.spectator"
        players = [{"book": LEVEL1, "mp": 0}, {"book": LEVEL1, "mp": 0}]
        assert rejected(lambda: post_debug_state(code, DebugStateBody(players=players),
                                                 x_player_token=spectator), status=403) == "room.spectator"
