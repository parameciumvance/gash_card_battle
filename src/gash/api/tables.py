"""固定牌桌(game-tables):每張牌桌記住目前對應的線上房;狀態一律由房間推導。

狀態:empty(沒有房間,或房間已被回收)、waiting(房間尚未開局,開桌者一人)、playing(對局中)、
ended(對局結束,等待雙方選擇再戰 / 離開)。一間房只進行一局:再戰或換人時在同一桌建立新房間。
斷線寬限與選擇期限由 app 的計時迴圈呼叫 `sweep` 檢查;入座的「讀狀態 → 決定 → 寫入」之間不 await,
所以同一桌的請求依到達順序處理。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from ..engine.state import GAME_OVER
from .rooms import Room, RoomStore

TABLE_COUNT = 5
TABLE_TIMERS = (30, 60, 120)        # 牌桌一律計時
GRACE_SECONDS = 60                  # 斷線寬限(等待中、結束後)
CHOICE_SECONDS = 120                # 結束後選擇期限

EMPTY, WAITING, PLAYING, ENDED = "empty", "waiting", "playing", "ended"
REMATCH, LEAVE = "rematch", "leave"


@dataclass
class Table:
    number: int
    room_code: str | None = None
    waiting_since: float | None = None            # 開始等待對手的時刻
    absent_since: dict = field(default_factory=dict)   # 座位 → 開始沒有連線的時刻
    ended_at: float | None = None                 # 偵測到對局結束的時刻
    choices: dict = field(default_factory=dict)   # 座位 → REMATCH / LEAVE

    def clear(self, room_code: str | None = None, now: float | None = None) -> None:
        """改為對應另一間房(None = 空桌),清除這一局的計時與選擇。"""
        self.room_code = room_code
        self.waiting_since = now if room_code else None
        self.absent_since = {}
        self.ended_at = None
        self.choices = {}


class TableStore:
    def __init__(self, count: int = TABLE_COUNT):
        self.count = count
        self.reset()

    def reset(self) -> None:
        self.tables = [Table(number=i + 1) for i in range(self.count)]

    def get(self, number: int) -> Table | None:
        return self.tables[number - 1] if 1 <= number <= self.count else None

    def room_of(self, table: Table, rooms: RoomStore) -> Room | None:
        room = rooms.rooms.get(table.room_code) if table.room_code else None
        if table.room_code and room is None:            # 房間已被回收:牌桌一併空出
            table.clear()
        return room

    def state(self, table: Table, rooms: RoomStore) -> str:
        room = self.room_of(table, rooms)
        if room is None:
            return EMPTY
        if room.game is None:
            return WAITING
        return ENDED if room.game.state.phase == GAME_OVER else PLAYING

    def view(self, table: Table, rooms: RoomStore, now: float | None = None) -> dict:
        """列表用的公開內容:不含玩家 token,也不含可用來加入的資訊。"""
        now = now if now is not None else time.time()
        state = self.state(table, rooms)
        room = self.room_of(table, rooms)
        out = {"number": table.number, "state": state, "names": [None, None], "timer_seconds": None,
               "season": None, "waiting_seconds": None, "spectate_url": None}
        if room is not None:
            out["names"] = list(room.names)
            out["timer_seconds"] = room.timer_seconds
            out["season"] = room.season
        if state == WAITING and table.waiting_since is not None:
            out["waiting_seconds"] = max(0, int(now - table.waiting_since))
        if state in (PLAYING, ENDED):
            out["spectate_url"] = f"/?spectate={room.code}&token={room.spectator_token}"
        return out

    def meta(self, table: Table, rooms: RoomStore, now: float | None = None) -> dict:
        """房間內的牌桌資訊(給該房的連線):桌號、雙方的選擇與選擇期限。"""
        now = now if now is not None else time.time()
        deadline = None
        if table.ended_at is not None:
            deadline = max(0, int(table.ended_at + CHOICE_SECONDS - now))
        return {"number": table.number, "state": self.state(table, rooms),
                "choices": {str(k): v for k, v in table.choices.items()},
                "choice_seconds_left": deadline}

    def table_of_room(self, code: str) -> Table | None:
        return next((t for t in self.tables if t.room_code == code), None)


TABLES = TableStore()


def connected_seats(room: Room) -> set:
    return {viewer for _ws, viewer in room.sockets if viewer in (0, 1)}
