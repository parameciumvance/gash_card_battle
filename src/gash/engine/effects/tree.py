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
    add_modifier, add_power, add_restriction, discard_partner, flip_coins, heal_slot,
    reduce_mp, schedule_standby, turn_back_pages, turn_pages,
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
    cond: Any = None
    then: Effect = field(default_factory=Nothing)

    def children(self):
        return (self.then,)

    def run(self, rt, ctx, path):
        if not self.cond.test(rt.game, ctx):
            return True
        return self.then.run(rt, ctx, path + (0,))


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


# ================================================================ 選項規格 / 觸發時機

@dataclass(frozen=True)
class OwnMamodo:
    """自己場上的魔物;以穩定的 slot UID 作為選項值。"""

    def options(self, game, ctx) -> list[dict]:
        return [{"value": s.uid, "card": s.top} for s in game.state.players[ctx["player"]].slots]

    def validate(self, game, ctx, value) -> None:
        from ..engine import IllegalCommand
        if game.state.slot_by_uid(ctx["player"], value if isinstance(value, int) else -1) is None:
            raise IllegalCommand("choose.invalid", "須選擇自己場上的魔物")


@dataclass(frozen=True)
class OwnInjuredMamodo:
    """自己場上負傷的魔物(E-007)。"""

    def options(self, game, ctx) -> list[dict]:
        return [{"value": s.uid, "card": s.top}
                for s in game.state.players[ctx["player"]].slots if s.injured]

    def validate(self, game, ctx, value) -> None:
        from ..engine import IllegalCommand
        slot = game.state.slot_by_uid(ctx["player"], value if isinstance(value, int) else -1)
        if slot is None or not slot.injured:
            raise IllegalCommand("choose.invalid", "須選擇自己場上的負傷魔物")


@dataclass(frozen=True)
class OpponentMamodo:
    """對手場上的魔物(E-024)。"""

    def options(self, game, ctx) -> list[dict]:
        return [{"value": s.uid, "card": s.top} for s in game.state.players[1 - ctx["player"]].slots]

    def validate(self, game, ctx, value) -> None:
        from ..engine import IllegalCommand
        if game.state.slot_by_uid(1 - ctx["player"], value if isinstance(value, int) else -1) is None:
            raise IllegalCommand("choose.invalid", "須選擇對手場上的魔物")


@dataclass(frozen=True)
class PartnerDiscardedThisTurn:
    """棄牌堆中本回合入墓的夥伴卡,且其家族魔物在場上尚有空位(尚未裝備夥伴)。"""

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
            out.append({"value": i, "card": number, "slot_uid": slot.uid})
        return out

    def options(self, game, ctx) -> list[dict]:
        return self._targets(game, ctx["player"])

    def validate(self, game, ctx, value) -> None:
        from ..engine import IllegalCommand
        if not any(t["value"] == value for t in self._targets(game, ctx["player"])):
            raise IllegalCommand("choose.invalid", "須選擇可放回的夥伴")


@dataclass(frozen=True)
class OpponentPartneredMamodo:
    """對手場上裝有夥伴的魔物;以 slot UID 作為選項值,顯示的卡為其夥伴。"""

    def options(self, game, ctx) -> list[dict]:
        opp = 1 - ctx["player"]
        return [{"value": s.uid, "card": s.partner}
                for s in game.state.players[opp].slots if s.partner]

    def validate(self, game, ctx, value) -> None:
        from ..engine import IllegalCommand
        slot = game.state.slot_by_uid(1 - ctx["player"], value if isinstance(value, int) else -1)
        if slot is None or not slot.partner:
            raise IllegalCommand("choose.invalid", "須選擇對手場上的夥伴卡")


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
        global _next_token
        _next_token += 1
        token = _next_token
        holder: dict = {}
        _INFLIGHT[token] = holder
        try:
            flip_coins(rt.game, rt.batch, _who(ctx, self.flipper), self.count, ctx["source"],
                       "effect_tree_resume",
                       {CONT_KEY: rt.cont(ctx, path), TOKEN_KEY: token})
        finally:
            _INFLIGHT.pop(token, None)
        if "results" not in holder:
            return False    # 進入確認鏈 pending,之後由 resume 接手
        return self._branch(rt, ctx, path, holder["results"])

    def _branch(self, rt, ctx, path, results) -> bool:
        ctx["results"] = [bool(r) for r in results]
        idx = 0 if self.on.test(rt.game, ctx) else 1
        return self.children()[idx].run(rt, ctx, path + (idx,))

    def resume(self, rt, ctx, value, path, floor):
        if self._branch(rt, ctx, path, value):
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
        rt.game.emit(rt.batch, "attack_negated", source=ctx["source"], player=ctx["player"])
        return True


@dataclass(frozen=True)
class MakeNextAttackUndefendable(Effect):
    """[待命] 本回合下一場戰鬥的攻擊不可被防禦。"""

    def run(self, rt, ctx, path):
        schedule_standby(rt.game, rt.batch, kind="attack_undefendable",
                         source=ctx["source"], owner=ctx["player"])
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
        battle.data["attack_spell_bonus"] = battle.data.get("attack_spell_bonus", 0) + amount
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
    """target("self" / "opponent")的魔本翻頁(效果造成,不獲得 MP);翻完即敗(E-005 / E-014)。"""
    leaves: int = 1
    target: str = "self"

    def __post_init__(self):
        _check_who(self.target)

    def run(self, rt, ctx, path):
        turn_pages(rt.game, rt.batch, _who(ctx, self.target), self.leaves, ctx["source"])
        return True


