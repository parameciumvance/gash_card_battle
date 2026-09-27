# 最近兩筆提交 Review

- 日期：2026-09-27
- 審查範圍：`7d6bedf..5c3c656`，工作目錄於審查開始時乾淨。
- `b2a7733`：修正 rider 重複註冊、同步主規格並歸檔。
- `5c3c656`：遷移 S-027／035／037／040／041／045／046／057 至效果樹。
- 結果：**未發現新增的遊戲行為回歸；有 2 項 P3 低優先級問題。** 其中註冊原子性的問題是此次修正仍未涵蓋的既有邊界情況，不是第二批卡片遷移造成的問題。

## R1 · P3：建構 `SpellRider` 失敗仍會留下部分註冊狀態

**位置：** [registry.py:163–165](../../src/gash/engine/effects/registry.py#L163-L165)。

`b2a7733` 已將樹合法性與掛鉤衝突檢查移到寫入之前，但 `SpellRider(**kwargs)` 仍在 `tree.rider_hook(...)` 寫入 `TREE_HOOKS`／`EFFECTS` 之後才執行。因此，註冊參數拼錯時，建構子雖然拒絕註冊，樹的標記卻已留下。

可在獨立 Python process 重現：

```python
from gash.engine.effects import registry as reg, tree

try:
    reg.spell_rider("T-REVIEW", on_damage=tree.Nothing(), countr=True)
except TypeError:
    pass

assert "T-REVIEW" not in reg.SPELL_RIDERS
assert ("T-REVIEW", "rider.on_damage") in tree.TREE_HOOKS
assert "T-REVIEW:rider.on_damage" in tree.EFFECTS

# 修正拼字後仍被前次殘留標記擋住：
reg.spell_rider("T-REVIEW", on_damage=tree.Nothing(), counter=True)
# ValueError: T-REVIEW 的 rider.on_damage 掛鉤已被註冊
```

這與新加入的 [註冊原子性要求](../specs/effect-tree/spec.md#L160-L169) 不符，也會令同一行程內修正參數後的重試失敗。

**影響與歸因：** 此執行順序在 `7d6bedf` 就存在；目前正式卡片註冊沒有傳錯參數，不影響正常對局。本項是原子性修正未完整涵蓋的錯誤處理路徑。

**建議：** 在任何註冊表寫入前，先驗證完整 `kwargs` 能建構 `SpellRider`；再安裝樹與最終 handler。補一個「未知 keyword 被拒絕，三個註冊表不變，修正後可重試」的測試。

## R2 · P3：歸檔後的 review 原始碼連結失效

**位置：** [歸檔 code-review.md:9](../changes/archive/2026-09-23-effect-tree-interpreter/code-review.md#L9)，以及同目錄 `review.md` 中的原始碼與測試連結。

`b2a7733` 將文件移至 `openspec/changes/archive/2026-09-23-effect-tree-interpreter/`，但原本的 `../../../src/...`、`../../../tests/...` 沒有隨目錄深度調整。現在這些連結會指向不存在的 `openspec/src/...`、`openspec/tests/...`，無法從審查意見開啟證據。

已檢查相對路徑：`review.md` 有 17 個失效目標，`code-review.md` 有 1 個，共 18 個。

**建議：** 改為 `../../../../src/...`、`../../../../tests/...`。若需要保留當時行號的歷史意義，可改用固定 commit 的原始碼連結。本問題由歸檔路徑改變造成，不影響引擎執行。

## 已確認的修正與相容性

- 前次 CR1 已修正：同一卡片再次呼叫 `spell_rider`，不論是不同掛鉤、同掛鉤或只設定旗標，都會在寫入前被拒絕，既有效果與旗標保留。
- 不合法效果樹放在 `on_declare` 或 `on_damage` 時，註冊表不變，修正後可正常重試。
- `openspec/specs/effect-tree/spec.md` 的 requirement 內容與歸檔 delta spec 一致，沒有略過主規格同步。
- 第二批八張卡的條件、作用對象、時效與原 callback 一致；S-040 零正面仍保留 `amount=0` 事件，S-045／046 仍直接作用於當前戰鬥，S-057 仍建立待命。

## 驗證

| 檢查 | 結果 |
|---|---|
| `python -m pytest -q` | **320 passed**，11.09 秒 |
| `openspec validate --all --strict` | **11 passed，0 failed** |
| `git diff HEAD~2 HEAD --check` | 通過 |
| 第二批卡片遷移前後差異比對 | **2,688 個場景、5,376 個比較點一致** |

差異比對以 `7d6bedf` 為舊版，涵蓋八張卡、雙方效果擁有者、所有初始硬幣組合、M-012／M-019 有無、保留／各枚重擲，以及戰鬥存在／不存在。初始效果透過 registry 掛鉤呼叫，確認選擇透過 `submit`；比較完整事件、RNG 呼叫次數與遊戲狀態，僅排除刻意改變的 pending 內部續體欄位。這是掛鉤層級的差異比對，不代表窮舉所有完整對局。

本次只新增這份 review 文件，未修改實作或原有測試。
