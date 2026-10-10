"""卡片效果樹登記:依卡片類別分檔(events / mamodo / partners / spells),每檔依卡號排序,
每卡的登記集中一處(多個掛鉤各一個 reg.xxx(...) 且相鄰),效果邏輯在 tree.py 的節點。

排版規則(讓巢狀層次一眼看得出來):
- 第一行固定是 `reg.xxx("卡號", ...,`,方便依卡號掃描。
- 有子節點的容器節點(Choose / Coin / CoinWithPaidReflip / When / Standby / Sequence /
  AsOpponent,以及 opponent_then_self(...))一律換行,子節點縮排一層;
  該容器的收尾括號獨立一行,與開頭對齊。
- 沒有子節點的葉節點、條件、選項規格寫在同一行。
- 整張卡只有一個葉節點(或只有旗標 / 查詢規格)時,整個註冊寫成一行;參數太長時續行對齊。

只有旗標、沒有邏輯的戰術卡(如 counter / damage_cap / injure_instead)也一併登記在 spells.py,讓登記集中。
"""

# 匯入順序即登記順序:events → mamodo → partners → spells,與卡號順序一致
# (reg.START_PHASE 等登記表依此順序迭代)。
from . import events, mamodo, partners, spells  # noqa: F401