@dataclass(frozen=True)
class TurnPagesBack(Effect):
    """自己魔本回翻頁(E-005 正正)。"""
    leaves: int = 1

    def run(self, rt, ctx, path):
        turn_back_pages(rt.game, rt.batch, ctx["player"], self.leaves, ctx["source"])
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
    """把 Choose(PartnerDiscardedThisTurn()) 選中的夥伴卡從棄牌堆裝到對應魔物上(E-022)。"""
    index: Ref = Ref("choice")

    def run(self, rt, ctx, path):
        game = rt.game
        player = ctx["player"]
        ps = game.state.players[player]
        idx = ctx[self.index.name]
        targets = {t["value"]: t for t in PartnerDiscardedThisTurn._targets(game, player)}
        t = targets.get(idx)
        if t is None:      # 場面已變化(Choose 已驗證過,理論上不會發生),防禦性放棄
            return True
        number = ps.discard.pop(idx)
        slot = game.state.slot_by_uid(player, t["slot_uid"])
        slot.partner = number
        game.emit(rt.batch, "card_played", player=player, card=number, slot=slot.uid,
                  zone="partner", from_discard=True)
        return True


@dataclass(frozen=True)
class DiscardChosenPartner(Effect):
    """棄掉 Choose(OpponentPartneredMamodo()) 選中魔物身上的夥伴卡(S-039)。"""
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
        battle.data["defense_self_bonus"] = battle.data.get("defense_self_bonus", 0) + self.amount
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
        battle.data["attack_spell_bonus"] = battle.data.get("attack_spell_bonus", 0) + self.amount
        rt.game.emit(rt.batch, "effect_applied", source="attack_bonus", amount=self.amount)
        return True


@dataclass(frozen=True)
class ReduceOpponentMp(Effect):
    """對手 MP 減少(不足額時歸 0)(S-020)。"""
    amount: int = 0

    def run(self, rt, ctx, path):
        reduce_mp(rt.game, rt.batch, 1 - ctx["player"], self.amount, ctx["source"])
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
    """雙方各設置一個限制旗標,依玩家 0、1 的順序(E-002 禁術 / E-008 夥伴效果失效)。"""
    flag: str = ""
    duration: str = ""

    def run(self, rt, ctx, path):
        for p in (0, 1):
            add_restriction(rt.game, rt.batch, source=ctx["source"], owner=ctx["player"],
                            target_player=p, flag=self.flag, duration=self.duration)
        return True


@dataclass(frozen=True)
class ZeroBothPlayersMp(Effect):
    """雙方 MP 歸 0;MP 本來就是 0 的一方不發事件(E-004)。"""

    def run(self, rt, ctx, path):
        for p in (0, 1):
            ps = rt.game.state.players[p]
            if ps.mp:
                rt.game.emit(rt.batch, "mp_changed", player=p, delta=-ps.mp, mp=0,
                             reason=ctx["source"])
                ps.mp = 0
        return True


@dataclass(frozen=True)
class BorrowPartner(Effect):
    """本回合借用 Choose(OpponentPartneredMamodo()) 選中的對手夥伴卡效果(E-010)。"""
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
    """[持續] 自己場上裝有夥伴的魔物魔力加值(E-023)。"""
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


# ================================================================ 數值查詢(SpellRider.damage_bonus 等)
# 這類掛鉤要「回傳數值」、不執行動作也不會停下,所以不是效果樹節點:
# 它們是不可變、可呼叫的規格物件,直接放進 SpellRider 欄位,不經過 EFFECTS / TREE_HOOKS。

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
        path = parent_path


def run_effect(game, batch, effect_id: str, ctx: dict) -> None:
    """從根節點開始解決一個效果。"""
    rt = Run(game, batch, effect_id)
    EFFECTS[effect_id].run(rt, dict(ctx), ())


def resume(game, batch, value, data: dict) -> None:
    """依 data 中的續體從停點繼續。value:Choose 為玩家選擇、Coin 為擲幣結果、Standby 無用。"""
    cont = data.get(CHOICE_KEY) or data[CONT_KEY]
    rt = Run(game, batch, cont["effect_id"])
    path = tuple(cont["path"])
    node = node_at(EFFECTS[cont["effect_id"]], path)
    node.resume(rt, dict(cont["ctx"]), value, path, cont["floor"])


@reg.choice_resolver("effect_tree_resume")
def _effect_tree_resume(game, batch, value, data):
    holder = _INFLIGHT.get(data.get(TOKEN_KEY))
    if holder is not None:      # Coin.run 尚在執行中(同步 callback):只回填結果,由 Coin.run 就地續行
        holder["results"] = value
        return
    resume(game, batch, value, data)


# ================================================================ 註冊

def validate_tree(root: Effect) -> None:
    """註冊時檢查:Choose.prompt 不可與引擎 pending kind 相同;Standby.then 不可含會停下的節點。"""
    def walk(node: Effect):
        if isinstance(node, Choose):
            if node.prompt in RESERVED_KINDS or node.prompt in reg.CHOICE_RESOLVERS:
                raise ValueError(f"Choose.prompt {node.prompt!r} 與既有 pending kind 相同")
        if isinstance(node, Standby) and node.then.may_suspend:
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
