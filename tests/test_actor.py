"""推送標明行動者(battle-api「推送標明行動者」):推送與指令回應帶 actor。"""

import asyncio
import time

from gash.api import app as api
from gash.api.app import (CommandBody, CreateRoom, DebugStateBody, _fire_due_timeouts, create_room,
                          get_debug_state, join_room, post_command, post_debug_state, store)
from gash.engine.awaiting import awaited_player
from tests.test_npc_room import SEED_NPC_FIRST, FakeWS, npc_idle


def actors(ws):
    return [m["actor"] for m in ws.sent if m["type"] == "update"]


def test_player_command_is_marked_with_that_player():
    async def run():
        r = await create_room(CreateRoom(mode="online", seed=3))
        j = await join_room(r["code"])
        room = store.rooms[r["code"]]
        ws0, ws1 = FakeWS(), FakeWS()
        room.sockets += [(ws0, 0), (ws1, 1)]
        tp = room.game.state.turn_player
        token = r["player_token"] if tp == 0 else j["player_token"]
        resp = await post_command(r["code"], CommandBody(command={"type": "flip_pages", "count": 0}),
                                  x_player_token=token)
        return tp, resp, ws0, ws1

    tp, resp, ws0, ws1 = asyncio.run(run())
    assert resp["actor"] == tp
    assert actors(ws0) == [tp] and actors(ws1) == [tp]


def test_npc_and_timeout_are_marked(monkeypatch):
    monkeypatch.setattr(api, "NPC_QUIET_DELAY", 0)
    monkeypatch.setattr(api, "NPC_ACTION_DELAY", 0)

    async def npc():
        body = await create_room(CreateRoom(mode="npc", seed=SEED_NPC_FIRST))
        room = store.rooms[body["code"]]
        ws = FakeWS()
        room.sockets.append((ws, 0))
        await npc_idle(room)
        return ws

    assert set(actors(asyncio.run(npc()))) == {1}

    async def timeout():
        r = await create_room(CreateRoom(mode="online", timer_seconds=30, seed=3))
        await join_room(r["code"])
        room = store.rooms[r["code"]]
        ws = FakeWS()
        room.sockets.append((ws, "spectator"))
        waiting = awaited_player(room.game)
        room.deadline = time.time() - 1
        await _fire_due_timeouts()
        return waiting, ws

    waiting, ws = asyncio.run(timeout())
    assert actors(ws) == [waiting]


def test_cheat_has_no_actor():
    async def run():
        r = await create_room(CreateRoom(mode="local"))
        room = store.rooms[r["code"]]
        ws = FakeWS()
        room.sockets.append((ws, 0))
        token = r["player_tokens"][0]
        players = (await get_debug_state(r["code"], x_player_token=token))["players"]
        await post_debug_state(r["code"], DebugStateBody(players=players), x_player_token=token)
        return ws

    assert actors(asyncio.run(run())) == [None]
