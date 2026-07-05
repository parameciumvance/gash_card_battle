"""房間層:Room 包裹 Game;token 即身分;計時器的等待者推導與逾時預設指令。

引擎對房間一無所知;逾時代打即正常指令,走同一條提交路徑。
"""

from __future__ import annotations

import secrets
import string
import time
from dataclasses import dataclass, field

from ..engine.state import BATTLE, GAME_OVER, START, Game

ROOM_CODE_ALPHABET = string.ascii_uppercase + string.digits
ROOM_CODE_LEN = 6
IDLE_SECONDS = 2 * 60 * 60          # 閒置回收:2 小時無活動
TIMER_CHOICES = (None, 30, 60, 120)


class RoomError(Exception):
    def __init__(self, status: int, code: str, message: str = ""):
        super().__init__(message or code)
        self.status = status
        self.code = code


@dataclass
class Room:
    code: str
    mode: str                                   # "online" | "local"
    timer_seconds: int | None
    seed: int | None
    spectator_token: str
    player_tokens: dict[str, int] = field(default_factory=dict)   # token → player index
    game: Game | None = None
    sockets: list = field(default_factory=list)   # [(websocket, viewer)]
    deadline: float | None = None                 # 逾時時刻(epoch 秒)
    last_activity: float = field(default_factory=time.time)

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

    def create(self, mode: str, timer_seconds: int | None, seed: int | None) -> tuple[Room, str]:
        if mode not in ("online", "local"):
            raise RoomError(422, "room.bad_mode", "mode 須為 online 或 local")
        if timer_seconds not in TIMER_CHOICES:
            raise RoomError(422, "room.bad_timer", f"timer 須為 {TIMER_CHOICES}")
        self.cleanup_idle()
        room = Room(code=self._new_code(), mode=mode, timer_seconds=timer_seconds,
                    seed=seed, spectator_token=secrets.token_hex(12))
        token0 = secrets.token_hex(12)
        room.player_tokens[token0] = 0
        self.rooms[room.code] = room
        return room, token0

    def get(self, code: str) -> Room:
        room = self.rooms.get(code.upper())
        if room is None:
            raise RoomError(404, "room.not_found", "房間不存在")
        return room

    def join(self, code: str) -> tuple[Room, str]:
        room = self.get(code)
        if room.mode != "online":
            raise RoomError(409, "room.not_joinable", "本機房不可加入")
        if room.player_count() >= 2:
            raise RoomError(409, "room.full", "房間已滿(仍可觀戰)")
        token1 = secrets.token_hex(12)
        room.player_tokens[token1] = 1
        room.touch()
        return room, token1

    def cleanup_idle(self) -> None:
        now = time.time()
        for code in [c for c, r in self.rooms.items()
                     if now - r.last_activity > IDLE_SECONDS]:
            del self.rooms[code]


# ---------------------------------------------------------------- 計時器輔助

def awaited_player(game: Game) -> int | None:
    """目前等待哪位玩家輸入;對局結束回 None。"""
    st = game.state
    if st.phase == GAME_OVER:
        return None
    if st.pending is not None:
        return st.pending.player
    if st.phase == START:
        return st.turn_player
    if st.phase != BATTLE:
        return None
    if st.battle is not None:
        if st.battle.step == "defense":
            return st.battle.defender
        return st.battle.data.get("effect_turn")
    if st.battle_in is not None:
        return 1 - st.battle_in["attacker"]
    return st.action_player


def default_command(game: Game) -> dict | None:
    """逾時代打的安全預設指令(不含 player,由呼叫端補上)。"""
    st = game.state
    if st.phase == GAME_OVER:
        return None
    if st.pending is not None:
        kind = st.pending.kind
        if kind == "protect" or kind == "coin_confirm":
            return {"type": "choose", "value": None}       # 不庇護 / 保留硬幣
        if kind == "e011_retry":
            return {"type": "choose", "value": False}      # 放棄付費重擲
        if kind == "damage_order":
            return {"type": "choose", "value": 0}
        opt = st.pending.options[0]
        return {"type": "choose", "value": opt.get("value", opt.get("page"))}
    if st.phase == START:
        return {"type": "flip_pages", "count": 0}
    if st.battle is not None:
        if st.battle.step == "defense":
            return {"type": "no_defense"}
        return {"type": "pass"}
    if st.battle_in is not None:
        return {"type": "battle_in_response", "allow": True}  # 讓過=依規則強制攻擊
    return {"type": "pass"}
