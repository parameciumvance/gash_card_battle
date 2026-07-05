"""FastAPI 薄殼:房間生命週期、token 鑑別、指令轉發、視角化快照與 WebSocket 推送。

引擎為唯一規則權威;所有輸出經 views.py 視角過濾;逾時代打走同一條指令路徑。
"""

from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ..engine.cards import DATA_DIR, card_db
from ..engine.deck import load_deck
from ..engine.engine import IllegalCommand, new_game, submit
from .rooms import Room, RoomError, RoomStore, awaited_player, default_command
from .views import filter_events, snapshot

ROOT = Path(__file__).resolve().parents[3]
FRONTEND_DIR = ROOT / "frontend"

store = RoomStore()
_locks: dict[str, asyncio.Lock] = {}


def _lock(code: str) -> asyncio.Lock:
    return _locks.setdefault(code, asyncio.Lock())


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_timeout_loop())
    yield
    task.cancel()


app = FastAPI(title="gash-card-battle", lifespan=lifespan)


class CreateRoom(BaseModel):
    mode: str = "online"
    timer_seconds: int | None = None
    seed: int | None = None
    deck: str = "level1"


class CommandBody(BaseModel):
    command: dict


# ---------------------------------------------------------------- 輔助

def _http_error(exc: RoomError) -> HTTPException:
    return HTTPException(exc.status, detail={"code": exc.code, "message": str(exc)})


def _effective_viewer(room: Room, viewer):
    """本機模式的 client 持有雙方 token → 回應與推送採全視角。"""
    if room.mode == "local" and viewer != "spectator":
        return "all"
    return viewer


def _room_meta(room: Room, viewer) -> dict:
    return {
        "code": room.code,
        "mode": room.mode,
        "timer_seconds": room.timer_seconds,
        "deadline": room.deadline,
        "server_time": time.time(),
        "players_joined": room.player_count(),
        "started": room.game is not None,
        "you": viewer,
        "awaited_player": awaited_player(room.game) if room.game else None,
    }


def _state_payload(room: Room, viewer) -> dict:
    ev = _effective_viewer(room, viewer)
    payload = {"room": _room_meta(room, viewer)}
    if room.game is not None:
        payload["state"] = snapshot(room.game, ev)
    return payload


def _start_game(room: Room) -> None:
    deck = load_deck(DATA_DIR / "decks/level1.json", card_db())
    room.game = new_game(deck.pages, seed=room.seed)
    room.reset_deadline()


async def _broadcast(room: Room, events: list[dict]) -> None:
    for ws, viewer in list(room.sockets):
        ev = _effective_viewer(room, viewer)
        try:
            await ws.send_json({
                "type": "update",
                "events": filter_events(events, ev),
                **_state_payload(room, viewer),
            })
        except Exception:
            try:
                room.sockets.remove((ws, viewer))
            except ValueError:
                pass


def _resolve(code: str, token: str | None) -> tuple[Room, int | str]:
    try:
        room = store.get(code)
        viewer = room.viewer_of(token or "")
    except RoomError as exc:
        raise _http_error(exc)
    return room, viewer


# ---------------------------------------------------------------- 房間端點

@app.post("/api/rooms")
async def create_room(body: CreateRoom):
    try:
        room, token0 = store.create(body.mode, body.timer_seconds, body.seed)
    except RoomError as exc:
        raise _http_error(exc)
    resp: dict = {
        "code": room.code,
        "mode": room.mode,
        "spectate_url": f"/?spectate={room.code}&token={room.spectator_token}",
    }
    if room.mode == "local":
        import secrets
        token1 = secrets.token_hex(12)
        room.player_tokens[token1] = 1
        _start_game(room)
        resp["player_tokens"] = [token0, token1]
        resp["events"] = filter_events(room.game.events, "all")
        resp.update(_state_payload(room, 0))
    else:
        resp["player_token"] = token0
        resp["join_url"] = f"/?join={room.code}"
        resp.update(_state_payload(room, 0))
    return resp


