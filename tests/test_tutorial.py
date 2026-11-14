"""教學對局(tutorial):教學房、固定局面、腳本對手、對手節奏,以及照劇本走完 17 步。

端點以函式直接呼叫,在同一個 event loop 中等待腳本對手的驅動 task;對手送出前的等待設為 0。
"""
import asyncio

import pytest
from fastapi import HTTPException

from gash.api import app as api
from gash.api.app import (CommandBody, CreateRoom, close_room, create_room, get_debug_state, post_command,
                          store, tutorial_continue)
from gash.engine.awaiting import awaited_player
from gash.engine.state import BATTLE

PLAYER, OPP = 0, 1


@pytest.fixture(autouse=True)
def no_npc_delay(monkeypatch):
    monkeypatch.setattr(api, "NPC_QUIET_DELAY", 0)
    monkeypatch.setattr(api, "NPC_ACTION_DELAY", 0)


class Tutorial:
    """一場教學房:玩家的指令與「下一步」放行對手。"""

    def __init__(self, body):
        self.body = body
        self.token = body["player_token"]
        self.room = store.rooms[body["code"]]

    @property
    def st(self):
        return self.room.game.state

    async def idle(self):
        while self.room.npc.task is not None and not self.room.npc.task.done():
            await self.room.npc.task

    async def send(self, command):
        res = await post_command(self.room.code, CommandBody(command=command), x_player_token=self.token)
        await self.idle()
        return res

    async def go(self):
        """按「下一步」:放行對手,等它出手到輪到玩家為止。"""
        await tutorial_continue(self.room.code, x_player_token=self.token)
        await self.idle()

    def events(self, kind):
        return [e for e in self.room.game.events if e["type"] == kind]

    def slot(self, player, top):
        return next(s for s in self.st.players[player].slots if s.top == top)


async def new_tutorial():
    t = Tutorial(await create_room(CreateRoom(mode="tutorial")))
    await t.idle()
    return t


def run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------- 教學房

def test_tutorial_room_setup():
    async def go():
        return await new_tutorial()
    t = run(go())
    st = t.st
    assert t.room.mode == "tutorial" and t.room.timer_seconds is None and t.room.npc.level == "tutorial"
    assert st.turn_player == PLAYER and awaited_player(t.room.game) == PLAYER          # 玩家先攻
    assert [s.top for s in st.players[PLAYER].slots] == ["M-001"]
    assert [s.top for s in st.players[OPP].slots] == ["M-021"]
    assert st.players[PLAYER].book[1:5] == ["P-001", "S-001", "Ex-005", "S-022"]
    assert st.players[PLAYER].book[5:9] == ["E-003", "S-001", "E-003", "S-001"]
    assert set(st.players[OPP].book[1:]) == {"S-037"}
    assert all(t.room.game.rng.random() >= 0.5 for _ in range(5))                     # 硬幣一律反面


def test_tutorial_room_has_no_cheat_and_can_be_closed():
    async def go():
        t = await new_tutorial()
        with pytest.raises(HTTPException) as exc:
            await get_debug_state(t.room.code, x_player_token=t.token)
        assert exc.value.status_code == 403
        await close_room(t.room.code, x_player_token=t.token)
        return t
    t = run(go())
    assert t.room.code not in store.rooms


def test_opponent_waits_for_continue():
    async def go():
        t = await new_tutorial()
        await t.send({"type": "flip_pages", "count": 0})
        await t.send({"type": "pass"})                                            # 輪到對手
        assert awaited_player(t.room.game) == OPP and t.room.tutorial_hold        # 對手不出手
        await t.go()
        return t
    t = run(go())
    assert awaited_player(t.room.game) == PLAYER and not t.room.tutorial_hold


def test_continue_only_for_tutorial_player():
    async def go():
        t = await new_tutorial()
        with pytest.raises(HTTPException) as bad:
            await tutorial_continue(t.room.code, x_player_token="bogus")
        npc = await create_room(CreateRoom(mode="npc", seed=1))
        with pytest.raises(HTTPException) as not_tutorial:
            await tutorial_continue(npc["code"], x_player_token=npc["player_token"])
        return bad.value, not_tutorial.value
    bad, not_tutorial = run(go())
    assert bad.status_code == 401
    assert not_tutorial.status_code == 409 and not_tutorial.detail["code"] == "room.not_tutorial"


# ---------------------------------------------------------------- 照劇本走完

