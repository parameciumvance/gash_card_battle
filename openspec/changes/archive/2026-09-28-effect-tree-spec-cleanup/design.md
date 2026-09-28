## Context

`effect-tree` 是內部架構的 capability,大部分需求都有 `tests/test_effect_tree.py` 的單元測試對應,屬於可驗證的約束。其中少數敘述寫的是實作細節:資料鍵名、續體欄位格式、註冊檔排版。這些內容改程式時容易忘記同步 spec,已經出現脫節(續體多了 `floor`)。專案層級的 `openspec/design.md` 第 2.2 節已記錄續體與分派鍵的現況。

## Goals / Non-Goals

**Goals:**

- spec 只保留可觀察的行為與可測試的約束;鍵名、欄位格式、排版等實作細節改由 `openspec/design.md` 或程式內說明承載。
- 改寫後每條需求的約束強度不變:原本 MUST 的行為仍是 MUST。

**Non-Goals:**

- 不改程式、測試與任何可觀察行為。
- 不調整 `effect-tree` 其餘需求(包括「Standby.then 限定同步完成」,它是設計上的約束,保留在 spec)。

## Decisions

### 1. 判斷標準:能否用行為或測試驗證

留在 spec 的是「換一種實作仍必須成立」的性質,例如續體經 JSON 往返後可恢復、擲幣確認由 M-012 / M-019 的流程處理、副作用恰好執行一次。移出的是「換一種實作就會變」的細節,例如 pending 資料裡用哪個鍵名、續體有哪些欄位、容器節點如何縮排。

- **替代方案:整個 `effect-tree` capability 移到 design。** 會失去與單元測試對應的可驗證約束,歸檔流程也無法用 delta 追蹤這些約束的變動。不採用。

### 2. 移出的內容放哪裡

- 分派鍵 `tree_choice` / `tree_cont` 與續體格式 `(effect_id, path, ctx, floor)`:`openspec/design.md` 第 2.2 節(已記錄)。
- 註冊檔排版:`src/gash/engine/effects/tree_cards.py` 開頭的說明(已記錄),`openspec/design.md` 第 2 節的檔案表已指向該處。

## Risks / Trade-offs

- **[spec 變得較抽象,新人不易從 spec 找到鍵名]** → design.md 第 2.2 節列出鍵名與分派方式,spec 的 Purpose 或相關需求不需重複。
- **[排版規則不再受 spec 約束]** → 排版屬寫作慣例,由 `tree_cards.py` 開頭說明與 code review 維持;依卡號排序、每卡集中、邏輯不寫在註冊檔這三項仍是 spec 約束。
