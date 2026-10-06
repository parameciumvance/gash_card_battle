"""效果樹:以不可變節點組合卡片效果,由直譯器逐層解決。

- 節點是 frozen dataclass,樹在註冊時建好並存入 EFFECTS,對局期間不變。
- 效果在停點(等玩家選擇 / 擲幣確認 / 待命)停下時,只把續體 (effect_id, path, ctx, floor)
  這份純資料存進 PendingChoice / Standby,不存閉包;醒來時由 resume() 依 path 找回節點繼續。
- path 是停點節點本身的位置(從根往下的子節點索引);節點完成後沿 path 上溯,
  Sequence 依序解決其後尚未執行的兄弟節點。floor 是上溯的下界(Standby 觸發的子樹為脫離式,
  不再上溯到排程它的祖先)。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

from ..cards import PARTNER
from ..state import DUR_TURN, DUR_UNTIL_END_NEXT_TURN, PendingChoice
from . import registry as reg
from .primitives import (
    add_modifier, add_power, add_restriction, add_spell_power, attach_partner_from_book, coin_info,
    discard_from_book, discard_option, discard_partner, flip_coins,
    heal_slot, mark_opp_mp_reduced, own_book_turn_effect, page_option, play_mamodo_from_book, reduce_mp,
    reduce_opponent_mp, return_to_book,
    schedule_standby, slot_option, take_from_book,
    turn_pages,
)

# 引擎內建的 pending kind,Choose.prompt 不得與之相同
RESERVED_KINDS = frozenset({
    "protect", "damage_order", "deploy_page", "injure_instead_target",
    "coin_confirm", "opp_coin_redo",
})

# SpellRider 中可以傳效果樹的掛鉤(其餘欄位是旗標或數值查詢,不是效果)
RIDER_TREE_HOOKS = ("on_declare", "on_damage", "on_win", "on_defense_damaged")

CHOICE_KEY = "tree_choice"   # Choose 建立的 pending:引擎只依此鍵把回應交給 resume
CONT_KEY = "tree_cont"       # Coin / Standby 的 callback payload,只由 effect_tree_resume 讀取
TOKEN_KEY = "tree_token"

EFFECTS: dict[str, "Effect"] = {}
TREE_HOOKS: set[tuple[str, str]] = set()   # 已以效果樹註冊的 (卡號, 掛鉤)

# Coin 同步 callback 用的行程內暫存(不進 state):token -> {"results": [...]}
_INFLIGHT: dict[int, dict] = {}
_next_token = 0


@dataclass(frozen=True)
class Run:
    """一次直譯的執行環境(行程內暫存,不進 state)。"""
    game: Any
    batch: list
    effect_id: str

    def cont(self, ctx: dict, path: tuple, floor: int = 0) -> dict:
        return {"effect_id": self.effect_id, "path": list(path), "ctx": dict(ctx), "floor": floor}


def _check_who(who: str) -> None:
    if who not in ("self", "opponent"):
        raise ValueError(f"對象須為 'self' 或 'opponent',收到 {who!r}")


def _who(ctx: dict, who: str) -> int:
    """把 "self" / "opponent" 換成玩家編號(相對於效果擁有者 ctx["player"])。"""
    return ctx["player"] if who == "self" else 1 - ctx["player"]


# ================================================================ 節點基底

@dataclass(frozen=True)
class Effect:
    """效果節點。run() 回傳 True=已完成、False=已停下(續體已存入 state)。"""

    def children(self) -> tuple["Effect", ...]:
        return ()

    @property
    def may_suspend(self) -> bool:
        return any(c.may_suspend for c in self.children())

    def run(self, rt: Run, ctx: dict, path: tuple) -> bool:
        raise NotImplementedError

    def resume(self, rt: Run, ctx: dict, value: Any, path: tuple, floor: int) -> None:
        raise NotImplementedError(f"{type(self).__name__} 不是停點節點")

    def leave(self, ctx: dict) -> dict:
        """子樹非同步完成、上溯經過本節點時呼叫,回傳繼續往外層使用的 ctx。預設不變;
        AsOpponent 用它把 ctx["player"] 換回原本的效果擁有者。"""
        return ctx

    def resume_choice(self, rt: Run, ctx: dict, value: Any, path: tuple, floor: int) -> None:
        """由 CHOICE_KEY 續體恢復(玩家回應了此節點建立的 pending)。預設與 resume 相同;
        同時會停在「擲幣確認鏈」與「玩家選擇」兩種停點的節點(CoinWithPaidReflip)才需要區分。"""
        self.resume(rt, ctx, value, path, floor)


@dataclass(frozen=True)
class Nothing(Effect):
    def run(self, rt, ctx, path):
        return True


@dataclass(frozen=True)
class Sequence(Effect):
    steps: tuple[Effect, ...] = ()

    def children(self):
        return self.steps

    def run(self, rt, ctx, path):
        for i, step in enumerate(self.steps):
            if not step.run(rt, ctx, path + (i,)):
                return False
        return True


@dataclass(frozen=True)
class When(Effect):
    """條件成立解決 then,否則解決 otherwise(預設無效果)。條件只在進入時判斷一次。"""
    cond: Any = None
    then: Effect = field(default_factory=Nothing)
    otherwise: Effect = field(default_factory=Nothing)

    def children(self):
        return (self.then, self.otherwise)

    def run(self, rt, ctx, path):
        idx = 0 if self.cond.test(rt.game, ctx) else 1
        return self.children()[idx].run(rt, ctx, path + (idx,))


@dataclass(frozen=True)
class AsOpponent(Effect):
    """以對手的視角解決 then:子樹內 ctx["player"] 為對手,選擇由對手決定、「自己」指對手。

    完成後外層的 ctx["player"] 仍是效果擁有者(同步完成時外層 ctx 本來就沒被換;
    非同步恢復時由 leave 換回)。子樹綁定的名稱(Choose 的 bind 等)會留在 ctx 中。
    """
    then: Effect = field(default_factory=Nothing)

    def children(self):
        return (self.then,)

    def run(self, rt, ctx, path):
        inner = dict(ctx)
        inner["player"] = 1 - ctx["player"]
        done = self.then.run(rt, inner, path + (0,))
        if done:
            ctx.update({k: v for k, v in inner.items() if k != "player"})
        return done

    def leave(self, ctx):
        out = dict(ctx)
        out["player"] = 1 - ctx["player"]
        return out


def opponent_then_self(effect: Effect) -> "Sequence":
    """效果文「相手は…。自分は…。(この順で)」:先以對手視角、再以自己視角各解決一次 effect。"""
    return Sequence(steps=(AsOpponent(then=effect), effect))


@dataclass(frozen=True)
class Ref:
    """引用 ctx 中先前綁定的名稱(例如 Choose 綁定的 slot UID)。"""
    name: str


# ================================================================ 條件

@dataclass(frozen=True)
class SideIs:
    side: str

    def test(self, game, ctx) -> bool:
        return ctx.get("side") == self.side


@dataclass(frozen=True)
class HeadsAtLeast:
    count: int = 1

    def test(self, game, ctx) -> bool:
        return sum(ctx["results"]) >= self.count


@dataclass(frozen=True)
class Always:
    """恆真條件:用於「不分支,只是需要先擲幣」的效果(如依正面數量計算數值)。"""

    def test(self, game, ctx) -> bool:
        return True


@dataclass(frozen=True)
class Bound:
    """ctx 中先前綁定的 name 等於 value(依 Choose 的選擇分支,如 S-043 融合 / 分裂)。"""
    name: str
    value: Any

    def test(self, game, ctx) -> bool:
        return ctx.get(self.name) == self.value


@dataclass(frozen=True)
class OwnMpAtMost:
    """自己 MP 不超過 n(M-002)。"""
    n: int = 0

    def test(self, game, ctx) -> bool:
        return game.state.players[ctx["player"]].mp <= self.n


@dataclass(frozen=True)
class OpponentOpenPagesLackDefenseSpell:
    """對手目前翻開的頁中,沒有可用來防禦的術卡(M-018)。"""

    def test(self, game, ctx) -> bool:
        opp = game.state.players[1 - ctx["player"]]
        return not any(game.db[opp.card_at(p)].type == "spell" and game.db[opp.card_at(p)].can_defend()
                       for p in opp.open_pages())


@dataclass(frozen=True)
class DetachedFromSelf:
    """觸發事件 stack_detached 是本魔物身上的 number 被分離入墓(M-028)。"""
    number: str

    def test(self, game, ctx) -> bool:
        ev = ctx["event"]
        return ev.get("slot") == ctx["self_slot"] and ev.get("detached") == self.number


@dataclass(frozen=True)
class OwnHasPartner:
    """自己場上至少有一隻魔物裝有搭檔(E-027)。"""

    def test(self, game, ctx) -> bool:
        return any(s.partner for s in game.state.players[ctx["player"]].slots)


@dataclass(frozen=True)
class OwnFieldHas:
    """自己場上有頂層為 number 的魔物(S-048 需要巴爾多羅本體 / P-006 需要コルル(変身後))。
    可當 When 條件(test),也可當啟動條件(fn(game, player, slot))。"""
    number: str

    def test(self, game, ctx) -> bool:
        return any(s.top == self.number for s in game.state.players[ctx["player"]].slots)

    def __call__(self, game, player, slot=None) -> bool:
        return self.test(game, {"player": player})


@dataclass(frozen=True)
class HeadsCount:
    """恰好 count 次正面(E-005 的三分支需精確計數,而非門檻)。"""
    count: int = 0

    def test(self, game, ctx) -> bool:
        return sum(ctx["results"]) == self.count


# ================================================================ 使用前置條件(reg.event 的 when=,簽名 fn(game, player))

def has_own_mamodo(game, player) -> bool:
    return bool(game.state.players[player].slots)


def has_partner_discarded_this_turn(game, player) -> bool:
    ps = game.state.players[player]
    return any(n in ps.discarded_this_turn and game.db[n].type == PARTNER for n in ps.discard)


def has_own_injured_mamodo(game, player) -> bool:
    return any(s.injured for s in game.state.players[player].slots)


def has_two_or_more_mamodo(game, player) -> bool:
    return len(game.state.players[player].slots) >= 2


def opponent_has_mamodo(game, player) -> bool:
    return bool(game.state.players[1 - player].slots)


def opponent_has_partner(game, player) -> bool:
    return any(s.partner for s in game.state.players[1 - player].slots)


@dataclass(frozen=True)
class HasOptions:
    """使用條件:選項規格至少有一個選項才能使用。可當事件卡的 when=(fn(game, player)),
    也可當啟動型效果的 condition=(fn(game, player, slot),ctx 另含 self_slot)。"""
    spec: Any

    def __call__(self, game, player, slot=None) -> bool:
        ctx = {"player": player}
        if slot is not None:
            ctx["self_slot"] = slot.uid
        return bool(self.spec.options(game, ctx))


@dataclass(frozen=True)
class All:
    """所有使用條件都成立(參數原樣轉給每個條件)。"""
    conds: tuple = ()

    def __init__(self, *conds):
        object.__setattr__(self, "conds", tuple(conds))

    def __call__(self, *args) -> bool:
        return all(c(*args) for c in self.conds)


# ================================================================ 選項規格 / 觸發時機

@dataclass(frozen=True)
class OwnMamodo:
    """自己場上的魔物;以穩定的 slot UID 作為選項值。"""

    def options(self, game, ctx) -> list[dict]:
        player = ctx["player"]
        return [slot_option(player, s) for s in game.state.players[player].slots]

    def validate(self, game, ctx, value) -> None:
        from ..engine import IllegalCommand
        if game.state.slot_by_uid(ctx["player"], value if isinstance(value, int) else -1) is None:
            raise IllegalCommand("choose.invalid", "須選擇自己場上的魔物")


@dataclass(frozen=True)
class PlayablePartnerInDiscard:
    """棄牌堆中的搭檔卡:其家族魔物在場上尚有空位,且場上沒有同名搭檔(E-011)。"""

    @staticmethod
    def _targets(game, player) -> list[dict]:
        ps = game.state.players[player]
        out = []
        for i, number in enumerate(ps.discard):
            card = game.db[number]
            if card.type != PARTNER:
                continue
            slot = next((s for s in ps.slots
                         if game.db[s.top].related_mamodo == card.related_mamodo
                         and s.partner is None), None)
            if slot is None:
                continue
            if any(game.db[s.partner].name_ja == card.name_ja for s in ps.slots if s.partner):
                continue
            out.append(discard_option(player, i, number, slot_uid=slot.uid))
        return out

    def options(self, game, ctx) -> list[dict]:
        return self._targets(game, ctx["player"])

    def validate(self, game, ctx, value) -> None:
        from ..engine import IllegalCommand
        if value not in {t["value"] for t in self._targets(game, ctx["player"])}:
            raise IllegalCommand("choose.invalid", "須選擇棄牌區中可放出的搭檔卡")


@dataclass(frozen=True)
class OwnOpenPages:
    """自己魔本目前翻開、且卡片仍在魔本中的頁(M-016)。選項值為頁碼。"""

    def options(self, game, ctx) -> list[dict]:
        ps = game.state.players[ctx["player"]]
        return [page_option(ctx["player"], p, ps.card_at(p)) for p in ps.open_pages()]

    def validate(self, game, ctx, value) -> None:
        from ..engine import IllegalCommand
        if value not in game.state.players[ctx["player"]].open_pages():
            raise IllegalCommand("choose.invalid", "須選擇目前翻開頁面的卡")


@dataclass(frozen=True)
class OwnEarlierPages:
    """自己魔本中比目前翻開頁更前面、且卡片仍在魔本中的頁(M-016)。選項值為頁碼。"""

    def options(self, game, ctx) -> list[dict]:
        ps = game.state.players[ctx["player"]]
        return [page_option(ctx["player"], p, ps.card_at(p))
                for p in range(1, ps.pos) if p not in ps.consumed_pages]

    def validate(self, game, ctx, value) -> None:
        from ..engine import IllegalCommand
        if value not in {o["value"] for o in self.options(game, ctx)}:
            raise IllegalCommand("choose.invalid", "須選擇之前頁面的卡")


@dataclass(frozen=True)
class OwnBookPartnerNamed:
    """自己魔本中(尚未離開的)名稱為 name 的搭檔卡頁(M-020 大海恵 / M-021 窪塚泳太)。"""
    name: str

    def options(self, game, ctx) -> list[dict]:
        ps = game.state.players[ctx["player"]]
        return [page_option(ctx["player"], p, ps.card_at(p))
                for p in range(1, 33)
                if p not in ps.consumed_pages
                and game.db[ps.card_at(p)].type == PARTNER
                and game.db[ps.card_at(p)].name_ja == self.name]

    def validate(self, game, ctx, value) -> None:
        from ..engine import IllegalCommand
        if value not in {o["value"] for o in self.options(game, ctx)}:
            raise IllegalCommand("choose.invalid", "須選擇魔本中對應的搭檔卡")


@dataclass(frozen=True)
class OpponentInjuredMamodo:
    """對手場上負傷的魔物(M-029)。選項值為 slot UID。"""

    def options(self, game, ctx) -> list[dict]:
        opp = 1 - ctx["player"]
        return [slot_option(opp, s) for s in game.state.players[opp].slots if s.injured]

    def validate(self, game, ctx, value) -> None:
        from ..engine import IllegalCommand
        slot = game.state.slot_by_uid(1 - ctx["player"], value if isinstance(value, int) else -1)
        if slot is None or not slot.injured:
            raise IllegalCommand("choose.invalid", "須選擇對手場上負傷的魔物")


@dataclass(frozen=True)
class DiscardedCardsToReturn:
    """可選擇放回魔本空頁的自己棄牌堆卡(卡號屬於 numbers);魔本沒有空頁時沒有選項。
    選項值為棄牌索引,另附一個「不使用」(value=None, label="skip")——效果文為「…できる」(M-025)。"""
    numbers: tuple = ()

    def _targets(self, game, player) -> list[dict]:
        ps = game.state.players[player]
        if not ps.consumed_pages:
            return []
        return [discard_option(player, i, n) for i, n in enumerate(ps.discard) if n in self.numbers]

    def options(self, game, ctx) -> list[dict]:
        targets = self._targets(game, ctx["player"])
        return targets + [{"value": None, "label": "skip"}] if targets else []

    def validate(self, game, ctx, value) -> None:
        from ..engine import IllegalCommand
        if value is not None and value not in {t["value"] for t in self._targets(game, ctx["player"])}:
            raise IllegalCommand("choose.invalid", "須選擇棄牌區的羅布諾斯卡")


@dataclass(frozen=True)
class OwnEmptyBookPages:
    """自己魔本的空頁(卡片已離開的頁),依頁序(M-025 放回)。選項值為頁碼。"""

    def options(self, game, ctx) -> list[dict]:
        return [page_option(ctx["player"], p) for p in sorted(game.state.players[ctx["player"]].consumed_pages)]

    def validate(self, game, ctx, value) -> None:
        from ..engine import IllegalCommand
        if value not in game.state.players[ctx["player"]].consumed_pages:
            raise IllegalCommand("choose.invalid", "須選擇魔本的空頁")


@dataclass(frozen=True)
class OwnPartneredMamodo:
    """自己場上裝有搭檔的魔物;選項值為 slot UID,顯示的卡為其搭檔(E-027 選保留哪張)。"""

    def options(self, game, ctx) -> list[dict]:
        player = ctx["player"]
        return [slot_option(player, s, s.partner) for s in game.state.players[player].slots if s.partner]

    def validate(self, game, ctx, value) -> None:
        from ..engine import IllegalCommand
        slot = game.state.slot_by_uid(ctx["player"], value if isinstance(value, int) else -1)
        if slot is None or not slot.partner:
            raise IllegalCommand("choose.invalid", "須選擇自己場上裝有搭檔的魔物")


def _partner_slots(game, player, card) -> list:
    """player 場上可裝備 card(搭檔卡)的魔物:同家族、尚未裝備搭檔。"""
    return [s for s in game.state.players[player].slots
            if game.db[s.top].related_mamodo == card.related_mamodo and s.partner is None]


@dataclass(frozen=True)
class AttachablePartnerPagesInOwnBook:
    """自己魔本中(尚未離開的)搭檔卡頁,且場上有可裝備它的魔物(E-027)。選項值為頁碼。"""

    def options(self, game, ctx) -> list[dict]:
        player = ctx["player"]
        ps = game.state.players[player]
        out = []
        for p in range(1, 33):
            if p in ps.consumed_pages:
                continue
            card = game.db[ps.card_at(p)]
            if card.type == PARTNER and _partner_slots(game, player, card):
                out.append(page_option(player, p, card.number))
        return out

    def validate(self, game, ctx, value) -> None:
        from ..engine import IllegalCommand
        if value not in {o["value"] for o in self.options(game, ctx)}:
            raise IllegalCommand("choose.invalid", "須選擇魔本中可放出的搭檔卡")


@dataclass(frozen=True)
class SlotsForBookPartner:
    """可裝備自己魔本 page 綁定那頁搭檔卡的魔物(E-027)。選項值為 slot UID。"""
    page: Ref = Ref("page")

    def options(self, game, ctx) -> list[dict]:
        ps = game.state.players[ctx["player"]]
        card = game.db[ps.card_at(ctx[self.page.name])]
        return [slot_option(ctx["player"], s) for s in _partner_slots(game, ctx["player"], card)]

    def validate(self, game, ctx, value) -> None:
        from ..engine import IllegalCommand
        if value not in {o["value"] for o in self.options(game, ctx)}:
            raise IllegalCommand("choose.invalid", "須選擇可裝備此搭檔的魔物")


@dataclass(frozen=True)
class OwnInjuredMamodo:
    """自己場上負傷的魔物(E-007)。"""

    def options(self, game, ctx) -> list[dict]:
        player = ctx["player"]
        return [slot_option(player, s) for s in game.state.players[player].slots if s.injured]

    def validate(self, game, ctx, value) -> None:
        from ..engine import IllegalCommand
        slot = game.state.slot_by_uid(ctx["player"], value if isinstance(value, int) else -1)
        if slot is None or not slot.injured:
            raise IllegalCommand("choose.invalid", "須選擇自己場上的負傷魔物")


@dataclass(frozen=True)
class OpponentMamodo:
    """對手場上的魔物(E-024)。"""

    def options(self, game, ctx) -> list[dict]:
        opp = 1 - ctx["player"]
        return [slot_option(opp, s) for s in game.state.players[opp].slots]

    def validate(self, game, ctx, value) -> None:
        from ..engine import IllegalCommand
        if game.state.slot_by_uid(1 - ctx["player"], value if isinstance(value, int) else -1) is None:
            raise IllegalCommand("choose.invalid", "須選擇對手場上的魔物")


@dataclass(frozen=True)
class PartnerDiscardedThisTurn:
    """棄牌堆中本回合入墓的搭檔卡,且其家族魔物在場上尚有空位(尚未裝備搭檔)。"""

    @staticmethod
    def _targets(game, player) -> list[dict]:
        ps = game.state.players[player]
        out = []
        for i, number in enumerate(ps.discard):
            card = game.db[number]
            if card.type != PARTNER or number not in ps.discarded_this_turn:
                continue
            slot = next((s for s in ps.slots
                         if game.db[s.top].related_mamodo == card.related_mamodo
                         and s.partner is None), None)
            if slot is None:
                continue
            out.append(discard_option(player, i, number, slot_uid=slot.uid))
        return out

    def options(self, game, ctx) -> list[dict]:
        return self._targets(game, ctx["player"])

    def validate(self, game, ctx, value) -> None:
        from ..engine import IllegalCommand
        if not any(t["value"] == value for t in self._targets(game, ctx["player"])):
            raise IllegalCommand("choose.invalid", "須選擇可放回的搭檔")


@dataclass(frozen=True)
class OpponentPartneredMamodo:
    """對手場上裝有搭檔的魔物;以 slot UID 作為選項值,顯示的卡為其搭檔。"""

    def options(self, game, ctx) -> list[dict]:
        opp = 1 - ctx["player"]
        return [slot_option(opp, s, s.partner) for s in game.state.players[opp].slots if s.partner]

    def validate(self, game, ctx, value) -> None:
        from ..engine import IllegalCommand
        slot = game.state.slot_by_uid(1 - ctx["player"], value if isinstance(value, int) else -1)
        if slot is None or not slot.partner:
            raise IllegalCommand("choose.invalid", "須選擇對手場上的搭檔卡")


@dataclass(frozen=True)
class DeployableMamodoInOwnBook:
    """自己魔本中可放出的魔物頁(E-012):場上未滿;變身後的魔物需場上有其變身前魔物,
    其餘不得與場上魔物同名。選項值為頁碼。"""

    @staticmethod
    def _targets(game, player) -> list[dict]:
        from ..engine import MAX_FIELD_MAMODO, same_name_in_play
        from ..cards import MAMODO
        ps = game.state.players[player]
        if len(ps.slots) >= MAX_FIELD_MAMODO:
            return []
        out = []
        for p in range(1, 33):
            if p in ps.consumed_pages:
                continue
            number = ps.card_at(p)
            card = game.db[number]
            if card.type != MAMODO:
                continue
            if number in reg.STACK_ON:
                if not any(s.top in reg.STACK_ON[number] for s in ps.slots):
                    continue
            elif same_name_in_play(game, player, card):
                continue
            out.append(page_option(player, p, number))
        return out

    def options(self, game, ctx) -> list[dict]:
        return self._targets(game, ctx["player"])

    def validate(self, game, ctx, value) -> None:
        from ..engine import IllegalCommand
        if value not in {t["value"] for t in self._targets(game, ctx["player"])}:
            raise IllegalCommand("choose.invalid", "須選擇魔本中可放出的魔物卡")


@dataclass(frozen=True)
class OpponentBookCards:
    """對手魔本中(尚未離開的)指定類型的卡;exclude_last 時排除末頁(E-016 術 / E-017 事件)。"""
    card_type: str
    exclude_last: bool = False

    def options(self, game, ctx) -> list[dict]:
        opp = game.state.players[1 - ctx["player"]]
        out = []
        for p in range(1, 33):
            if p in opp.consumed_pages or (self.exclude_last and p == 32):
                continue
            if game.db[opp.card_at(p)].type == self.card_type:
                out.append(page_option(1 - ctx["player"], p, opp.card_at(p)))
        return out

    def validate(self, game, ctx, value) -> None:
        from ..engine import IllegalCommand
        if value not in {o["value"] for o in self.options(game, ctx)}:
            raise IllegalCommand("choose.invalid", "須選擇對手書中對應類型的卡")


@dataclass(frozen=True)
class OwnBookCopiesOf:
    """自己魔本中(尚未離開的)卡號為 number 的頁(S-043 / S-048)。"""
    number: str

    def options(self, game, ctx) -> list[dict]:
        ps = game.state.players[ctx["player"]]
        return [page_option(ctx["player"], p, ps.card_at(p))
                for p in range(1, 33)
                if p not in ps.consumed_pages and ps.card_at(p) == self.number]

    def validate(self, game, ctx, value) -> None:
        from ..engine import IllegalCommand
        if value not in {o["value"] for o in self.options(game, ctx)}:
            raise IllegalCommand("choose.invalid", "須選擇魔本中的指定卡")


@dataclass(frozen=True)
class RobnosTransformMode:
    """羅布諾斯雙向轉換的模式(S-043):場上二體 ≥2 可「融合」、有完全體可「分裂」。"""
    double: str = "M-024"
    complete: str = "M-025"

    def _counts(self, game, ctx):
        slots = game.state.players[ctx["player"]].slots
        return (sum(1 for s in slots if s.top == self.double),
                sum(1 for s in slots if s.top == self.complete))

    def options(self, game, ctx) -> list[dict]:
        doubles, completes = self._counts(game, ctx)
        out = []
        if doubles >= 2:
            out.append({"value": "fuse", "label": "s043_fuse"})
        if completes:
            out.append({"value": "split", "label": "s043_split"})
        return out

    def validate(self, game, ctx, value) -> None:
        from ..engine import IllegalCommand
        doubles, completes = self._counts(game, ctx)
        if value == "fuse":
            if doubles < 2:
                raise IllegalCommand("choose.invalid", "場上羅布諾斯(二體)不足 2 隻")
        elif value == "split":
            if not completes:
                raise IllegalCommand("choose.invalid", "場上沒有羅布諾斯(完全體)")
        else:
            raise IllegalCommand("choose.invalid", "無效的選擇")


@dataclass(frozen=True)
class NextStartPhase:
    kind: ClassVar[str] = "start_phase"


# ================================================================ 停點節點

@dataclass(frozen=True)
class Choose(Effect):
    """玩家選擇:單一選項自動解決;多選項建立 pending,回應後把選到的值綁定到 bind。"""
    target: Any = None
    bind: str = "choice"
    prompt: str = ""
    then: Effect = field(default_factory=Nothing)

    def children(self):
        return (self.then,)

    @property
    def may_suspend(self) -> bool:
        return True

    def run(self, rt, ctx, path):
        game = rt.game
        options = self.target.options(game, ctx)
        if not options:
            return True
        if len(options) == 1:
            ctx[self.bind] = options[0]["value"]
            return self.then.run(rt, ctx, path + (0,))
        game.state.pending = PendingChoice(
            kind=self.prompt, player=ctx["player"], options=options, source=ctx["source"],
            data={CHOICE_KEY: rt.cont(ctx, path)})
        game.emit(rt.batch, "choice_required", kind=self.prompt, player=ctx["player"],
                  options=options)
        return False

    def resume(self, rt, ctx, value, path, floor):
        self.target.validate(rt.game, ctx, value)   # 驗證失敗拋出,引擎保留 pending
        ctx[self.bind] = value
        if self.then.run(rt, ctx, path + (0,)):
            _ascend(rt, ctx, path, floor)


@dataclass(frozen=True)
class Standby(Effect):
    """排程待命(脫離式):排程後立即完成;觸發時只解決 then,不再上溯。

    then 只能同步完成(不含會停下的節點),由註冊時的 validate_tree 檢查。
    """
    at: Any = field(default_factory=NextStartPhase)
    expires: str = "turn"
    then: Effect = field(default_factory=Nothing)

    def children(self):
        return (self.then,)

    @property
    def may_suspend(self) -> bool:
        return False

    def run(self, rt, ctx, path):
        schedule_standby(
            rt.game, rt.batch, kind=self.at.kind, source=ctx["source"], owner=ctx["player"],
            data={"callback": "effect_tree_resume", "expires": self.expires,
                  CONT_KEY: rt.cont(ctx, path, floor=len(path) + 1)})
        return True

    def resume(self, rt, ctx, value, path, floor):
        self.then.run(rt, ctx, path + (0,))


def _flip(rt: Run, ctx: dict, path: tuple, count: int, flipper: int):
    """擲幣並走 M-012 / M-019 確認鏈。確認鏈同步結束時回傳結果;停在確認 pending 時回傳 None,
    之後由 effect_tree_resume 以 CONT_KEY 續體呼叫 path 節點的 resume(value=結果)。"""
    global _next_token
    _next_token += 1
    token = _next_token
    holder: dict = {}
    _INFLIGHT[token] = holder
    try:
        flip_coins(rt.game, rt.batch, flipper, count, ctx["source"], "effect_tree_resume",
                   {CONT_KEY: rt.cont(ctx, path), TOKEN_KEY: token})
    finally:
        _INFLIGHT.pop(token, None)
    return holder.get("results")


@dataclass(frozen=True)
class NegateNextDamageThisBattle(Effect):
    """[待命] 本場戰鬥中,自己頂層為 number 的魔物下一次受到傷害時不受該傷害,之後解決 then
    (脫離式,同 Standby;then 只能同步完成)。ctx["shielded"] 為受保護魔物的 UID(P-006)。"""
    number: str = ""
    then: Effect = field(default_factory=Nothing)

    def children(self):
        return (self.then,)

    @property
    def may_suspend(self) -> bool:
        return False

    def run(self, rt, ctx, path):
        slot = next((s for s in rt.game.state.players[ctx["player"]].slots if s.top == self.number), None)
        if slot is None:
            return True
        ctx = dict(ctx, shielded=slot.uid)
        schedule_standby(rt.game, rt.batch, kind="negate_damage", source=ctx["source"], owner=ctx["player"],
                         data={"slot_uid": slot.uid, "after": "effect_tree_resume", "expires": "battle",
                               CONT_KEY: rt.cont(ctx, path, floor=len(path) + 1)})
        return True

    def resume(self, rt, ctx, value, path, floor):
        self.then.run(rt, ctx, path + (0,))


@dataclass(frozen=True)
class Coin(Effect):
    """由 flipper 擲 count 枚硬幣(沿用 M-012 / M-019 確認鏈),確認後依條件走 then / otherwise。

    flipper="opponent" 時由對手擲(E-020):M-012 由對手決定、M-019 由效果擁有者決定。
    ctx["player"] 始終是效果擁有者,不因擲幣者改變。
    """
    count: int = 1
    on: Any = field(default_factory=HeadsAtLeast)
    then: Effect = field(default_factory=Nothing)
    otherwise: Effect = field(default_factory=Nothing)
    flipper: str = "self"

    def __post_init__(self):
        _check_who(self.flipper)

    def children(self):
        return (self.then, self.otherwise)

    @property
    def may_suspend(self) -> bool:
        return True

    def run(self, rt, ctx, path):
        results = _flip(rt, ctx, path, self.count, _who(ctx, self.flipper))
        if results is None:
            return False    # 進入確認鏈 pending,之後由 resume 接手
        return self._branch(rt, ctx, path, results)

    def _branch(self, rt, ctx, path, results) -> bool:
        ctx["results"] = [bool(r) for r in results]
        idx = 0 if self.on.test(rt.game, ctx) else 1
        return self.children()[idx].run(rt, ctx, path + (idx,))

    def resume(self, rt, ctx, value, path, floor):
        if self._branch(rt, ctx, path, value):
            _ascend(rt, ctx, path, floor)


@dataclass(frozen=True)
class CoinWithPaidReflip(Effect):
    """擲 count 枚硬幣;符合 on 則解決 then。不符合時,若 MP ≥ cost 就詢問是否付 cost 重擲,
    可重複任意次(E-011)。

    迴圈只發生在本節點內部:玩家選擇重擲時付費後重新執行本節點(同一個 path),
    直到結果符合、玩家停止或 MP 不足時,本節點才算完成並上溯一次。
    兩種停點:擲幣確認鏈(CONT_KEY → resume)、重擲詢問(CHOICE_KEY → resume_choice)。
    """
    count: int = 1
    on: Any = field(default_factory=HeadsAtLeast)
    cost: int = 0
    prompt: str = ""
    then: Effect = field(default_factory=Nothing)

    def children(self):
        return (self.then,)

    @property
    def may_suspend(self) -> bool:
        return True

    def run(self, rt, ctx, path):
        return self._flip_and_branch(rt, ctx, path, floor=0)

    def _flip_and_branch(self, rt, ctx, path, floor) -> bool:
        results = _flip(rt, ctx, path, self.count, ctx["player"])
        if results is None:
            return False
        return self._after_results(rt, ctx, path, floor, results)

    def _after_results(self, rt, ctx, path, floor, results) -> bool:
        ctx["results"] = [bool(r) for r in results]
        if self.on.test(rt.game, ctx):
            return self.then.run(rt, ctx, path + (0,))
        player = ctx["player"]
        if rt.game.state.players[player].mp < self.cost:
            return True     # 無法重擲:本節點結束,無效果
        rt.game.state.pending = PendingChoice(
            kind=self.prompt, player=player, source=ctx["source"],
            options=[{"value": True, "label": "pay_reflip"}, {"value": False, "label": "stop"}],
            data={CHOICE_KEY: rt.cont(ctx, path, floor)}, info=coin_info(results))
        rt.game.emit(rt.batch, "choice_required", kind=self.prompt, player=player)
        return False

    def resume(self, rt, ctx, value, path, floor):
        """擲幣確認鏈結束,value 為結果。"""
        if self._after_results(rt, ctx, path, floor, value):
            _ascend(rt, ctx, path, floor)

    def resume_choice(self, rt, ctx, value, path, floor):
        """玩家回應重擲詢問:True 付費重擲、False 停止。驗證先於任何狀態變更。"""
        from ..engine import IllegalCommand, pay_mp
        if value is not True and value is not False:
            raise IllegalCommand("choose.invalid", "須選擇是否重擲")
        player = ctx["player"]
        if value and rt.game.state.players[player].mp < self.cost:
            raise IllegalCommand("choose.invalid", "MP 不足以重擲")
        if value:
            pay_mp(rt.game, rt.batch, player, self.cost, ctx["source"])
            if not self._flip_and_branch(rt, ctx, path, floor):
                return
        _ascend(rt, ctx, path, floor)


# ================================================================ 葉節點(包裝 primitives)

@dataclass(frozen=True)
class AddPower(Effect):
    """對 target 綁定的魔物加魔力。執行時才依 UID 重新查找;目標已離場則無效果、無事件。"""
    amount: int = 0
    duration: str = ""
    target: Ref = Ref("slot")

    def run(self, rt, ctx, path):
        player = ctx["player"]
        slot = rt.game.state.slot_by_uid(player, ctx[self.target.name])
        if slot is None:
            return True
        add_power(rt.game, rt.batch, source=ctx["source"], owner=player, target_player=player,
                  target_slot=slot.uid, amount=self.amount, duration=self.duration)
        return True


@dataclass(frozen=True)
class RestrictOpponent(Effect):
    """對對手設置限制旗標(禁術卡等)。"""
    flag: str = ""
    duration: str = ""

    def run(self, rt, ctx, path):
        player = ctx["player"]
        add_restriction(rt.game, rt.batch, source=ctx["source"], owner=player,
                        target_player=1 - player, flag=self.flag, duration=self.duration)
        return True


@dataclass(frozen=True)
class NegateAttack(Effect):
    """使目前戰鬥的攻擊無效。"""

    def run(self, rt, ctx, path):
        battle = rt.game.state.battle
        if battle is None:
            return True
        battle.attack_negated = True
        battle.data["attack_negated_by"] = ctx["source"]
        rt.game.emit(rt.batch, "attack_negated", source=ctx["source"], player=ctx["player"])
        return True


@dataclass(frozen=True)
class MakeNextAttackUndefendable(Effect):
    """[待命] 本回合下一場戰鬥的攻擊不可被防禦。mamodo 指定時,只在由該家族的魔物攻擊時生效
    (以使用術的魔物判定,指令術由該魔物使用時也適用)(P-001)。"""
    mamodo: str | None = None

    def run(self, rt, ctx, path):
        data = {"expires": "next_battle"}
        if self.mamodo:
            data["mamodo"] = self.mamodo
        schedule_standby(rt.game, rt.batch, kind="attack_undefendable",
                         source=ctx["source"], owner=ctx["player"], data=data)
        return True


@dataclass(frozen=True)
class MakeAttackUndefendable(Effect):
    """使目前這場戰鬥的攻擊立即不可被防禦(與 MakeNextAttackUndefendable 不同:
    後者是排程給下一場戰鬥的待命,這裡是宣告時直接作用於當前戰鬥)。"""

    def run(self, rt, ctx, path):
        battle = rt.game.state.battle
        if battle is not None:
            battle.attack_undefendable = True
        return True


@dataclass(frozen=True)
class ScheduleInjureInsteadNextWin(Effect):
    """[待命] 本回合下一場戰鬥獲勝時,改為負傷對手 1 隻魔物代替魔本傷害(S-057)。"""

    def run(self, rt, ctx, path):
        schedule_standby(rt.game, rt.batch, kind="injure_instead",
                         source=ctx["source"], owner=ctx["player"])
        return True


@dataclass(frozen=True)
class GrantFullImmune(Effect):
    """令自己的魔本與魔物至對手下個結束階段前不受傷害(S-037 / S-041)。"""

    def run(self, rt, ctx, path):
        player = ctx["player"]
        add_modifier(rt.game, rt.batch, kind="full_immune", source=ctx["source"], owner=player,
                     duration=DUR_UNTIL_END_NEXT_TURN, target_player=player)
        return True


@dataclass(frozen=True)
class AdjustDefenseDamage(Effect):
    """調整目前戰鬥中防禦方承受的傷害值(S-027:-1)。"""
    amount: int = 0

    def run(self, rt, ctx, path):
        battle = rt.game.state.battle
        if battle is None:
            return True
        battle.data["defense_damage_delta"] = battle.data.get("defense_damage_delta", 0) + self.amount
        rt.game.emit(rt.batch, "effect_applied", source=ctx["source"], amount=self.amount)
        return True


@dataclass(frozen=True)
class DisableBookProtection(Effect):
    """本場戰鬥中,防禦方不能保護魔本(S-035)。"""

    def run(self, rt, ctx, path):
        battle = rt.game.state.battle
        if battle is None:
            return True
        battle.data["no_protect_book"] = True
        rt.game.emit(rt.batch, "effect_applied", source=ctx["source"])
        return True


@dataclass(frozen=True)
class AddAttackBonusPerHeads(Effect):
    """依 ctx["results"](Coin 擲出的結果)的正面數量,為本場戰鬥的攻擊魔力加值(S-040)。"""
    per_head: int = 0

    def run(self, rt, ctx, path):
        battle = rt.game.state.battle
        if battle is None:
            return True
        amount = sum(ctx["results"]) * self.per_head
        add_spell_power(battle, "attack", ctx["source"], amount)
        rt.game.emit(rt.batch, "effect_applied", source=ctx["source"], amount=amount)
        return True


@dataclass(frozen=True)
class HealSlot(Effect):
    """令 target 綁定的魔物回復健康狀態(E-006)。執行時才依 UID 重新查找,目標已離場則無效果。"""
    target: Ref = Ref("slot")

    def run(self, rt, ctx, path):
        player = ctx["player"]
        slot = rt.game.state.slot_by_uid(player, ctx[self.target.name])
        if slot is None:
            return True
        heal_slot(rt.game, rt.batch, player, slot, ctx["source"])
        return True


@dataclass(frozen=True)
class TurnPagesForward(Effect):
    """target("self" / "opponent")的魔本翻頁(效果造成,不獲得 MP);翻完即敗(E-005 / E-014)。
    翻自己的魔本時算「自分の魔本をめくる」效果,受 P-010 的「合計1回」限制。"""
    leaves: int = 1
    target: str = "self"

    def __post_init__(self):
        _check_who(self.target)

    def run(self, rt, ctx, path):
        if self.target == "self":
            own_book_turn_effect(rt.game, rt.batch, ctx["player"], self.leaves, ctx["source"])
        else:
            turn_pages(rt.game, rt.batch, _who(ctx, self.target), self.leaves, ctx["source"])
        return True


@dataclass(frozen=True)
class TurnPagesBack(Effect):
    """自己魔本回翻頁(E-005 正正);算「自分の魔本をもどす」效果,受 P-018 的「合計1回」限制。"""
    leaves: int = 1

    def run(self, rt, ctx, path):
        own_book_turn_effect(rt.game, rt.batch, ctx["player"], -self.leaves, ctx["source"])
        return True


@dataclass(frozen=True)
class GainMp(Effect):
    """target("self" / "opponent")的 MP 增加固定值(E-020)。"""
    amount: int = 0
    target: str = "self"

    def __post_init__(self):
        _check_who(self.target)

    def run(self, rt, ctx, path):
        from ..engine import gain_mp
        gain_mp(rt.game, rt.batch, _who(ctx, self.target), self.amount, ctx["source"])
        return True


@dataclass(frozen=True)
class GainMpPerHeads(Effect):
    """依 ctx["results"] 的正面數量,為自己增加 MP(E-026:每正面 +2)。"""
    per_head: int = 0

    def run(self, rt, ctx, path):
        from ..engine import gain_mp
        amount = sum(ctx["results"]) * self.per_head
        gain_mp(rt.game, rt.batch, ctx["player"], amount, ctx["source"])
        return True


@dataclass(frozen=True)
class AttachPartnerFromDiscard(Effect):
    """把 Choose(spec) 選中的搭檔卡從棄牌堆裝到對應魔物上,並觸發其登場效果(E-011 / E-022)。

    spec 須提供 _targets(game, player) → [{"value": 棄牌索引, "slot_uid": ...}],與 Choose 用的相同。
    """
    spec: Any = field(default_factory=PartnerDiscardedThisTurn)
    index: Ref = Ref("choice")

    def run(self, rt, ctx, path):
        game = rt.game
        player = ctx["player"]
        ps = game.state.players[player]
        idx = ctx[self.index.name]
        targets = {t["value"]: t for t in self.spec._targets(game, player)}
        t = targets.get(idx)
        if t is None:      # 場面已變化(Choose 已驗證過,理論上不會發生),防禦性放棄
            return True
        number = ps.discard.pop(idx)
        slot = game.state.slot_by_uid(player, t["slot_uid"])
        slot.partner = number
        game.emit(rt.batch, "card_played", player=player, card=number, slot=slot.uid,
                  zone="partner", from_discard=True)
        if number in reg.ON_PLAY:
            reg.ON_PLAY[number](game, rt.batch, player, slot)
        return True


@dataclass(frozen=True)
class DiscardChosenPartner(Effect):
    """棄掉 Choose(OpponentPartneredMamodo()) 選中魔物身上的搭檔卡(S-039)。"""
    target: Ref = Ref("choice")

    def run(self, rt, ctx, path):
        opp = 1 - ctx["player"]
        slot = rt.game.state.slot_by_uid(opp, ctx[self.target.name])
        if slot is None or not slot.partner:
            return True
        discard_partner(rt.game, rt.batch, opp, slot, ctx["source"])
        return True


@dataclass(frozen=True)
class AddPowerToAllOpponentMamodo(Effect):
    """對手場上每一隻魔物各加一筆魔力 modifier(S-033:-2000)。"""
    amount: int = 0
    duration: str = ""

    def run(self, rt, ctx, path):
        player = ctx["player"]
        opp = 1 - player
        for s in rt.game.state.players[opp].slots:
            add_modifier(rt.game, rt.batch, kind="power", source=ctx["source"], owner=player,
                         duration=self.duration, target_player=opp, target_slot=s.uid,
                         amount=self.amount)
        return True


@dataclass(frozen=True)
class MarkInjuredMamodoDiscarded(Effect):
    """本場戰鬥中,因此術負傷的魔物直接入墓而非負傷(S-031)。"""

    def run(self, rt, ctx, path):
        battle = rt.game.state.battle
        if battle is not None:
            battle.data["injure_to_discard"] = True
        return True


@dataclass(frozen=True)
class AddDefenseSelfBonus(Effect):
    """以此術防禦時魔力加值(S-016)。事件 source 沿用遷移前的 "defense_bonus"。"""
    amount: int = 0

    def run(self, rt, ctx, path):
        battle = rt.game.state.battle
        if battle is None:
            return True
        add_spell_power(battle, "defense", ctx["source"], self.amount, kind="defense_self")
        rt.game.emit(rt.batch, "effect_applied", source="defense_bonus", amount=self.amount)
        return True


@dataclass(frozen=True)
class AddAttackSelfBonus(Effect):
    """以此術攻擊時魔力加值(S-017)。事件 source 沿用遷移前的 "attack_bonus"。"""
    amount: int = 0

    def run(self, rt, ctx, path):
        battle = rt.game.state.battle
        if battle is None:
            return True
        add_spell_power(battle, "attack", ctx["source"], self.amount)
        rt.game.emit(rt.batch, "effect_applied", source="attack_bonus", amount=self.amount)
        return True


@dataclass(frozen=True)
class ReduceOpponentMp(Effect):
    """對手 MP 減少(不足額時歸 0)(S-020)。"""
    amount: int = 0

    def run(self, rt, ctx, path):
        reduce_opponent_mp(rt.game, rt.batch, ctx["player"], self.amount, ctx["source"])
        return True


@dataclass(frozen=True)
class GainMpPerDamage(Effect):
    """依 ctx["amount"](本次受到的傷害 = 翻頁數)為自己增加 MP(S-056:每點 +2)。"""
    per_point: int = 0

    def run(self, rt, ctx, path):
        from ..engine import gain_mp
        gain_mp(rt.game, rt.batch, ctx["player"], ctx["amount"] * self.per_point, ctx["source"])
        return True


@dataclass(frozen=True)
class DamageOpponentBookAndAllMamodo(Effect):
    """獲勝時接管傷害流程:對防方魔本造成本術傷害,並對其場上每隻魔物各造成 1 點傷害(S-036)。

    須搭配 SpellRider 的 on_win_owns_damage=True,引擎才不會再走預設的魔本傷害。
    傷害流程可能進入引擎自己的 pending(保護 / 順序),那是引擎的停點,不是效果樹的停點。
    """

    def run(self, rt, ctx, path):
        from ..engine import _attack_damage_amount, _start_damage
        game = rt.game
        player = ctx["player"]
        opp = 1 - player
        battle = game.state.battle
        amount = _attack_damage_amount(game, battle)
        items = []
        if amount > 0:
            items.append({"kind": "book", "player": opp, "amount": amount})
        items += [{"kind": "slot", "player": opp, "slot_uid": s.uid, "amount": 1}
                  for s in list(game.state.players[opp].slots)]
        _start_damage(game, rt.batch, items,
                      {"cause": "battle_attack", "source": battle.attack_spell,
                       "source_player": player, "amount": amount})
        return True


@dataclass(frozen=True)
class RestrictBothPlayers(Effect):
    """雙方各設置一個限制旗標,依玩家 0、1 的順序(E-002 禁術 / E-008 搭檔效果失效)。"""
    flag: str = ""
    duration: str = ""

    def run(self, rt, ctx, path):
        for p in (0, 1):
            add_restriction(rt.game, rt.batch, source=ctx["source"], owner=ctx["player"],
                            target_player=p, flag=self.flag, duration=self.duration)
        return True


@dataclass(frozen=True)
class ZeroBothPlayersMp(Effect):
    """雙方 MP 歸 0;MP 本來就是 0 的一方不發事件(E-004)。對手 MP≥1 時記錄為「減少對手 MP」的效果。"""

    def run(self, rt, ctx, path):
        if rt.game.state.players[1 - ctx["player"]].mp >= 1:   # 效果文註記:MP≥1 時視為「減少 MP」
            mark_opp_mp_reduced(rt.game, ctx["player"])
        for p in (0, 1):
            ps = rt.game.state.players[p]
            if ps.mp:
                rt.game.emit(rt.batch, "mp_changed", player=p, delta=-ps.mp, mp=0,
                             reason=ctx["source"])
                ps.mp = 0
        return True


@dataclass(frozen=True)
class BorrowPartner(Effect):
    """本回合借用 Choose(OpponentPartneredMamodo()) 選中的對手搭檔卡效果(E-010)。"""
    target: Ref = Ref("choice")

    def run(self, rt, ctx, path):
        player = ctx["player"]
        opp_slot = rt.game.state.slot_by_uid(1 - player, ctx[self.target.name])
        if opp_slot is None or not opp_slot.partner:
            return True
        add_modifier(rt.game, rt.batch, kind="borrow_partner", source=ctx["source"], owner=player,
                     duration=DUR_TURN, target_player=player,
                     data={"slot_uid": opp_slot.uid, "card": opp_slot.partner})
        return True


@dataclass(frozen=True)
class ScheduleNoProtectBookNextBattle(Effect):
    """[待命] 本回合下一場戰鬥,對手不能保護魔本(E-013)。"""

    def run(self, rt, ctx, path):
        schedule_standby(rt.game, rt.batch, kind="no_protect_book",
                         source=ctx["source"], owner=ctx["player"])
        return True


@dataclass(frozen=True)
class PeekOpponentOpenPages(Effect):
    """檢視對手目前翻開的頁面(只對使用者揭露)(E-014)。"""

    def run(self, rt, ctx, path):
        player = ctx["player"]
        opp = rt.game.state.players[1 - player]
        rt.game.emit(rt.batch, "pages_peeked", player=1 - player, viewer=player,
                     cards=[{"page": p, "card": opp.card_at(p)} for p in opp.open_pages()])
        return True


@dataclass(frozen=True)
class DiscardChosenMamodo(Effect):
    """把 target 綁定的自己魔物棄掉(E-019)。執行時依 UID 重新查找,已離場則無效果。"""
    target: Ref = Ref("slot")

    def run(self, rt, ctx, path):
        from ..engine import _discard_slot
        player = ctx["player"]
        slot = rt.game.state.slot_by_uid(player, ctx[self.target.name])
        if slot is None:
            return True
        _discard_slot(rt.game, rt.batch, player, slot, reason=ctx["source"])
        return True


@dataclass(frozen=True)
class HealFirstInjuredMamodo(Effect):
    """回復自己場上第一隻負傷魔物;沒有負傷魔物則無效果(E-021)。"""

    def run(self, rt, ctx, path):
        player = ctx["player"]
        slot = next((s for s in rt.game.state.players[player].slots if s.injured), None)
        if slot is not None:
            heal_slot(rt.game, rt.batch, player, slot, ctx["source"])
        return True


@dataclass(frozen=True)
class BoostPartneredMamodo(Effect):
    """[持續] 自己場上裝有搭檔的魔物魔力加值(E-023)。"""
    amount: int = 0
    duration: str = ""

    def run(self, rt, ctx, path):
        player = ctx["player"]
        add_modifier(rt.game, rt.batch, kind="power_partnered", source=ctx["source"], owner=player,
                     duration=self.duration, target_player=player, amount=self.amount)
        return True


@dataclass(frozen=True)
class LockChosenOpponentMamodo(Effect):
    """本回合封鎖 target 綁定的對手魔物:不能使用其魔物效果與術(E-024)。

    沿用遷移前的作法:先以 add_restriction 建立(此時 modifier_added 事件的 target_slot 為 None),
    再把 modifier 的 target_slot 設為選中的魔物。
    """
    target: Ref = Ref("choice")

    def run(self, rt, ctx, path):
        from ..state import MAMODO_LOCKED
        player = ctx["player"]
        slot = rt.game.state.slot_by_uid(1 - player, ctx[self.target.name])
        if slot is None:
            return True
        m = add_restriction(rt.game, rt.batch, source=ctx["source"], owner=player,
                            target_player=1 - player, flag=MAMODO_LOCKED, duration=DUR_TURN)
        m.target_slot = slot.uid
        return True


@dataclass(frozen=True)
class RevealOpponentBook(Effect):
    """對使用者揭露對手魔本中尚未離開的所有頁(E-016 / E-017)。"""

    def run(self, rt, ctx, path):
        player = ctx["player"]
        opp = rt.game.state.players[1 - player]
        rt.game.emit(rt.batch, "book_revealed", player=1 - player, viewer=player,
                     cards=[{"page": p, "card": opp.card_at(p)}
                            for p in range(1, 33) if p not in opp.consumed_pages])
        return True


@dataclass(frozen=True)
class DiscardFromOpponentBookPayCost(Effect):
    """棄掉對手魔本中 page 綁定的那頁卡,使用者 MP 減少該卡費用(不足額歸 0)(E-016 / E-017)。"""
    page: Ref = Ref("page")

    def run(self, rt, ctx, path):
        game = rt.game
        player = ctx["player"]
        page = ctx[self.page.name]
        cost = game.db[game.state.players[1 - player].card_at(page)].cost or 0
        discard_from_book(game, rt.batch, 1 - player, page, ctx["source"])
        reduce_mp(game, rt.batch, player, cost, ctx["source"])
        return True


@dataclass(frozen=True)
class DeployMamodoFromBook(Effect):
    """把自己魔本 page 綁定的魔物放到場上;變身後的魔物疊放到其變身前魔物上(E-012)。"""
    page: Ref = Ref("page")

    def run(self, rt, ctx, path):
        from ..state import MamodoSlot
        game = rt.game
        player = ctx["player"]
        page = ctx[self.page.name]
        ps = game.state.players[player]
        number = ps.card_at(page)
        ps.consumed_pages.add(page)
        if number in reg.STACK_ON:
            slot = next(s for s in ps.slots if s.top in reg.STACK_ON[number])
            slot.stack.append(number)
            slot.injured = False
            game.emit(rt.batch, "card_played", player=player, card=number, slot=slot.uid,
                      zone="mamodo", stacked=True)
        else:
            slot = MamodoSlot(uid=game.state.next_uid(), stack=[number])
            ps.slots.append(slot)
            game.emit(rt.batch, "card_played", player=player, card=number, slot=slot.uid,
                      zone="mamodo")
        if number in reg.ON_PLAY:
            reg.ON_PLAY[number](game, rt.batch, player, slot)
        return True


@dataclass(frozen=True)
class PlayMamodoFromBook(Effect):
    """經 play_mamodo_from_book 放出 page 綁定的魔物(受場上 / 同名上限約束)(S-043 融合)。"""
    page: Ref = Ref("page")

    def run(self, rt, ctx, path):
        play_mamodo_from_book(rt.game, rt.batch, ctx["player"], ctx[self.page.name])
        return True


@dataclass(frozen=True)
class StackFromBookOnto(Effect):
    """把自己魔本 page 綁定的卡疊放到場上頂層為 base 的魔物上,並回復健康(S-048)。"""
    base: str = ""
    page: Ref = Ref("page")

    def run(self, rt, ctx, path):
        game = rt.game
        player = ctx["player"]
        slot = next((s for s in game.state.players[player].slots if s.top == self.base), None)
        if slot is None:
            return True
        number = take_from_book(game, rt.batch, player, ctx[self.page.name])
        slot.stack.append(number)
        slot.injured = False
        game.emit(rt.batch, "card_played", player=player, card=number, slot=slot.uid,
                  zone="mamodo", stacked=True, from_book=True)
        return True


@dataclass(frozen=True)
class DiscardOwnMamodoByNumber(Effect):
    """把自己場上頂層為 number 的魔物,依場上順序棄掉前 count 隻(S-043)。"""
    number: str = ""
    count: int = 1

    def run(self, rt, ctx, path):
        from ..engine import _discard_slot
        player = ctx["player"]
        targets = [s for s in rt.game.state.players[player].slots if s.top == self.number]
        for s in targets[:self.count]:
            _discard_slot(rt.game, rt.batch, player, s, reason=ctx["source"])
        return True


@dataclass(frozen=True)
class PlaceMamodoFromBookUpTo(Effect):
    """自魔本依頁序放出至多 count 張卡號為 number 的魔物;無頁可放或放不出(上限)即停(S-043 分裂)。"""
    number: str = ""
    count: int = 1

    def run(self, rt, ctx, path):
        spec = OwnBookCopiesOf(self.number)
        for _ in range(self.count):
            pages = spec.options(rt.game, ctx)
            if not pages:
                break
            if play_mamodo_from_book(rt.game, rt.batch, ctx["player"], pages[0]["value"]) is None:
                break
        return True


@dataclass(frozen=True)
class ReduceOpponentMpUnlessReducedLastTurn(Effect):
    """對手 MP 減少 amount;若直前的回合自己用過任何「減少對手 MP」的效果,則減 0(E-018 日版)。

    被限制成減 0 時,本次仍算「使用了減少對手 MP 的效果」,一樣記錄。
    記錄存在 PlayerState.opp_mp_reduced_turns,由 primitives.reduce_opponent_mp /
    mark_opp_mp_reduced 寫入(S-020、P-002、P-019、E-004 等都會寫)。
    """
    amount: int = 0

    def run(self, rt, ctx, path):
        st = rt.game.state
        player = ctx["player"]
        if st.turn_no - 1 in st.players[player].opp_mp_reduced_turns:
            rt.game.emit(rt.batch, "effect_applied", source=ctx["source"], skipped=True)
            mark_opp_mp_reduced(rt.game, player)
            return True
        reduce_opponent_mp(rt.game, rt.batch, player, self.amount, ctx["source"])
        return True


@dataclass(frozen=True)
class DiscardOtherPartners(Effect):
    """自己場上的搭檔卡只保留 keep 綁定那隻魔物身上的,其餘依場上順序棄掉(E-027)。"""
    keep: Ref = Ref("keep")

    def run(self, rt, ctx, path):
        player = ctx["player"]
        keep = ctx[self.keep.name]
        for s in list(rt.game.state.players[player].slots):
            if s.partner and s.uid != keep:
                discard_partner(rt.game, rt.batch, player, s, ctx["source"])
        return True


@dataclass(frozen=True)
class AttachPartnerFromBookPage(Effect):
    """把自己魔本 page 綁定那頁的搭檔卡裝到 slot 綁定的魔物上(觸發登場效果)(E-027)。"""
    page: Ref = Ref("page")
    slot: Ref = Ref("slot")

    def run(self, rt, ctx, path):
        player = ctx["player"]
        slot = rt.game.state.slot_by_uid(player, ctx[self.slot.name])
        if slot is None:
            return True
        attach_partner_from_book(rt.game, rt.batch, player, ctx[self.page.name], slot)
        return True


@dataclass(frozen=True)
class IncreaseSelfDamage(Effect):
    """這隻魔物的魔物效果與術造成的傷害 +amount(M-005)。"""
    amount: int = 0
    duration: str = ""

    def run(self, rt, ctx, path):
        add_modifier(rt.game, rt.batch, kind="damage_delta", source=ctx["source"], owner=ctx["player"],
                     duration=self.duration, target_player=ctx["player"],
                     target_slot=ctx["self_slot"], amount=self.amount)
        return True


@dataclass(frozen=True)
class PreventDamageToSelf(Effect):
    """這隻魔物不受傷害(M-013 / M-015)。"""
    duration: str = ""

    def run(self, rt, ctx, path):
        add_modifier(rt.game, rt.batch, kind="no_damage", source=ctx["source"], owner=ctx["player"],
                     duration=self.duration, target_player=ctx["player"], target_slot=ctx["self_slot"])
        return True


@dataclass(frozen=True)
class ScheduleNextSpellBonus(Effect):
    """[待命] 本回合下一場戰鬥中,mamodo 使用的術費用 +cost_delta、魔力 +power_delta(M-008 / P-007)。
    optional:由使用者在宣告術時選擇是否套用(M-008「1低いコストで使うことができる。そうしたなら…」)。"""
    mamodo: str = ""
    power_delta: int = 0
    cost_delta: int = 0
    optional: bool = False

    def run(self, rt, ctx, path):
        schedule_standby(rt.game, rt.batch, kind="spell_bonus", source=ctx["source"], owner=ctx["player"],
                         data={"mamodo": self.mamodo, "power_delta": self.power_delta,
                               "cost_delta": self.cost_delta, "expires": "next_battle",
                               **({"optional": True} if self.optional else {})})
        return True


@dataclass(frozen=True)
class ScheduleSkipEndFlip(Effect):
    """[待命] 本回合結束階段不翻魔本(M-030)。"""

    def run(self, rt, ctx, path):
        schedule_standby(rt.game, rt.batch, kind="skip_end_flip", source=ctx["source"], owner=ctx["player"])
        return True


@dataclass(frozen=True)
class DiscardFromOpponentBook(Effect):
    """棄掉對手魔本中 page 綁定的那頁卡(M-011)。"""
    page: Ref = Ref("page")

    def run(self, rt, ctx, path):
        discard_from_book(rt.game, rt.batch, 1 - ctx["player"], ctx[self.page.name], ctx["source"])
        return True


@dataclass(frozen=True)
class SwapBookPages(Effect):
    """交換自己魔本 a、b 兩頁的卡(M-016)。"""
    a: Ref = Ref("open")
    b: Ref = Ref("earlier")

    def run(self, rt, ctx, path):
        ps = rt.game.state.players[ctx["player"]]
        a, b = ctx[self.a.name], ctx[self.b.name]
        ps.book[a - 1], ps.book[b - 1] = ps.book[b - 1], ps.book[a - 1]
        rt.game.emit(rt.batch, "effect_applied", source=ctx["source"], pages=[a, b])
        return True


@dataclass(frozen=True)
class DiscardChosenOpponentMamodo(Effect):
    """把 target 綁定的對手魔物棄掉(M-029)。執行時依 UID 重新查找,已離場則無效果。"""
    target: Ref = Ref("choice")

    def run(self, rt, ctx, path):
        from ..engine import _discard_slot
        opp = 1 - ctx["player"]
        slot = rt.game.state.slot_by_uid(opp, ctx[self.target.name])
        if slot is None:
            return True
        _discard_slot(rt.game, rt.batch, opp, slot, reason=ctx["source"])
        return True


@dataclass(frozen=True)
class ReturnDiscardToBook(Effect):
    """把自己棄牌堆 card 綁定索引的那張卡放回魔本 page 綁定的空頁(M-025)。"""
    card: Ref = Ref("card")
    page: Ref = Ref("page")

    def run(self, rt, ctx, path):
        ps = rt.game.state.players[ctx["player"]]
        idx, page = ctx[self.card.name], ctx[self.page.name]
        if not 0 <= idx < len(ps.discard) or page not in ps.consumed_pages:
            return True
        number = ps.discard.pop(idx)
        return_to_book(rt.game, rt.batch, ctx["player"], number, page)
        return True


@dataclass(frozen=True)
class StealOpponentMp(Effect):
    """對手 MP 減少 amount,自己增加實際減少的量(P-002)。"""
    amount: int = 0

    def run(self, rt, ctx, path):
        from ..engine import gain_mp
        actual = reduce_opponent_mp(rt.game, rt.batch, ctx["player"], self.amount, ctx["source"])
        gain_mp(rt.game, rt.batch, ctx["player"], actual, ctx["source"])
        return True


@dataclass(frozen=True)
class IncreaseAttackDamage(Effect):
    """本場戰鬥中,自己攻擊的魔物造成的傷害 +amount(P-003)。"""
    amount: int = 0

    def run(self, rt, ctx, path):
        from ..state import DUR_BATTLE
        b = rt.game.state.battle
        add_modifier(rt.game, rt.batch, kind="damage_delta", source=ctx["source"], owner=ctx["player"],
                     duration=DUR_BATTLE, target_player=ctx["player"], target_slot=b.attack_slot,
                     amount=self.amount)
        return True


@dataclass(frozen=True)
class DoubleAttackDamage(Effect):
    """本場戰鬥中,自己攻擊的魔物造成的傷害 ×2(P-004)。"""

    def run(self, rt, ctx, path):
        from ..state import DUR_BATTLE
        b = rt.game.state.battle
        add_modifier(rt.game, rt.batch, kind="damage_double", source=ctx["source"], owner=ctx["player"],
                     duration=DUR_BATTLE, target_player=ctx["player"], target_slot=b.attack_slot)
        return True


@dataclass(frozen=True)
class SpellsCostZeroThisTurn(Effect):
    """本回合 mamodo 使用的術費用為 0(以使用術的魔物判定,指令術也適用)(P-005)。"""
    mamodo: str = ""

    def run(self, rt, ctx, path):
        add_modifier(rt.game, rt.batch, kind="spell_cost_zero", source=ctx["source"], owner=ctx["player"],
                     duration=DUR_TURN, target_player=ctx["player"], data={"mamodo": self.mamodo})
        return True


@dataclass(frozen=True)
class DiscardTopMamodoCard(Effect):
    """把 target 綁定魔物頂層的 number 棄掉、下層留在場上(P-006「下のカードを残して捨て札」)。"""
    number: str = ""
    target: Ref = Ref("shielded")

    def run(self, rt, ctx, path):
        from ..engine import to_discard
        player = ctx["player"]
        slot = rt.game.state.slot_by_uid(player, ctx[self.target.name])
        if slot is None or slot.top != self.number or len(slot.stack) < 2:
            return True
        slot.stack.pop()
        to_discard(rt.game.state.players[player], self.number)
        rt.game.emit(rt.batch, "card_discarded", player=player, card=self.number, zone="mamodo",
                     reason=ctx["source"])
        return True


@dataclass(frozen=True)
class NegateOpponentSpell(Effect):
    """使本場戰鬥中對手的術無效(which 見 CanNegateOpponentSpell)(P-009 / P-016 / P-017)。"""
    which: str = "any"

    def run(self, rt, ctx, path):
        b = rt.game.state.battle
        side = _negatable_opponent_spell(rt.game, ctx["player"], self.which)
        if side == "attack":
            b.attack_negated = True
            b.data["attack_negated_by"] = ctx["source"]
            rt.game.emit(rt.batch, "attack_negated", source=ctx["source"], player=ctx["player"])
        elif side == "defense":
            b.defense_negated = True
            b.data["defense_negated_by"] = ctx["source"]
            rt.game.emit(rt.batch, "defense_negated", source=ctx["source"], player=ctx["player"])
        return True


@dataclass(frozen=True)
class TurnOwnPagesOncePerTurn(Effect):
    """翻自己的魔本 leaves 張,並記錄本回合已用過「翻自己魔本」的效果(P-010);翻完即敗。"""
    leaves: int = 1

    def run(self, rt, ctx, path):
        from .primitives import own_page_turn_effect
        own_page_turn_effect(rt.game, rt.batch, ctx["player"], self.leaves, ctx["source"])
        return True


@dataclass(frozen=True)
class TurnOwnPagesBackOncePerTurn(Effect):
    """回翻自己的魔本 leaves 張,並記錄本回合已用過「回翻自己魔本」的效果(P-018)。"""
    leaves: int = 1

    def run(self, rt, ctx, path):
        from .primitives import own_page_turnback_effect
        own_page_turnback_effect(rt.game, rt.batch, ctx["player"], self.leaves, ctx["source"])
        return True


@dataclass(frozen=True)
class SetPowerZeroThisTurn(Effect):
    """本回合 target 綁定的對手魔物魔力為 0(P-011)。"""
    target: Ref = Ref("choice")

    def run(self, rt, ctx, path):
        opp = 1 - ctx["player"]
        slot = rt.game.state.slot_by_uid(opp, ctx[self.target.name])
        if slot is None:
            return True
        add_modifier(rt.game, rt.batch, kind="power_zero", source=ctx["source"], owner=ctx["player"],
                     duration=DUR_TURN, target_player=opp, target_slot=slot.uid)
        return True


@dataclass(frozen=True)
class ProtectorsDiscardedThisTurn(Effect):
    """本回合「保護」mamodo 造成的傷害而受傷的魔物改為入墓(P-012)。"""
    mamodo: str = ""

    def run(self, rt, ctx, path):
        add_modifier(rt.game, rt.batch, kind="protect_discard", source=ctx["source"], owner=ctx["player"],
                     duration=DUR_TURN, target_player=ctx["player"], data={"mamodo": self.mamodo})
        return True


@dataclass(frozen=True)
class ScheduleSpellFromAnyPage(Effect):
    """[待命] 本回合一次,可使用自己魔本任意頁上名為 spell 的術卡(P-015)。"""
    spell: str = ""

    def run(self, rt, ctx, path):
        schedule_standby(rt.game, rt.batch, kind="spell_any_page", source=ctx["source"], owner=ctx["player"],
                         data={"spell_name": self.spell})
        return True


@dataclass(frozen=True)
class TurnOpponentPagesPerMamodoCardDiscarded(Effect):
    """觸發器:對手每有 1 張魔物卡入墓,翻對手魔本 1 張(P-013)。
    事件 mamodo_discarded(整隻魔物入墓)依其中的魔物卡張數計;card_discarded(疊放頂層單獨入墓、
    自魔本棄卡等)只在該卡為魔物卡時計 1 張。"""

    def run(self, rt, ctx, path):
        from ..cards import MAMODO
        ev = ctx["event"]
        opp = 1 - ctx["player"]
        if ev.get("player") != opp:
            return True
        if ev["type"] == "mamodo_discarded":
            count = sum(1 for n in ev.get("cards", []) if rt.game.db[n].type == MAMODO)
        else:
            count = 1 if rt.game.db[ev["card"]].type == MAMODO else 0
        if count:
            turn_pages(rt.game, rt.batch, opp, count, ctx["source"])
        return True


@dataclass(frozen=True)
class ReduceOpponentMpPerPageTurnedBack(Effect):
    """觸發器:對手每回翻自己的魔本 1 張,對手 MP 減少 per_page(P-019)。"""
    per_page: int = 0

    def run(self, rt, ctx, path):
        ev = ctx["event"]
        pages = -ev.get("count", 0)
        if ev.get("player") == 1 - ctx["player"] and pages > 0:
            reduce_opponent_mp(rt.game, rt.batch, ctx["player"], self.per_page * pages, ctx["source"])
        return True


# ================================================================ 數值查詢(SpellRider.damage_bonus 等)
# 這類掛鉤要「回傳數值」、不執行動作也不會停下,所以不是效果樹節點:
# 它們是不可變、可呼叫的規格物件,直接放進 SpellRider 欄位,不經過 EFFECTS / TREE_HOOKS。

# ---- 魔物 / 搭檔卡的查詢:啟動條件 fn(game, player, slot) -> bool、常駐魔力加成

@dataclass(frozen=True)
class SelfInBattleAs:
    """這隻魔物正以 side("attack" / "defense")身分參與目前的戰鬥(M-001 / M-005 / M-010 / M-017)。"""
    side: str

    def __call__(self, game, player, slot) -> bool:
        b = game.state.battle
        if b is None:
            return False
        if self.side == "attack":
            return b.attacker == player and b.attack_slot == slot.uid
        return b.defender == player and b.defense_slot == slot.uid


@dataclass(frozen=True)
class SelfInjured:
    """這隻魔物是負傷狀態(M-003 加成 / M-013 使用條件)。"""

    def __call__(self, game, player, slot) -> bool:
        return slot.injured


@dataclass(frozen=True)
class SelfHasNoPartner:
    """這隻魔物尚未裝備搭檔(M-020 / M-021)。"""

    def __call__(self, game, player, slot) -> bool:
        return slot.partner is None


@dataclass(frozen=True)
class SelfHasPartner:
    """這隻魔物裝有搭檔(M-004)。"""

    def __call__(self, game, player, slot) -> bool:
        return bool(slot.partner)


@dataclass(frozen=True)
class OwnMamodoAtLeast:
    """自己場上至少 n 隻魔物(M-014)。"""
    n: int = 1

    def __call__(self, game, player, slot) -> bool:
        return len(game.state.players[player].slots) >= self.n


@dataclass(frozen=True)
class OwnBookAtLastPage:
    """自己的魔本翻到最後一頁(M-030)。"""

    def __call__(self, game, player, slot) -> bool:
        return game.state.players[player].pos >= 32


@dataclass(frozen=True)
class Never:
    """永遠不成立:效果不由玩家主動宣告,而由其他流程處理(M-019 於擲幣確認鏈中處理)。"""

    def __call__(self, game, player, slot) -> bool:
        return False


@dataclass(frozen=True)
class OwnAttackBy:
    """目前的戰鬥中,自己是攻方且攻擊的魔物屬於 mamodo 家族(P-003 / P-004:以使用術的魔物判定)。"""
    mamodo: str

    def __call__(self, game, player, slot=None) -> bool:
        b = game.state.battle
        if b is None or b.attacker != player:
            return False
        attacker = game.state.slot_by_uid(player, b.attack_slot)
        return attacker is not None and game.db[attacker.top].related_mamodo == self.mamodo


@dataclass(frozen=True)
class NoBattleDamageModifierFrom:
    """本場戰鬥尚未套用過 source 的傷害加成(「重複しない」:P-003 / P-004)。"""
    source: str

    def __call__(self, game, player, slot=None) -> bool:
        from ..state import DUR_BATTLE
        return not any(m.kind in ("damage_delta", "damage_double") and m.source == self.source
                       and m.duration == DUR_BATTLE for m in game.state.modifiers)


@dataclass(frozen=True)
class CanNegateOpponentSpell:
    """目前的戰鬥中,對手有可被無效的術(P-009 any / P-016 attack / P-017 defense)。
    attack:自己是防方、對手以術攻擊(無術攻擊不算)且尚未被無效;defense:自己是攻方、對手以術防禦且尚未被無效。"""
    which: str = "any"

    def __call__(self, game, player, slot=None) -> bool:
        return _negatable_opponent_spell(game, player, self.which) is not None


def _negatable_opponent_spell(game, player, which):
    """回傳 "attack" / "defense"(可被無效的對手術)或 None。"""
    b = game.state.battle
    if b is None:
        return None
    if which in ("attack", "any") and b.defender == player and b.attack_spell is not None \
            and not b.attack_negated:
        return "attack"
    if which in ("defense", "any") and b.attacker == player and b.defense_spell is not None \
            and not b.defense_negated:
        return "defense"
    return None


@dataclass(frozen=True)
class OwnPageTurnEffectAvailable:
    """本回合尚未使用「翻自己魔本」的效果、也未受「合計1回」限制(P-010;E-005 反反也算;
    依效果文,翻完魔本而敗北也可以使用)。"""

    def __call__(self, game, player, slot=None) -> bool:
        ps = game.state.players[player]
        return not (ps.page_effect_used or ps.page_effect_limited)


@dataclass(frozen=True)
class OwnPageTurnBackEffectAvailable:
    """本回合尚未使用「回翻自己魔本」的效果、也未受「合計1回」限制(P-018;E-005 正正也算)。
    依效果文,魔本在第一頁時也能使用(回翻 0 張,但 P-018 本身仍算 1 次)。"""

    def __call__(self, game, player, slot=None) -> bool:
        ps = game.state.players[player]
        return not (ps.page_back_effect_used or ps.page_back_effect_limited)


@dataclass(frozen=True)
class SelfPowerBonus:
    """只加給提供者本身(頂層為該卡的魔物),且 when 成立時 +amount(M-003 / M-004)。"""
    amount: int = 0
    when: Any = None

    def bonus(self, game, player, slot, provider) -> int:
        return self.amount if slot.top == provider and self.when(game, player, slot) else 0


@dataclass(frozen=True)
class OwnMamodoPowerBonus:
    """提供者在場上時,自己場上每隻魔物在 when 成立時 +amount(M-014)。"""
    amount: int = 0
    when: Any = None

    def bonus(self, game, player, slot, provider) -> int:
        return self.amount if self.when(game, player, slot) else 0


@dataclass(frozen=True)
class PowerBonus:
    """STATIC_POWER 的登記物件:綁定提供者卡號,引擎以 fn(game, player, slot) 查詢。"""
    provider: str
    spec: Any

    def __call__(self, game, player, slot) -> int:
        return self.spec.bonus(game, player, slot, self.provider)


@dataclass(frozen=True)
class CanUseSpellsWithAttr:
    """術相容:這隻魔物可使用其他魔物屬性為 attr 的術(M-023「木」)。fn(game, player, slot, spell) -> bool。"""
    attr: str

    def __call__(self, game, player, slot, spell_card) -> bool:
        return spell_card.attr_name == self.attr


@dataclass(frozen=True)
class CanUseSpellNamed:
    """術相容:這隻魔物可使用 mamodo 家族中名稱「完全等於」name 的術(M-029 可用賈修的「ザケル」;
    「バオウ・ザケルガ」等名稱只是包含 ザケル 的術不算)。fn(game, player, slot, spell) -> bool。"""
    mamodo: str
    name: str

    def __call__(self, game, player, slot, spell_card) -> bool:
        return spell_card.related_mamodo == self.mamodo and spell_card.name_ja == self.name


@dataclass(frozen=True)
class SpellUsesPerTurnWhileCopies:
    """自己場上有 copies 隻以上 number 時,名為 spell 的術卡每張每回合可用 uses 次(M-024 二身一体)。
    fn(game, player, spell_card) -> int | None(None = 不影響)。"""
    spell: str
    uses: int
    number: str
    copies: int

    def __call__(self, game, player, spell_card):
        if spell_card.name_ja != self.spell:
            return None
        count = sum(1 for s in game.state.players[player].slots if s.top == self.number)
        return self.uses if count >= self.copies else None


@dataclass(frozen=True)
class ImmuneToSpellDamageAtMost:
    """傷害免疫:不受合計魔力 total 以下的術造成的傷害(無術攻擊不算術)(M-031)。
    fn(game, player, slot, ctx) -> bool。"""
    total: int

    def __call__(self, game, player, slot, ctx) -> bool:
        b = game.state.battle
        if b is None or ctx.get("cause") != "battle_attack" or b.attack_spell is None:
            return False
        return b.data.get("attack_total", 0) <= self.total


@dataclass(frozen=True)
class DamageBonusIfAttackTotalAtLeast:
    """攻方合計魔力達 threshold 以上時,此術傷害 +bonus(S-042)。簽名 fn(game, battle) -> int。"""
    threshold: int = 0
    bonus: int = 0

    def __call__(self, game, battle) -> int:
        return self.bonus if battle.data.get("attack_total", 0) >= self.threshold else 0


# ================================================================ 直譯器

def node_at(root: Effect, path) -> Effect:
    node = root
    for i in path:
        kids = node.children()
        if not 0 <= i < len(kids):
            raise LookupError(f"效果樹路徑無效:{tuple(path)}")
        node = kids[i]
    return node


def _ascend(rt: Run, ctx: dict, path: tuple, floor: int) -> None:
    """path 指向的節點已完成:上溯,解決各層 Sequence 中其後尚未執行的兄弟節點。"""
    root = EFFECTS[rt.effect_id]
    while len(path) > floor:
        parent_path, idx = path[:-1], path[-1]
        parent = node_at(root, parent_path)
        if isinstance(parent, Sequence):
            for j in range(idx + 1, len(parent.steps)):
                if not parent.steps[j].run(rt, ctx, parent_path + (j,)):
                    return
        ctx = parent.leave(ctx)
        path = parent_path


def run_effect(game, batch, effect_id: str, ctx: dict) -> None:
    """從根節點開始解決一個效果。"""
    rt = Run(game, batch, effect_id)
    EFFECTS[effect_id].run(rt, dict(ctx), ())


def resume(game, batch, value, data: dict) -> None:
    """依 data 中的續體從停點繼續。value:Choose 為玩家選擇、Coin 為擲幣結果、Standby 無用。"""
    via_choice = CHOICE_KEY in data
    cont = data[CHOICE_KEY] if via_choice else data[CONT_KEY]
    rt = Run(game, batch, cont["effect_id"])
    path = tuple(cont["path"])
    node = node_at(EFFECTS[cont["effect_id"]], path)
    handler = node.resume_choice if via_choice else node.resume
    handler(rt, dict(cont["ctx"]), value, path, cont["floor"])


@reg.choice_resolver("effect_tree_resume")
def _effect_tree_resume(game, batch, value, data):
    holder = _INFLIGHT.get(data.get(TOKEN_KEY))
    if holder is not None:      # Coin.run 尚在執行中(同步 callback):只回填結果,由 Coin.run 就地續行
        holder["results"] = value
        return
    resume(game, batch, value, data)


# ================================================================ 註冊

def validate_tree(root: Effect) -> None:
    """註冊時檢查:節點的 prompt 不可與引擎 pending kind 相同;Standby.then 不可含會停下的節點。"""
    def walk(node: Effect):
        prompt = getattr(node, "prompt", None)
        if prompt is not None and (prompt in RESERVED_KINDS or prompt in reg.CHOICE_RESOLVERS):
            raise ValueError(f"{type(node).__name__}.prompt {prompt!r} 與既有 pending kind 相同")
        if isinstance(node, (Standby, NegateNextDamageThisBattle)) and node.then.may_suspend:
            raise ValueError("Standby.then 只能同步完成,不可包含 Choose / Coin")
        for c in node.children():
            walk(c)
    walk(root)


def check_free(number: str, hook: str, legacy_taken: bool = False) -> None:
    if (number, hook) in TREE_HOOKS or legacy_taken:
        raise ValueError(f"{number} 的 {hook} 掛鉤已被註冊")


def _install(number: str, hook: str, tree: Effect, legacy_taken: bool = False) -> str:
    """先驗證樹與掛鉤未被佔用,通過後才寫入 TREE_HOOKS / EFFECTS(失敗時不留下部分狀態)。"""
    validate_tree(tree)
    check_free(number, hook, legacy_taken)
    effect_id = f"{number}:{hook}"
    TREE_HOOKS.add((number, hook))
    EFFECTS[effect_id] = tree
    return effect_id


def register_event(number: str, tree: Effect):
    effect_id = _install(number, "event", tree, number in reg.EVENT)

    def handler(game, batch, player, page):
        run_effect(game, batch, effect_id, {"player": player, "page": page, "source": number})
    return handler


def register_spell_nonbattle(number: str, tree: Effect):
    effect_id = _install(number, "spell_nonbattle", tree, number in reg.SPELL_NONBATTLE)

    def handler(game, batch, player):
        run_effect(game, batch, effect_id, {"player": player, "source": number})
    return handler


def register_slot_hook(number: str, hook: str, tree: Effect, legacy_taken: bool = False):
    """魔物 / 搭檔卡的效果掛鉤(activated / on_play / on_discard / start_phase)。
    handler 簽名 fn(game, batch, player, slot);ctx["self_slot"] 為該卡所在魔物的 UID。"""
    effect_id = _install(number, hook, tree, legacy_taken)

    def handler(game, batch, player, slot):
        run_effect(game, batch, effect_id, {"player": player, "source": number, "self_slot": slot.uid})
    return handler


def register_trigger(number: str, event_type: str, tree: Effect, legacy_taken: bool = False):
    """[IN PLAY] 事件型觸發器。handler 簽名 fn(game, batch, owner, slot, ev);
    ctx["player"] 為該卡的持有者、ctx["event"] 為觸發事件。"""
    effect_id = _install(number, f"trigger.{event_type}", tree, legacy_taken)

    def handler(game, batch, owner, slot, ev):
        run_effect(game, batch, effect_id,
                   {"player": owner, "source": number, "self_slot": slot.uid, "event": dict(ev)})
    return handler


def rider_hook(number: str, hook: str, tree: Effect):
    """hook 為 RIDER_TREE_HOOKS 之一。呼叫前須已由 spell_rider 確認該卡尚未註冊 rider。

    各掛鉤沿用引擎原本的呼叫簽名,多出來的參數寫進 ctx:
    on_declare(player, side) → ctx["side"];on_defense_damaged(defender, amount) → ctx["amount"]。
    """
    if hook not in RIDER_TREE_HOOKS:
        raise ValueError(f"rider 掛鉤 {hook!r} 不支援效果樹")
    effect_id = _install(number, f"rider.{hook}", tree)
    if hook == "on_declare":
        def on_declare(game, batch, player, side):
            run_effect(game, batch, effect_id, {"player": player, "side": side, "source": number})
        return on_declare
    if hook == "on_defense_damaged":
        def on_defense_damaged(game, batch, defender, amount):
            run_effect(game, batch, effect_id,
                       {"player": defender, "amount": amount, "source": number})
        return on_defense_damaged

    def handler(game, batch, player):     # on_damage / on_win
        run_effect(game, batch, effect_id, {"player": player, "source": number})
    return handler
