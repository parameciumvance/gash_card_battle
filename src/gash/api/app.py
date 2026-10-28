"""FastAPI 薄殼:房間生命週期、token 鑑別、指令轉發、視角化快照與 WebSocket 推送。

引擎為唯一規則權威;所有輸出經 views.py 視角過濾;逾時代打走同一條指令路徑。
"""

from __future__ import annotations

import asyncio
import json
import logging
import mimetypes
import random
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ..engine.awaiting import awaited_player, default_command
from ..engine.cards import DATA_DIR, card_db
from ..engine.deck import DeckError, load_deck, validate_deck
from ..engine.seasons import deck_season, default_season, selectable_seasons
from ..engine.engine import IllegalCommand, new_game, submit
from ..engine.state import BOOK_SIZE, GAME_OVER
from ..npc import LEVELS as NPC_LEVELS
from ..npc import decide, submit_ranked
from ..paths import frontend_dir, resolve_assets
from ..version import app_version
from .rooms import NpcSeat, Room, RoomError, RoomStore
from . import tables as tables_mod
from .tables import (ENDED, EMPTY, LEAVE, PLAYING, REMATCH, TABLE_TIMERS, TABLES, WAITING,
                     connected_seats)
from .views import filter_events, snapshot

# Python 3.12 的 .webp 只在非嚴格對照表,python:3.12-slim 又沒有 /etc/mime.types,
# StaticFiles 會回 application/octet-stream;先登記,卡圖一律 image/webp
mimetypes.add_type("image/webp", ".webp")

FRONTEND_DIR = frontend_dir()
ASSETS = resolve_assets()
if not ASSETS.installed:
    try:  # 先建好安裝點:玩家放入卡圖後重新整理即生效,免重啟
        ASSETS.dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

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


@app.middleware("http")
async def cache_headers(request, call_next):
    """前端資源帶 Cache-Control: no-cache:瀏覽器每次使用前以 ETag 確認(未變回 304),
    部署後不會混用新舊版本。卡圖內容固定,成功回應快取 7 天(404 不帶,補圖後才看得到);
    API 本來就不快取,不套用。"""
    response = await call_next(request)
    path = request.url.path
    if "cache-control" in response.headers:
        return response
    if path.startswith("/static/assets/"):
        if response.status_code in (200, 304):
            response.headers["Cache-Control"] = "public, max-age=604800"
    elif path == "/" or path.startswith(("/static/", "/data/")):
        response.headers["Cache-Control"] = "no-cache"
    return response


class CreateRoom(BaseModel):
    mode: str = "online"
    timer_seconds: int | None = None
    seed: int | None = None
    deck: dict | None = None          # 建房者牌組:{"preset":"level1"} 或 {"pages":[...]}
    decks: list[dict] | None = None   # 本機房:雙方各一副([p0, p1])
    name: str | None = None           # 建房者暱稱
    names: list[str | None] | None = None  # 本機房:雙方暱稱([n0, n1])
    npc_level: str | None = None      # NPC 房:難度(dummy / normal,缺省 normal)
    npc_deck: dict | None = None      # NPC 房:指定的 NPC 牌組
    npc_decks: list[dict] | None = None  # NPC 房:隨機抽選的候選牌組
    season: int | None = None         # 賽季(缺省為 default_season())


class JoinBody(BaseModel):
    deck: dict | None = None
    name: str | None = None           # 加入者暱稱


class SitBody(BaseModel):
    name: str | None = None
    deck: dict | None = None
    expect: str = "empty"             # 入座者以為的牌桌狀態:empty / waiting
    timer_seconds: int | None = None  # 開空桌時的計時(30 / 60 / 120)
    season: int | None = None         # 開空桌時的賽季(缺省為 default_season())


class ChoiceBody(BaseModel):
    choice: str                       # rematch / leave


class CommandBody(BaseModel):
    command: dict


class DebugPlayerState(BaseModel):
    book: list[str]
    mp: int


class DebugStateBody(BaseModel):
    players: list[DebugPlayerState]


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
        "npc": _npc_meta(room),
        "table": _table_meta(room),
        "season": room.season,
    }