async def play_round_1(t):
    st = t.st
    gash = t.slot(PLAYER, "M-001")
    await t.send({"type": "flip_pages", "count": 0})                               # 2:不翻頁
    assert st.players[PLAYER].pos == 2
    await t.send({"type": "play_card", "page": 2, "slot_uid": gash.uid})          # 3:裝上高嶺清麿
    assert gash.partner == "P-001"
    await t.go()                                                                  # 4:對手 pass
    assert st.action_player == PLAYER and st.battle is None
    await t.send({"type": "use_field_ability", "zone": "partner", "slot_uid": gash.uid})   # 5:清麿的效果
    assert gash.partner is None
    await t.go()
    opp_pos = st.players[OPP].pos
    await t.send({"type": "declare_attack", "page": 3, "slot_uid": gash.uid})     # 6:ザケル攻擊
    await t.go()                                                                  # 對手同意、不能防禦
    assert st.battle is not None and st.battle.step == "effects" and st.battle.defense_spell is None
    await t.send({"type": "pass"})
    await t.go()
    assert st.battle is None and st.players[OPP].pos == opp_pos + 2               # 對手魔書受 1 點傷害
    await t.send({"type": "pass"})                                                # 7:連續 pass
    await t.go()


async def play_round_2(t, protect):
    st = t.st
    assert st.turn_player == OPP and st.battle_in is not None                     # 8:對手準備攻擊
    assert st.players[PLAYER].pos == 4 and st.players[PLAYER].mp == 3
    await t.send({"type": "play_card", "page": 4})                                # 插入行動:放出ティオ
    tio = t.slot(PLAYER, "Ex-005")
    assert t.events("battle_in_voided")
    await t.go()
    assert st.battle_in is not None                                               # 9:對手重新準備攻擊
    await t.send({"type": "battle_in_response", "allow": True})
    await t.send({"type": "declare_defense", "page": 5, "slot_uid": tio.uid})     # 10:ティオ+セウシル
    await t.go()
    await t.send({"type": "pass"})
    await t.go()
    showdown = t.events("showdown")[-1]
    assert (showdown["attacker_total"], showdown["defender_total"]) == (6000, 8000)
    assert st.players[PLAYER].pos == 4                                            # 沒有受到傷害
    assert st.battle_in is not None                                               # 11:第二次攻擊
    await t.send({"type": "battle_in_response", "allow": True})
    await t.send({"type": "no_defense"})
    await t.go()
    await t.send({"type": "pass"})
    assert st.pending is not None and st.pending.kind == "protect"
    await t.send({"type": "choose", "value": protect(t)})
    coins = t.events("coin_flipped")
    assert coins and not any(m.kind == "full_immune" for m in st.modifiers)       # 擲反面,不發動
    await t.go()
    await t.send({"type": "pass"})                                                # 12:連續 pass
    await t.go()


async def play_round_3(t):
    st = t.st
    assert st.turn_player == PLAYER and st.phase == "start"
    pos = st.players[PLAYER].pos                  # 回合 2 不保護時魔書受了傷害,已翻到ブリ與ザケル的對頁
    await t.send({"type": "flip_pages", "count": 1})                              # 13:翻 1 張
    pos += 2
    assert st.players[PLAYER].pos == pos and st.players[PLAYER].book[pos - 1:pos + 1] == ["E-003", "S-001"]
    mp = st.players[PLAYER].mp
    await t.send({"type": "use_book_card", "page": pos})                          # 14:ブリ
    assert st.players[PLAYER].mp == mp + 2
    await t.go()
    gash = t.slot(PLAYER, "M-001")
    await t.send({"type": "declare_attack", "page": pos + 1, "slot_uid": gash.uid})   # 15:ザケル
    await t.go()
    assert st.battle is not None and st.battle.step == "effects" and st.battle.defense_spell == "S-037"
    await t.send({"type": "use_field_ability", "zone": "mamodo", "slot_uid": gash.uid})   # 16:ガッシュの效果
    await t.go()
    await t.send({"type": "pass"})
    await t.go()
    showdown = t.events("showdown")[-1]
    assert (showdown["attacker_total"], showdown["defender_total"]) == (7000, 6000)   # 17:攻擊成功


PROTECTS = {
    "none": lambda t: None,
    "gash": lambda t: t.slot(PLAYER, "M-001").uid,
    "tio": lambda t: t.slot(PLAYER, "Ex-005").uid,
}


@pytest.mark.parametrize("protect", list(PROTECTS))
def test_full_script(protect):
    async def go():
        t = await new_tutorial()
        await play_round_1(t)
        await play_round_2(t, PROTECTS[protect])
        opp_pos = t.st.players[OPP].pos
        await play_round_3(t)
        return t, opp_pos
    t, opp_pos = run(go())
    assert t.st.players[OPP].pos == opp_pos + 2 and t.st.phase == BATTLE


def test_free_step_deviation_pass_early():
    # 自由步驟提早 pass(不放出ティオ就同意進入戰鬥、不防禦):對手照狀態行動,回合 3 照樣能走
    async def go():
        t = await new_tutorial()
        await play_round_1(t)
        st = t.st
        while st.turn_player == OPP:
            if st.pending is not None:
                await t.send({"type": "choose", "value": None})
            elif st.battle_in is not None:
                await t.send({"type": "battle_in_response", "allow": True})
            elif st.battle is not None and st.battle.step == "defense":
                await t.send({"type": "no_defense"})
            else:
                await t.send({"type": "pass"})
            await t.go()
        await play_round_3(t)
        return t
    t = run(go())
    assert t.events("showdown")[-1]["attacker_total"] == 7000
