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
from ..engine.deck import DeckError, load_deck, validate_deck
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
    deck: dict | None = None          # 建房者牌組:{"preset":"level1"} 或 {"pages":[...]}
    decks: list[dict] | None = None   # 本機房:雙方各一副([p0, p1])
    name: str | None = None           # 建房者暱稱
    names: list[str | None] | None = None  # 本機房:雙方暱稱([n0, n1])


class JoinBody(BaseModel):
    deck: dict | None = None
    name: str | None = None           # 加入者暱稱


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


NAME_MAX_LEN = 16


def _clean_name(raw) -> str | None:
    """暱稱清理:去頭尾空白、移除控制字元、限長;空字串視為未設(回退預設)。"""
    if not isinstance(raw, str):
        return None
    cleaned = "".join(ch for ch in raw if ch.isprintable()).strip()
    cleaned = cleaned[:NAME_MAX_LEN]
    return cleaned or None


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
        "names": [room.names[0], room.names[1]],   # 公開:雙方暱稱(None=用預設)
        "awaited_player": awaited_player(room.game) if room.game else None,
    }


def _state_payload(room: Room, viewer) -> dict:
    ev = _effective_viewer(room, viewer)
    payload = {"room": _room_meta(room, viewer)}
    if room.game is not None:
        payload["state"] = snapshot(room.game, ev)
    return payload


DECKS_DIR = DATA_DIR / "decks"
DEFAULT_PRESET = "level1"


def _load_i18n() -> dict:
    import json
    path = FRONTEND_DIR / "i18n" / "zh-TW.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError:
        return {}


def _scan_presets() -> dict[str, dict]:
    """掃描 data/decks/*.json 建 {id: {"path", "name"}} 對照表;壞檔排除記 log。

    顯示名:name_key(經 i18n 字典解析)→ 內嵌 name → id。
    """
    import json
    import logging

    i18n = _load_i18n()
    db = card_db()
    presets: dict[str, dict] = {}
    for path in sorted(DECKS_DIR.glob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            deck_id = str(raw["id"])
            load_deck(path, db)  # 確認為合法牌組;壞檔在此拋出
        except (OSError, KeyError, DeckError, ValueError) as exc:
            logging.getLogger(__name__).warning("跳過無效預組 %s: %s", path.name, exc)
            continue
        name = i18n.get(raw.get("name_key", ""), None) or raw.get("name") or deck_id
        presets[deck_id] = {"path": path, "name": name}
    return presets


_PRESETS: dict[str, dict] | None = None


def _presets() -> dict[str, dict]:
    """快取的預組對照表(啟動掃描一次;部署期檔案不變)。"""
    global _PRESETS
    if _PRESETS is None:
        _PRESETS = _scan_presets()
    return _PRESETS


def preset_list() -> list[dict]:
    """對外清單:預設預組置頂,其餘依 id 排序。"""
    items = [{"id": pid, "name": p["name"]} for pid, p in _presets().items()]
    items.sort(key=lambda x: (x["id"] != DEFAULT_PRESET, x["id"]))
    return items


def _default_deck() -> tuple[str, ...]:
    return load_deck(_presets()[DEFAULT_PRESET]["path"], card_db()).pages


def _resolve_deck(spec: dict | None) -> tuple[str, ...] | None:
    """解析牌組欄位。回傳 None = 用預設預組(level1)。

    - {preset: id}:id 必須在掃描集合內(白名單,絕不轉為任意路徑);未知回 4xx。
    - {pages:[...]}:自訂牌組以構築規則驗證,違規回 422。
    """
    if spec is None:
        return None
    if "preset" in spec:
        pid = spec.get("preset")
        if pid == DEFAULT_PRESET:
            return None
        preset = _presets().get(pid)
        if preset is None:
            raise HTTPException(404, detail={"code": "deck.unknown_preset",
                                             "message": f"未知的預組:{pid}"})
        return load_deck(preset["path"], card_db()).pages
    pages = spec.get("pages")
    if not isinstance(pages, list):
        raise HTTPException(422, detail={"code": "deck.bad_request",
                                         "message": "deck 須為 preset 或 pages"})
    try:
        validate_deck(pages, card_db())
    except DeckError as exc:
        raise HTTPException(422, detail={"code": exc.code, "message": str(exc)})
    return tuple(pages)


def _start_game(room: Room) -> None:
    default = _default_deck()
    deck0 = room.decks[0] or default
    deck1 = room.decks[1] or default
    room.game = new_game(deck0, seed=room.seed, decks=(list(deck0), list(deck1)))
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


# ---------------------------------------------------------------- 預組探索

@app.get("/api/decks")
async def list_decks():
    """列出伺服器 data/decks/ 下所有預組魔本(丟檔即現)。"""
    return {"decks": preset_list()}


# ---------------------------------------------------------------- 房間端點

@app.post("/api/rooms")
async def create_room(body: CreateRoom):
    # 牌組先驗證再建房(非法牌組不建房)
    if body.mode == "local" and body.decks is not None:
        if len(body.decks) != 2:
            raise HTTPException(422, detail={"code": "deck.bad_request",
                                             "message": "本機房 decks 須為兩副"})
        resolved = [_resolve_deck(body.decks[0]), _resolve_deck(body.decks[1])]
    else:
        resolved = [_resolve_deck(body.deck), None]
    if body.mode == "local" and body.names is not None:
        names = [_clean_name(body.names[0] if len(body.names) > 0 else None),
                 _clean_name(body.names[1] if len(body.names) > 1 else None)]
    else:
        names = [_clean_name(body.name), None]
    try:
        room, token0 = store.create(body.mode, body.timer_seconds, body.seed, names=names)
    except RoomError as exc:
        raise _http_error(exc)
    room.decks = resolved
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
async def join_room(code: str, body: JoinBody | None = None):
    deck1 = _resolve_deck(body.deck if body else None)  # 非法牌組在佔位前就被拒
    try:
        room, token1 = store.join(code, name=_clean_name(body.name if body else None))
    except RoomError as exc:
        raise _http_error(exc)
    room.decks[1] = deck1
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