def _table_meta(room: Room) -> dict | None:
    """牌桌的房間:桌號、雙方的選擇與選擇剩餘秒數(結束後)。"""
    table = TABLES.table_of_room(room.code) if room.table else None
    return TABLES.meta(table, store) if table else None


def _npc_meta(room: Room) -> dict | None:
    """NPC 的座位與難度;NPC 使用的牌組在對局結束後才公開。"""
    if room.npc is None:
        return None
    over = room.game is not None and room.game.state.phase == GAME_OVER
    return {"seat": room.npc.seat, "level": room.npc.level, "deck": room.npc.deck if over else None}


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
    """掃描 data/decks/*.json 建 {id: {"path", "name", "name_key"}} 對照表;壞檔排除記 log。

    顯示名:name_key(經中文 i18n 字典解析)→ 內嵌 name → id;前端另以 name_key 依目前語言解析。
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
        presets[deck_id] = {"path": path, "name": name, "name_key": raw.get("name_key") or None,
                            "season": deck_season(raw["pages"])}
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
    items = [{"id": pid, "name": p["name"], "season": p["season"],
              **({"name_key": p["name_key"]} if p["name_key"] else {})}
             for pid, p in _presets().items()]
    items.sort(key=lambda x: (x["id"] != DEFAULT_PRESET, x["id"]))
    return items


def _default_deck() -> tuple[str, ...]:
    return load_deck(_presets()[DEFAULT_PRESET]["path"], card_db()).pages


def _season_of(raw: int | None) -> int:
    """請求的賽季;未指定為缺省賽季,不可選的值回 422 room.bad_season。"""
    if raw is None:
        return default_season()
    if raw not in selectable_seasons():
        raise HTTPException(422, detail={"code": "room.bad_season",
                                         "message": f"賽季須為 {selectable_seasons()}"})
    return raw


def _resolve_deck(spec: dict | None, season: int) -> tuple[str, ...] | None:
    """解析牌組欄位並依賽季驗證。回傳 None = 用預設預組(level1)。

    - {preset: id}:id 必須在掃描集合內(白名單,絕不轉為任意路徑);未知回 4xx。
    - {pages:[...]}:自訂牌組以構築規則驗證,違規回 422。
    預組與缺省牌組也依賽季驗證;超出賽季回 422 deck.season,detail 附房間賽季。
    """
    if spec is None:
        pages = list(_default_deck())
    elif "preset" in spec:
        pid = spec.get("preset")
        preset = _presets().get(pid)
        if preset is None:
            raise HTTPException(404, detail={"code": "deck.unknown_preset",
                                             "message": f"未知的預組:{pid}"})
        pages = list(load_deck(preset["path"], card_db()).pages)
    else:
        pages = spec.get("pages")
        if not isinstance(pages, list):
            raise HTTPException(422, detail={"code": "deck.bad_request",
                                             "message": "deck 須為 preset 或 pages"})
    try:
        validate_deck(pages, card_db(), season=season)
    except DeckError as exc:
        extra = {"season": season} if exc.code == "deck.season" else {}
        raise HTTPException(422, detail={"code": exc.code, "message": str(exc), **extra})
    if spec is None or spec.get("preset") == DEFAULT_PRESET:
        return None
    return tuple(pages)


NPC_DECK_CANDIDATES_MAX = 64


def _npc_http_error(code: str, message: str) -> HTTPException:
    return HTTPException(422, detail={"code": code, "message": message})


def _deck_label(spec: dict | None) -> dict:
    """公開用的牌組描述:預組以 id、自訂牌組以頁序(與 _resolve_deck 的判斷順序相同)。"""
    if spec is None:
        return {"preset": DEFAULT_PRESET}
    if "preset" in spec:
        return {"preset": spec.get("preset")}
    return {"pages": list(spec["pages"])}


def _npc_seat(body: CreateRoom, season: int) -> tuple[NpcSeat, tuple[str, ...] | None]:
    """驗證 NPC 難度與牌組,抽選隨機牌組;回傳 NPC 座位與 NPC 牌組頁序(None=level1)。"""
    level = body.npc_level or "normal"
    if level not in NPC_LEVELS:
        raise _npc_http_error("npc.bad_level", f"NPC 難度須為 {NPC_LEVELS}")
    if body.npc_deck is not None and body.npc_decks is not None:
        raise _npc_http_error("npc.deck_conflict", "npc_deck 與 npc_decks 只能擇一")
    if body.npc_decks is not None and not 1 <= len(body.npc_decks) <= NPC_DECK_CANDIDATES_MAX:
        raise _npc_http_error("npc.bad_decks", f"候選牌組須為 1 至 {NPC_DECK_CANDIDATES_MAX} 副")
    rng = random.Random(f"npc:{body.seed}") if body.seed is not None else random.Random()
    if body.npc_decks is not None:
        resolved = [_resolve_deck(spec, season) for spec in body.npc_decks]   # 全部驗證後才抽
        i = rng.randrange(len(resolved))
        spec, pages = body.npc_decks[i], resolved[i]
    else:
        spec, pages = body.npc_deck, _resolve_deck(body.npc_deck, season)
    return NpcSeat(level=level, rng=rng, deck=_deck_label(spec)), pages


def _start_game(room: Room) -> None:
    default = _default_deck()
    deck0 = room.decks[0] or default
    deck1 = room.decks[1] or default
    # 自由調查時間(本機模式)固定玩家 1 先攻;其他模式擲硬幣
    room.game = new_game(deck0, seed=room.seed, decks=(list(deck0), list(deck1)),
                         first_player=0 if room.mode == "local" else None)
    room.reset_deadline()


async def _broadcast(room: Room, events: list[dict], actor: int | None = None) -> None:
    """推送一批事件;actor 為發起這批事件的玩家(金手指、開局等為 None),前端據以決定聚焦展示。"""
    for ws, viewer in list(room.sockets):
        ev = _effective_viewer(room, viewer)
        try:
            await ws.send_json({
                "type": "update",
                "actor": actor,
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
    """列出伺服器 data/decks/ 下所有預組魔書(丟檔即現)。"""
    return {"decks": preset_list()}


# ---------------------------------------------------------------- 執行環境

@app.get("/api/meta")
async def get_meta():
    """執行環境資訊:卡圖安裝狀態與版本號(供前端顯示安裝提示與版本)。"""
    cards_dir = ASSETS.dir / "cards"
    count = sum(1 for p in cards_dir.glob("*.webp")) if cards_dir.is_dir() else 0  # 只認 WebP,舊的 .jpg 不算
    return {
        "assets": {
            "installed": cards_dir.is_dir(),  # 即時偵測:啟動後放入卡圖也能反映
            "count": count,
            "expected": len(card_db()),
            "install_dir": str(ASSETS.dir),
        },
        "version": app_version(),
    }


ANNOUNCEMENT_FILE = "announcement.json"


def read_announcement(now: datetime | None = None) -> dict | None:
    """卡圖目錄下的公告檔;每次即時讀取,編輯檔案即可發布 / 撤下。不存在、格式錯誤或已過 until 時為 None。"""
    path = ASSETS.dir / ANNOUNCEMENT_FILE
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        ann_id, message, until = data["id"], data["message"], data.get("until")
        if not isinstance(ann_id, str) or not ann_id:
            raise ValueError("id")
        if not isinstance(message, dict) or not message or not all(
                isinstance(k, str) and isinstance(v, str) for k, v in message.items()):
            raise ValueError("message")
        if until is not None:
            end = datetime.fromisoformat(until)
            if end.tzinfo is None:
                end = end.replace(tzinfo=timezone.utc)      # 沒有時區視為 UTC
            if end <= (now or datetime.now(timezone.utc)):
                return None
    except (OSError, ValueError, KeyError, TypeError) as exc:
        logging.getLogger(__name__).warning("公告檔格式錯誤,視為沒有公告:%s", exc)
        return None
    return {"id": ann_id, "message": message, "until": until}


@app.get("/api/announcement")
async def get_announcement():
    """維護公告(前端定期查詢);沒有時為 null。"""
    return {"announcement": read_announcement()}


@app.get("/api/online")
async def get_online():
    """對戰中人數(首頁顯示);只回總數,不含任何房間資訊。"""
    return {"count": store.online_count()}


# ---------------------------------------------------------------- 房間端點

@app.post("/api/rooms")
async def create_room(body: CreateRoom):
    # 牌組先驗證再建房(非法牌組不建房)
    season = _season_of(body.season)
    if body.mode == "local" and body.decks is not None:
        if len(body.decks) != 2:
            raise HTTPException(422, detail={"code": "deck.bad_request",
                                             "message": "本機房 decks 須為兩副"})
        resolved = [_resolve_deck(body.decks[0], season), _resolve_deck(body.decks[1], season)]
    else:
        resolved = [_resolve_deck(body.deck, season), None]
    npc_seat = None
    if body.mode == "npc":
        npc_seat, resolved[1] = _npc_seat(body, season)
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
    room.season = season
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
    elif room.mode == "npc":
        room.npc = npc_seat
        _start_game(room)
        resp["player_token"] = token0
        resp["events"] = filter_events(room.game.events, 0)
        resp.update(_state_payload(room, 0))
        _kick_npc(room)
    else:
        resp["player_token"] = token0
        resp["join_url"] = f"/?join={room.code}"
        resp.update(_state_payload(room, 0))
    return resp


@app.post("/api/rooms/{code}/join")
async def join_room(code: str, body: JoinBody | None = None):
    existing = store.rooms.get(code.upper())
    season = existing.season if existing is not None else default_season()
    deck1 = _resolve_deck(body.deck if body else None, season)  # 非法牌組在佔位前就被拒
    if existing is not None and existing.table:
        raise HTTPException(409, detail={"code": "room.table_only", "message": "牌桌的房間須經牌桌入座"})
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
    await _broadcast(room, events, actor=viewer)
    _kick_npc(room)
    ev = _effective_viewer(room, viewer)
    return {"actor": viewer, "events": filter_events(events, ev), **_state_payload(room, viewer)}


def _debug_state_payload(room: Room) -> dict:
    return {"players": [{"book": list(p.book), "mp": p.mp} for p in room.game.state.players]}


def _check_cheat_access(room: Room, viewer) -> None:
    """金手指只開放本機房與 NPC 房的玩家;線上房與觀戰者 403。"""
    if room.mode not in ("local", "npc"):
        raise HTTPException(403, detail={"code": "room.not_local", "message": "僅本機測試模式與 NPC 對戰開放"})
    if viewer == "spectator":
        raise HTTPException(403, detail={"code": "room.spectator", "message": "觀戰者不能使用金手指"})


@app.get("/api/rooms/{code}/debug-state")
async def get_debug_state(code: str, x_player_token: str | None = Header(default=None)):
    """金手指:僅本機測試模式與 NPC 對戰開放,回傳雙方 book/mp 供編輯。"""
    room, viewer = _resolve(code, x_player_token)
    _check_cheat_access(room, viewer)
    if room.game is None:
        raise HTTPException(409, detail={"code": "room.waiting", "message": "等待對手加入"})
    return _debug_state_payload(room)


@app.post("/api/rooms/{code}/debug-state")
async def post_debug_state(code: str, body: DebugStateBody,
                           x_player_token: str | None = Header(default=None)):
    """金手指:驗證卡號存在、book 長度為 32 後整包取代雙方 book/mp。"""
    room, viewer = _resolve(code, x_player_token)
    _check_cheat_access(room, viewer)
    if room.game is None:
        raise HTTPException(409, detail={"code": "room.waiting", "message": "等待對手加入"})
    if len(body.players) != 2:
        raise HTTPException(422, detail={"code": "debug_state.bad_players",
                                         "message": "players 須含雙方"})
    db = card_db()
    for ps in body.players:
        if len(ps.book) != BOOK_SIZE:
            raise HTTPException(422, detail={"code": "debug_state.bad_book",
                                             "message": f"book 長度須為 {BOOK_SIZE}"})
        unknown = [c for c in ps.book if c not in db]
        if unknown:
            raise HTTPException(422, detail={"code": "debug_state.unknown_card",
                                             "message": f"不存在的卡號:{unknown[0]}"})
    async with _lock(room.code):
        for i, ps in enumerate(body.players):
            room.game.state.players[i].book = list(ps.book)
            room.game.state.players[i].mp = ps.mp
        batch: list[dict] = []
        room.game.emit(batch, "cheat_applied", player=None)
        room.touch()
    await _broadcast(room, batch)
    _kick_npc(room)
    return _debug_state_payload(room)


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


# ---------------------------------------------------------------- 牌桌(game-tables)

def _table_or_404(number: int):
    table = TABLES.get(number)
    if table is None:
        raise HTTPException(404, detail={"code": "table.not_found", "message": "牌桌不存在"})
    return table


def _table_error(status: int, code: str, message: str, **extra) -> HTTPException:
    return HTTPException(status, detail={"code": code, "message": message, **extra})


@app.get("/api/tables")
async def list_tables():
    """牌桌列表(牌桌頁每 5 秒查詢);不含玩家 token。"""
    now = time.time()
    return {"tables": [TABLES.view(t, store, now) for t in TABLES.tables]}


def _new_table_room(number: int, timer: int, season: int, names: list, decks: list) -> tuple[Room, list[str]]:
    """在牌桌上建立線上房;names / decks 有兩位時直接開局。回傳房間與各座位的 token。"""
    room, token0 = store.create("online", timer, None, names=[names[0], None])
    room.table = number
    room.season = season
    room.decks = [decks[0], None]
    tokens = [token0]
    if len(names) > 1:
        room, token1 = store.join(room.code, name=names[1])
        room.decks[1] = decks[1]
        tokens.append(token1)
        _start_game(room)
    return room, tokens


@app.post("/api/tables/{number}/sit")
async def sit_table(number: int, body: SitBody):
    table = _table_or_404(number)
    if body.expect not in (EMPTY, WAITING):
        raise _table_error(422, "table.bad_expect", "expect 須為 empty 或 waiting")
    if body.expect == EMPTY and body.timer_seconds not in TABLE_TIMERS:
        raise _table_error(422, "table.bad_timer", f"牌桌計時須為 {TABLE_TIMERS}")
    # 以下到開局為止都不 await:同一桌的請求依到達順序處理
    state = TABLES.state(table, store)
    if body.expect == EMPTY:
        season = _season_of(body.season)
    else:
        waiting = TABLES.room_of(table, store)
        season = waiting.season if waiting is not None else default_season()
    deck = _resolve_deck(body.deck, season)  # 非法牌組在改變牌桌前就被拒
    name = _clean_name(body.name)
    if state in (PLAYING, ENDED):
        raise _table_error(409, "table.busy", "這桌正在對戰")
    if body.expect == EMPTY:
        if state == WAITING:
            room = TABLES.room_of(table, store)
            raise _table_error(409, "table.taken", "這桌剛有人開桌",
                               host=room.names[0], timer_seconds=room.timer_seconds, season=room.season)
        room, tokens = _new_table_room(number, body.timer_seconds, season, [name], [deck])
        table.clear(room.code, time.time())
        return {"code": room.code, "player_token": tokens[0], "table": number,
                "spectate_url": f"/?spectate={room.code}&token={room.spectator_token}",
                **_state_payload(room, 0)}
    if state == EMPTY:
        raise _table_error(409, "table.empty", "開桌者已離開")
    room = TABLES.room_of(table, store)
    try:
        room, token1 = store.join(room.code, name=name)
    except RoomError:
        raise _table_error(409, "table.busy", "這桌正在對戰")
    room.decks[1] = deck
    _start_game(room)
    table.absent_since = {}
    await _broadcast(room, room.game.events)
    return {"code": room.code, "player_token": token1, "table": number,
            "events": filter_events(room.game.events, 1), **_state_payload(room, 1)}


@app.post("/api/tables/{number}/leave")
async def leave_table(number: int, x_player_token: str | None = Header(default=None)):
    """等待中的開桌者離開:立即空出牌桌(房間一併刪除,不再接受加入)。結束後離開同「離開」選擇。"""
    table = _table_or_404(number)
    room = TABLES.room_of(table, store)
    if room is None:
        return {"ok": True}
    try:
        viewer = room.viewer_of(x_player_token or "")
    except RoomError as exc:
        raise _http_error(exc)
    state = TABLES.state(table, store)
    if state == WAITING and viewer == 0:
        _free_table(table, room)
        return {"ok": True}
    if state == ENDED and viewer in (0, 1):
        table.choices[viewer] = LEAVE
        await _settle_table(table, room, time.time())
        return {"ok": True}
    raise _table_error(409, "table.busy", "這桌正在對戰")


@app.post("/api/tables/{number}/choice")
async def choose_table(number: int, body: ChoiceBody, x_player_token: str | None = Header(default=None)):
    """對局結束後的再戰 / 離開。"""
    table = _table_or_404(number)
    room = TABLES.room_of(table, store)
    if room is None or TABLES.state(table, store) != ENDED:
        raise _table_error(409, "table.not_ended", "對局尚未結束")
    try:
        viewer = room.viewer_of(x_player_token or "")
    except RoomError as exc:
        raise _http_error(exc)
    if viewer not in (0, 1):
        raise _table_error(403, "table.not_player", "只有對局雙方可以選擇")
    if body.choice not in (REMATCH, LEAVE):
        raise _table_error(422, "table.bad_choice", "choice 須為 rematch 或 leave")
    now = time.time()
    if table.ended_at is None:
        table.ended_at = now
    table.choices[viewer] = body.choice
    await _settle_table(table, room, now)
    return {"ok": True}


def _free_table(table, room: Room) -> None:
    store.rooms.pop(room.code, None)
    table.clear()


async def _settle_table(table, room: Room, now: float, notify: bool = True) -> None:
    """雙方都已決定時:都再戰 → 同桌新房開局;一方再戰 → 他成為新房的開桌者;都離開 → 空桌。
    還有一方未決定時,只把目前的選擇推送給房間的連線。"""
    if len(table.choices) < 2:
        if notify:
            await _broadcast(room, [])
        return
    stay = [seat for seat in (0, 1) if table.choices.get(seat) == REMATCH]
    moves: dict = {}                        # 舊座位 → (新 token, 新座位);觀戰者以 "spectator"
    if len(stay) == 2:
        new, tokens = _new_table_room(table.number, room.timer_seconds, room.season, list(room.names), list(room.decks))
        moves = {0: (tokens[0], 0), 1: (tokens[1], 1), "spectator": (new.spectator_token, None)}
        table.clear(new.code, now)
    elif len(stay) == 1:
        seat = stay[0]
        new, tokens = _new_table_room(table.number, room.timer_seconds, room.season, [room.names[seat]], [room.decks[seat]])
        moves = {seat: (tokens[0], 0)}        # 留下的人成為新房的開桌者(座位 0)
        table.clear(new.code, now)
    else:
        table.clear()
        new = None
    if notify and new is not None:
        for ws, viewer in list(room.sockets):
            if viewer not in moves:
                continue
            token, seat = moves[viewer]
            msg = {"type": "table_moved", "table": table.number, "code": new.code}
            if viewer == "spectator":
                msg["spectator_token"] = token
            else:
                msg.update(token=token, seat=seat, started=new.game is not None)
            try:
                await ws.send_json(msg)
            except Exception:
                pass


async def check_tables(now: float | None = None, notify: bool = True) -> None:
    """計時迴圈呼叫:等待中開桌者斷線超過寬限 → 空桌;結束後斷線超過寬限或超過選擇期限 → 視為離開。"""
    now = now if now is not None else time.time()
    for table in TABLES.tables:
        room = TABLES.room_of(table, store)
        if room is None:
            continue
        state = TABLES.state(table, store)
        seats = connected_seats(room)
        if state == WAITING:
            if 0 in seats:
                table.absent_since.pop(0, None)
            elif now - table.absent_since.setdefault(0, now) >= tables_mod.GRACE_SECONDS:
                _free_table(table, room)
        elif state == ENDED:
            if table.ended_at is None:
                table.ended_at = now
            changed = False
            for seat in (0, 1):
                if seat in table.choices:
                    continue
                if seat in seats:
                    table.absent_since.pop(seat, None)
                    gone = False
                else:
                    gone = now - table.absent_since.setdefault(seat, now) >= tables_mod.GRACE_SECONDS
                if gone or now - table.ended_at >= tables_mod.CHOICE_SECONDS:
                    table.choices[seat] = LEAVE
                    changed = True
            if changed:
                await _settle_table(table, room, now, notify=notify)


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
        await _broadcast(room, events, actor=player)


async def _timeout_loop() -> None:
    while True:
        await asyncio.sleep(1)
        try:
            await _fire_due_timeouts()
        except Exception:
            pass
        for room in list(store.rooms.values()):
            _kick_npc(room)     # 保險:輪到 NPC 卻沒有執行中的驅動時恢復
        try:
            await check_tables()
        except Exception:
            _log.exception("牌桌檢查失敗")


# ---------------------------------------------------------------- NPC 驅動

# NPC 送出前的等待秒數:略長於標準速度的聚焦展示(pass 1 秒、其他 2 秒),畫面才跟得上
NPC_QUIET_DELAY = 1.2     # 不改變盤面的指令(pass、迎戰、不防禦、不翻頁)
NPC_ACTION_DELAY = 2.3    # 其他指令
_QUIET_COMMANDS = {"pass", "battle_in_response", "no_defense"}
_log = logging.getLogger(__name__)


def _npc_delay(command: dict) -> float:
    quiet = (command["type"] in _QUIET_COMMANDS
             or (command["type"] == "flip_pages" and command.get("count") == 0))
    return NPC_QUIET_DELAY if quiet else NPC_ACTION_DELAY


async def _npc_pause(seconds: float) -> None:
    await asyncio.sleep(seconds)


def _npc_turn(room: Room) -> bool:
    game = room.game
    return (room.npc is not None and game is not None and game.state.phase != GAME_OVER
            and awaited_player(game) == room.npc.seat)


def _kick_npc(room: Room) -> None:
    """輪到 NPC 時啟動驅動;同一房間同時只有一個驅動 task。"""
    if not _npc_turn(room):
        return
    task = room.npc.task
    if task is not None and not task.done():
        return
    room.npc.task = asyncio.get_running_loop().create_task(_drive_npc(room))


def _npc_decide(room: Room) -> list[dict]:
    seat = room.npc
    try:
        return decide(room.game, seat.seat, seat.level, seat.rng)
    except Exception:       # 模擬中的引擎錯誤不可拖垮房間:退回安全預設
        _log.exception("NPC 決策失敗(房間 %s)", room.code)
        return []


async def _drive_npc(room: Room) -> None:
    """輪到 NPC 時連續出手:決策 → 稍候 → 局面沒變才送出(變了就重新決策)→ 廣播。"""
    game = room.game
    while _npc_turn(room):
        version = len(game.events)
        ranked = _npc_decide(room)
        await _npc_pause(_npc_delay(ranked[0]) if ranked else NPC_QUIET_DELAY)
        async with _lock(room.code):
            if len(game.events) != version or not _npc_turn(room):
                continue
            result = submit_ranked(game, room.npc.seat, ranked)
            if result is None:
                _log.error("NPC 沒有可送出的指令(房間 %s)", room.code)
                return
            events = result[1]
            room.touch()
            room.reset_deadline()
        await _broadcast(room, events, actor=room.npc.seat)


# ---------------------------------------------------------------- 靜態資源

app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")
# 卡圖為外部資源,先於 /static 掛載;目錄可能不存在(未安裝 → 404,前端以卡背佔位)
app.mount("/static/assets", StaticFiles(directory=ASSETS.dir, check_dir=False), name="assets")
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="frontend")

    @app.get("/")
    def index():
        return FileResponse(FRONTEND_DIR / "index.html")
