## Context

- `PlayerState.slots` 是清單,登場時 `append`,離場時 `remove`;前端 `renderFieldBlock` 以清單索引排欄,所以離場後後面的魔物往左補。
- 新增魔物槽的地方:`engine.py`(開局、放卡、魔物消失處理)、`effects/primitives.py`(效果放出)、`effects/tree.py`(分裂等)。場上上限 `MAX_FIELD_MAMODO = 3`。

## Goals / Non-Goals

**Goals:** 魔物的欄位在引擎狀態中固定,快照帶出,盤面依欄位排列。

**Non-Goals:** 不改清單順序的語意(預設選擇、NPC 候選等仍依清單順序);不讓玩家選擇放哪一欄。

## Decisions

### D1:欄位存在引擎狀態

- `MamodoSlot` 加 `column: int | None = None`。
- 新增 `place_slot(ps, slot)`:把 `column` 設為最左邊的空欄,再加入清單。所有新增魔物槽的地方改用它。
- 不只在前端記位置:重新整理、重連、觀戰、對手的畫面都要一致,只有伺服器狀態能保證。
- 新魔物放「最左邊的空欄」,是自然的預設(原本也是往左排);效果文沒有規定位置,也不影響規則。

### D2:舊狀態與測試直接建立的魔物槽

測試或金手指可能直接 `append` 沒有欄位的魔物槽。快照輸出時,`column` 為 None 的魔物槽依清單順序補上最左邊的空欄(只在輸出時計算,不寫回)。

### D3:前端

`renderFieldBlock` 先建立 3 欄空格,再依 `slot.column` 放入(沒有 `column` 時退回清單索引)。欄位超過 3 時沿用原本的延伸方式。

## Risks / Trade-offs

- [遺漏某個新增魔物槽的地方] → 以 grep 找出所有 `slots.append`,並加測試:各種登場方式後欄位正確;快照的 D2 補位只是保底。
