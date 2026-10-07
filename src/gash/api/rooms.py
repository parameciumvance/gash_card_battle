"""房間層:Room 包裹 Game;token 即身分;計時器期限。

引擎對房間一無所知;逾時代打即正常指令,走同一條提交路徑
(等待者與安全預設指令見 engine/awaiting.py)。
"""

from __future__ import annotations

import random
import secrets
import string
import time
from dataclasses import dataclass, field
from typing import Any

from ..engine.awaiting import awaited_player
from ..engine.state import Game

ROOM_CODE_ALPHABET = string.ascii_uppercase + string.digits
ROOM_CODE_LEN = 6
IDLE_SECONDS = 2 * 60 * 60          # 閒置回收:2 小時無活動
TIMER_CHOICES = (None, 30, 60, 120)
MODES = ("online", "local", "npc")
NPC_SEAT = 1                        # NPC 房:建房者為玩家 0,NPC 為玩家 1


class RoomError(Exception):
    def __init__(self, status: int, code: str, message: str = ""):
        super().__init__(message or code)
        self.status = status
        self.code = code


@dataclass
class NpcSeat:
    """NPC 房的 NPC 座位。rng 由房間 seed 衍生(決策與隨機牌組抽選共用),可重現整局。"""
    level: str                                  # "dummy" | "normal"
    rng: random.Random
    deck: dict | None = None                    # 實際使用的牌組:{"preset": id} 或 {"pages": [...]}
    seat: int = NPC_SEAT
    task: Any = None                            # 目前的驅動 asyncio.Task


@dataclass
class Room:
    code: str
    mode: str                                   # "online" | "local" | "npc"
    timer_seconds: int | None
    seed: int | None
    spectator_token: str
    player_tokens: dict[str, int] = field(default_factory=dict)   # token → player index
    names: list = field(default_factory=lambda: [None, None])     # 雙方暱稱(公開;None=用預設)
    decks: list = field(default_factory=lambda: [None, None])     # 雙方牌組頁序(None=level1)
    game: Game | None = None
    sockets: list = field(default_factory=list)   # [(websocket, viewer)]
    deadline: float | None = None                 # 逾時時刻(epoch 秒)
    last_activity: float = field(default_factory=time.time)
    npc: NpcSeat | None = None                    # NPC 房的 NPC 座位

    def viewer_of(self, token: str):
        """token → viewer(0/1/"spectator");本機模式玩家 token 仍對映到各自 index。"""
        if token in self.player_tokens:
            return self.player_tokens[token]
        if token == self.spectator_token:
            return "spectator"
        raise RoomError(401, "room.bad_token", "無效的 token")

    def player_count(self) -> int:
        return len(set(self.player_tokens.values()))

    def touch(self) -> None:
        self.last_activity = time.time()

    def reset_deadline(self) -> None:
        """每次成功指令(或開局)後呼叫:有等待者且計時開啟才設期限。"""
        if self.timer_seconds and self.game is not None and awaited_player(self.game) is not None:
            self.deadline = time.time() + self.timer_seconds
        else:
            self.deadline = None


class RoomStore:
    def __init__(self):
        self.rooms: dict[str, Room] = {}

    def _new_code(self) -> str:
        for _ in range(20):
            code = "".join(secrets.choice(ROOM_CODE_ALPHABET) for _ in range(ROOM_CODE_LEN))
            if code not in self.rooms:
                return code
        raise RoomError(500, "room.code_exhausted")

    def create(self, mode: str, timer_seconds: int | None, seed: int | None,
               names: list | None = None) -> tuple[Room, str]:
        if mode not in MODES:
            raise RoomError(422, "room.bad_mode", "mode 須為 online、local 或 npc")
        if mode == "npc":
            timer_seconds = None            # NPC 房不計時
        if timer_seconds not in TIMER_CHOICES:
            raise RoomError(422, "room.bad_timer", f"timer 須為 {TIMER_CHOICES}")
        self.cleanup_idle()
        room = Room(code=self._new_code(), mode=mode, timer_seconds=timer_seconds,
                    seed=seed, spectator_token=secrets.token_hex(12))
        if names:
            for i in (0, 1):
                if i < len(names):
                    room.names[i] = names[i]
        token0 = secrets.token_hex(12)
        room.player_tokens[token0] = 0
        self.rooms[room.code] = room
        return room, token0

    def get(self, code: str) -> Room:
        room = self.rooms.get(code.upper())
        if room is None:
            raise RoomError(404, "room.not_found", "房間不存在")
        return room

    def join(self, code: str, name: str | None = None) -> tuple[Room, str]:
        room = self.get(code)
        if room.mode != "online":
            raise RoomError(409, "room.not_joinable", "本機房不可加入")
        if room.player_count() >= 2:
            raise RoomError(409, "room.full", "房間已滿(仍可觀戰)")
        token1 = secrets.token_hex(12)
        room.player_tokens[token1] = 1
        room.names[1] = name
        room.touch()
        return room, token1

    def online_count(self) -> int:
        """對戰中人數:玩家連線依 (房號, 座位) 去重,觀戰連線(共用 token,無從區分)每條一人。"""
        players = set()
        spectators = 0
        for room in self.rooms.values():
            for _ws, viewer in room.sockets:
                if viewer == "spectator":
                    spectators += 1
                else:
                    players.add((room.code, viewer))
        return len(players) + spectators

    def cleanup_idle(self) -> None:
        now = time.time()
        for code in [c for c, r in self.rooms.items()
                     if now - r.last_activity > IDLE_SECONDS]:
            del self.rooms[code]
