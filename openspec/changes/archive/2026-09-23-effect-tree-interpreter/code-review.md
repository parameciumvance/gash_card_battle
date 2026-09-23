# effect-tree-interpreter Code Review

- 審查版本：`7d6bedf`，相對於實作前的 `07cd466`。
- 範圍：效果樹直譯器、註冊層、引擎分派、六張遷移卡片，以及新增測試。
- 結果：**發現 1 項 P2 註冊問題。** 六張已遷移卡片未發現可重現的行為回歸；前次提案 review 的主要問題已處理。

## CR1 · P2：再次註冊不同 rider 掛鉤會靜默清除既有樹效果

**位置：** [registry.py:153–160](../../../src/gash/engine/effects/registry.py#L153-L160)，核心問題為第 160 行整筆替換 `SpellRider`。

新的註冊檢查以 `(卡號, 掛鉤)` 判定衝突，但只檢查此次 `kwargs` 有傳入、且值非 `None` 的掛鉤。迴圈結束後卻用 `SpellRider(**kwargs)` 替換整張卡的記錄，因此對同一卡片註冊另一個掛鉤或旗標時，未傳入的既有掛鉤與旗標會被重設。

以下程式可在獨立 Python process 重現，不需改動卡片資料：

```python
from gash.engine.effects import registry as reg, tree

reg.spell_rider("T-REVIEW", on_damage=tree.Nothing(), counter=True)
reg.spell_rider("T-REVIEW", on_declare=tree.Nothing())

rider = reg.SPELL_RIDERS["T-REVIEW"]
assert rider.on_declare is not None
assert rider.on_damage is None                  # 第一個效果被清掉
assert rider.counter is False                  # 既有旗標也被重設
assert ("T-REVIEW", "rider.on_damage") in tree.TREE_HOOKS

# 嘗試補回已消失的效果，反而被殘留的註冊標記拒絕：
reg.spell_rider("T-REVIEW", on_damage=tree.Nothing())
# ValueError: T-REVIEW 的 rider.on_damage 掛鉤已被註冊
```

同樣地，在現有 S-004 註冊完成後呼叫 `reg.spell_rider("S-004", counter=True)`，不會得到衝突錯誤，卻會直接移除它的 `on_damage` 效果。這使新的樹掛鉤防覆寫檢查可以被另一個掛鉤或單純旗標註冊繞過，且 `TREE_HOOKS`／`EFFECTS` 與引擎實際使用的 `SPELL_RIDERS` 不再一致。

**影響範圍：** 本次六張卡均以單次呼叫註冊，尚未觸發此問題。問題發生於同一卡片分次註冊不同掛鉤，或新舊註冊對同一卡片分別設定效果／旗標時。舊版原本就採整筆替換，但此次新增的掛鉤層級衝突檢查沒有攔住這條移除樹效果的路徑。

**建議修正：** 明確選定並實作其中一種行為：

- 若允許不同掛鉤分次註冊，只更新本次明確指定的欄位，保留其他掛鉤與旗標；同掛鉤重複註冊仍拒絕。
- 若要求每張卡只註冊一次，在任何會覆蓋已註冊樹效果的再次呼叫發生前直接拒絕，且不得留下部分寫入的 `TREE_HOOKS`／`EFFECTS`。

**建議測試：** 先註冊 `on_damage`，再註冊 `on_declare`；先註冊樹掛鉤，再以舊式呼叫設定旗標。確認兩次呼叫要麼安全保留既有資料，要麼明確拒絕且註冊表完全不變。

## 前次提案 Review 的核對結果

| 前次項目 | 本次核對 |
|---|---|
| R1：`cont` 分派跳過重擲 resolver | 已以 `tree_choice`／`tree_cont` 分離；確認 pending 仍交給既有 resolver |
| R2：`Sequence` 停點恢復與同步 callback | 已實作 `_ascend` 與 `_INFLIGHT`；巢狀與同步／非同步路徑未發現重做或漏做 |
| R3：缺少掛鉤入口 | 已補 event、on_damage、on_declare、spell_nonbattle；另有上述 CR1 註冊表一致性問題 |
| R4：E-001 延遲目標消失 | `AddPower` 會重新依 UID 查找，目標不存在時不建立 modifier、不發事件 |
| R5：待命子樹再次停下 | 註冊時拒絕會暫停的 `Standby.then`，符合修訂後範圍 |
| R6：特徵測試不足 | 新增 23 個特徵案例，並已驗證在遷移前與遷移後皆通過 |

## 驗證結果與限制

- `python -m pytest -q`：**302 passed**，11.06 秒。
- `openspec validate effect-tree-interpreter --strict`：通過。
- 將新增的 23 個特徵案例套用於 `07cd466` 舊實作：全數通過。
- 對上述 23 個場景的 **157 次 `submit` 指令**做遷移前後差異比對：完整事件、錯誤、RNG 呼叫次數，以及玩家 0、玩家 1、`all`、觀戰者四種視角的指令前後 API snapshot 均一致。
- 額外產生 1,000 棵深度 4 的效果樹，組合 `Sequence`／`Choose`／`Coin`／`When`，分別走同步擲幣與 M-012 確認模式；共 2,000 次執行的順序符合獨立參考遍歷。
- CR1 已以獨立 Python process 重現；這些額外檢查不會修改正式註冊檔或應用程式碼。

以上結果支持本次六張卡的遷移相容性，但不能涵蓋尚未實作的節點與所有未來組合。本次僅新增本 review 文件，未修正實作。
