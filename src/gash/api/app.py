"""FastAPI 薄殼:對局生命週期、指令轉發、狀態快照。引擎為唯一規則權威。

資訊隱藏:魔本未翻開頁面的內容絕不出現在任何回應中(僅回傳頁數統計)。
"""

from __future__ import annotations

import threading
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ..engine.cards import DATA_DIR, card_db
from ..engine.deck import load_deck
from ..engine.engine import IllegalCommand, new_game, slot_power, spell_cost, submit
from ..engine.state import BOOK_SIZE, Game

ROOT = Path(__file__).resolve().parents[3]
FRONTEND_DIR = ROOT / "frontend"

app = FastAPI(title="gash-card-battle")

_games: dict[str, Game] = {}
_locks: dict[str, threading.Lock] = {}


class CreateGame(BaseModel):
    seed: int | None = None
    deck: str = "level1"


class CommandBody(BaseModel):
    command: dict


def _get(game_id: str) -> tuple[Game, threading.Lock]:
    if game_id not in _games:
        raise HTTPException(404, detail={"code": "game.not_found"})
    return _games[game_id], _locks[game_id]


def _ability_view(number: str | None) -> dict | None:
    from ..engine.effects import registry as reg
    if number is None:
        return None
    spec = reg.ACTIVATED.get(number)
    if spec is None:
        return None
    return {"mode": spec.mode, "mp_cost": spec.mp_cost,
            "timing": spec.timing, "per_game": spec.per_game}


def _slot_view(game: Game, player: int, slot) -> dict:
    return {
        "uid": slot.uid,
        "stack": list(slot.stack),
        "top": slot.top,
        "injured": slot.injured,
        "partner": slot.partner,
        "power": slot_power(game, player, slot),
        "ability": _ability_view(slot.top),
        "partner_ability": _ability_view(slot.partner),
    }


def _player_view(game: Game, p: int) -> dict:
    ps = game.state.players[p]
    open_pages = []
    for page in ps.open_pages():
        number = ps.card_at(page)
        card = game.db[number]
        entry = {"page": page, "card": number}
        if card.type == "spell":
            entry["cost"] = spell_cost(game, p, page, card)
        open_pages.append(entry)
    return {
        "mp": ps.mp,
        "pos": min(ps.pos, BOOK_SIZE + 2),
        "book_size": BOOK_SIZE,
        "open_pages": open_pages,           # 只有翻開且仍在魔本中的卡
        "consumed_pages": sorted(ps.consumed_pages),
        "slots": [_slot_view(game, p, s) for s in ps.slots],
        "discard": list(ps.discard),
        "used_spell_pages": sorted(ps.used_spell_pages),
        "used_event_this_turn": ps.used_event_this_turn,
    }


def snapshot(game: Game) -> dict:
    st = game.state
    view: dict = {
        "phase": st.phase,
        "turn_no": st.turn_no,
        "turn_player": st.turn_player,
        "action_player": st.action_player,
        "players": [_player_view(game, 0), _player_view(game, 1)],
        "winner": st.winner,
        "end_reason": st.end_reason,
        "event_count": len(game.events),
    }
    if st.battle_in is not None:
        view["battle_in"] = dict(st.battle_in)
    if st.battle is not None:
        b = st.battle
        from ..engine.engine import _side_total
        view["battle"] = {
            "attacker": b.attacker,
            "step": b.step,
            "attack_spell": b.attack_spell,
            "attack_slot": b.attack_slot,
            "attack_negated": b.attack_negated,
            "attack_undefendable": b.attack_undefendable,
            "defense_spell": b.defense_spell,
            "defense_slot": b.defense_slot,
            "defense_negated": b.defense_negated,
            "effect_turn": b.data.get("effect_turn"),
            "attacker_total": _side_total(game, b, "attack"),
            "defender_total": _side_total(game, b, "defense"),
        }
    if st.pending is not None:
        view["pending"] = {
            "kind": st.pending.kind,
            "player": st.pending.player,
            "source": st.pending.source,
            "options": st.pending.options,
        }
    return view


@app.post("/api/games")
def create_game(body: CreateGame):
    deck = load_deck(DATA_DIR / f"decks/{body.deck}.json", card_db())
    game = new_game(deck.pages, seed=body.seed)
    game_id = uuid.uuid4().hex[:12]
    _games[game_id] = game
    _locks[game_id] = threading.Lock()
    return {"game_id": game_id, "state": snapshot(game), "events": game.events}


@app.post("/api/games/{game_id}/commands")
def post_command(game_id: str, body: CommandBody):
    game, lock = _get(game_id)
    with lock:  # 指令逐一循序處理
        try:
            events = submit(game, body.command)
        except IllegalCommand as exc:
            raise HTTPException(400, detail={"code": exc.code, "message": str(exc)})
    return {"events": events, "state": snapshot(game)}


@app.get("/api/games/{game_id}/state")
def get_state(game_id: str):
    game, _ = _get(game_id)
    return {"state": snapshot(game)}


@app.get("/api/games/{game_id}/events")
def get_events(game_id: str, since: int = 0):
    game, _ = _get(game_id)
    return {"events": game.events[since:], "next": len(game.events)}


# --- 靜態資源:前端與卡片資料 ---
app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="frontend")

    @app.get("/")
    def index():
        return FileResponse(FRONTEND_DIR / "index.html")
