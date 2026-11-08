"""MJ12 卡(MJ-xxx)的效果登記:獨立卡區的卡(game-engine「獨立卡區與 MJ12」)。依卡號排序,排版規則見 `cards/__init__.py`。

MJ12 的效果都沒有戰鬥圖示:非戰鬥中、不限自己的回合(雙方的戰鬥階段)。
「このカードを捨て札にする→」為 mode="discard"(引擎先把此卡從獨立卡區棄掉);效果不是魔物 / 搭檔的效果。
"""

from .. import registry as reg
from ..tree import (
    AttachPartnerFromBookPage, BoundPageIsPartner, Choose, DamageOpponentBook, DeployMamodoFromBook, HasOptions,
    MamodoOrPartnerPagesInOwnBook, PeekOpponentOpenPages, SidePowerThisTurn, SlotsForBookPartner, When,
)

# 「この効果は1ターンに1回しか使えない」:每個效果本來就每回合 1 次;以卡號記錄,同回合再放出另一張也不能再用
reg.activated("MJ-001", mode="discard", timing="nonbattle", effect=DamageOpponentBook(amount=1))
reg.activated("MJ-002", mode="discard", timing="nonbattle", effect=SidePowerThisTurn(side="defense", amount=4000))
reg.activated("MJ-003", mode="discard", timing="nonbattle",
              condition=HasOptions(MamodoOrPartnerPagesInOwnBook()), effect=Choose(
    MamodoOrPartnerPagesInOwnBook(), bind="page", prompt="pick_card_in_own_book",
    then=When(
        BoundPageIsPartner(),
        then=Choose(
            SlotsForBookPartner(), bind="slot", prompt="pick_mamodo_for_partner",
            then=AttachPartnerFromBookPage(),
        ),
        otherwise=DeployMamodoFromBook(),
    ),
))
reg.activated("MJ-004", mode="mp", mp_cost=1, timing="nonbattle", effect=PeekOpponentOpenPages())
reg.activated("MJ-005", mode="discard", timing="nonbattle", effect=SidePowerThisTurn(side="attack", amount=2000))
# 「このカードが場にある→」強制效果;掛在「被對手的效果減少 MP」(primitives.mp_counter_after_reduction)
reg.mp_counter("MJ-006")