@app.post("/api/rooms/{code}/join")
async def join_room(code: str):
    try:
        room, token1 = store.join(code)
    except RoomError as exc:
        raise _http_error(exc)
    async with _lock(room.code):
        if room.game is None:
            _start_game(room)
    await _broadcast(room, room.game.events)
    return {
        "player_token": token1,
        "events": filter_events(room.game.events, 1),
        **_state_payload(room, 1),
    }


@app.post("/api/rooms/{code}/commands")
async def post_command(code: str, body: CommandBody,
                       x_player_token: str | None = Header(default=None)):
    room, viewer = _resolve(code, x_player_token)
    if viewer == "spectator":
        raise HTTPException(403, detail={"code": "room.spectator", "message": "觀戰者不能提交指令"})
    if room.game is None:
        raise HTTPException(409, detail={"code": "room.waiting", "message": "等待對手加入"})
    async with _lock(room.code):
        command = dict(body.command)
        command["player"] = viewer  # token 即身分:忽略 payload 自報的 player
        try:
            events = submit(room.game, command)
        except IllegalCommand as exc:
            raise HTTPException(400, detail={"code": exc.code, "message": str(exc)})
        room.touch()
        room.reset_deadline()
    await _broadcast(room, events)
    ev = _effective_viewer(room, viewer)
    return {"events": filter_events(events, ev), **_state_payload(room, viewer)}


@app.get("/api/rooms/{code}/state")
async def get_state(code: str, x_player_token: str | None = Header(default=None)):
    room, viewer = _resolve(code, x_player_token)
    return _state_payload(room, viewer)


@app.get("/api/rooms/{code}/events")
async def get_events(code: str, since: int = 0,
                     x_player_token: str | None = Header(default=None)):
    room, viewer = _resolve(code, x_player_token)
    if room.game is None:
        return {"events": [], "next": 0}
    ev = _effective_viewer(room, viewer)
    return {"events": filter_events(room.game.events[since:], ev),
            "next": len(room.game.events)}


# ---------------------------------------------------------------- WebSocket

@app.websocket("/api/rooms/{code}/ws")
async def room_ws(ws: WebSocket, code: str, token: str = ""):
    try:
        room = store.get(code)
        viewer = room.viewer_of(token)
    except RoomError:
        await ws.close(code=4401)
        return
    await ws.accept()
    entry = (ws, viewer)
    room.sockets.append(entry)
    try:
        await ws.send_json({
            "type": "welcome",
            "next_seq": len(room.game.events) if room.game else 0,
            **_state_payload(room, viewer),
        })
        while True:
            await ws.receive_text()  # 純下行;收到的訊息一律忽略(保活)
    except WebSocketDisconnect:
        pass
    finally:
        try:
            room.sockets.remove(entry)
        except ValueError:
            pass


# ---------------------------------------------------------------- 逾時代打

async def _fire_due_timeouts(now: float | None = None) -> None:
    now = now if now is not None else time.time()
    for room in list(store.rooms.values()):
        if room.game is None or room.deadline is None or now < room.deadline:
            continue
        async with _lock(room.code):
            if room.deadline is None or now < room.deadline:
                continue  # 取得鎖前已被真實指令重置
            player = awaited_player(room.game)
            command = default_command(room.game)
            if player is None or command is None:
                room.deadline = None
                continue
            command["player"] = player
            try:
                events = submit(room.game, command)
            except IllegalCommand:
                room.reset_deadline()
                continue
            for ev in events:
                ev["timeout"] = True  # 事件標記逾時(回放一致)
            room.touch()
            room.reset_deadline()
        await _broadcast(room, events)


async def _timeout_loop() -> None:
    while True:
        await asyncio.sleep(1)
        try:
            await _fire_due_timeouts()
        except Exception:
            pass


# ---------------------------------------------------------------- 靜態資源

app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="frontend")

    @app.get("/")
    def index():
        return FileResponse(FRONTEND_DIR / "index.html")
