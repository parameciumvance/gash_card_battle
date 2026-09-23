# effect-tree-interpreter 提案 Review

- 日期：2026-09-23
- 審查基準：工作目錄中的提案文件，以及 commit `fb40e24` 的現有實作。
- 範圍：`proposal.md`、`design.md`、`tasks.md`、`specs/effect-tree/spec.md`，並對照引擎、效果註冊、API view 與測試。
- 結論：**建議修訂後再開始實作。** 效果樹與逐卡遷移的方向可行，但目前有 1 項 P1 分派錯誤，以及 5 項 P2 契約或驗收缺口。

以下意見針對提案，不表示效果樹已實作或已在現行遊戲中造成缺陷。P1 為依提案實作就會破壞本次遷移流程的問題；P2 為需補明的設計、相容性或測試要求。

## R1 · P1：以 `cont` 存在與否分派，會跳過擲幣確認 resolver

**提案位置：** [design.md:62–64](design.md#L62-L64)、[tasks.md:12](tasks.md#L12)、[tasks.md:18](tasks.md#L18)。

提案要求 `Choose` 的指令處理在 `pending.data` 含有 `cont` 時直接呼叫 `resume`；同時又要求 `Coin` 把 `data={"cont": …}` 傳給既有 `flip_coins`。這兩個設計會衝突：

1. `flip_coins` 保留傳入的 `data`，再加入 `results`、`callback` 等欄位。
2. 確認鏈將這份資料存入 `opp_coin_redo` 或 `coin_confirm` 的 pending。
3. 玩家回覆時，新的分派條件會直接呼叫效果樹 `resume`，跳過原有 M-019／M-012 resolver。

因此玩家的 `None`（保留）、整數（重擲第幾枚）或 `True`（令整組重擲）會被誤當成樹停點的回覆；真正的重擲、能力使用標記、M-019 → M-012 串接都不會依原流程執行。

**程式依據：** [primitives.py:218–254](../../../src/gash/engine/effects/primitives.py#L218-L254) 保留並傳遞資料；[primitives.py:257–306](../../../src/gash/engine/effects/primitives.py#L257-L306) 才負責確認與重擲；現有分派位於 [engine.py:1116–1127](../../../src/gash/engine/engine.py#L1116-L1127)。

已以現有 `flip_coins` 傳入假續體驗證，得到：

| 場上效果 | 建立的 pending | `data` 含 `cont` | 玩家可回覆值 |
|---|---|---|---|
| 自己 M-012 | `coin_confirm` | 是 | `None`、`0` |
| 對手 M-019 | `opp_coin_redo` | 是 | `None`、`True` |

**建議修正：** 明確區分「由樹的 `Choose` 建立的 pending」與「內部帶有樹 callback 的既有 pending」。只有前者直接呼叫 `resume`；後者仍依 `pending.kind` 呼叫原 resolver，等確認鏈完成後才透過 `effect_tree_resume` 回到樹。可使用獨立分派標記或隔離 callback payload，不能只檢查 `cont`。

**驗收：** 透過 `submit(..., type="choose")` 測試 M-019 → M-012 整條鏈；確認每一步的決策者、pending kind、能力消耗、重擲事件及最終效果。不可只直接呼叫 `resume` 做單元測試。

## R2 · P2：續體尚未定義如何接回外層 `Sequence`

**提案位置：** [design.md:46–56](design.md#L46-L56)、[design.md:72](design.md#L72)、[tasks.md:3–5](tasks.md#L3-L5)。

目前只定義以 `path` 找回停點並執行後續子節點，沒有說明子樹完成後如何返回祖先、執行尚未完成的同層節點。例如：

```text
Sequence(
    A,
    Choose(..., then=B),
    C,
)
```

`Choose` 進入 pending 後，原本的 Python 呼叫堆疊已結束。若 `resume` 只是找回 `Choose` 並執行 `B`，便會漏掉 `C`。這不代表三欄位續體無法實現，而是提案缺少利用 `path` 重建執行位置的規則。

另需處理同步 callback：沒有 M-012／M-019 時，`flip_coins` 會立即呼叫 callback（[primitives.py:254](../../../src/gash/engine/effects/primitives.py#L254)）。若 callback 的 `resume` 接著執行剩餘 siblings，原本尚在執行的 `Sequence` 又繼續迴圈，就可能重複執行後續效果。

**建議修正：** 補上控制流程契約，包含節點子索引順序、`path` 指向停點或下一步、祖先 `Sequence` 如何續行，以及同步 callback 與非同步恢復如何保證每個效果僅執行一次。也需決定 `Standby` 排程完成後，外層 `Sequence` 是立即續行還是等待觸發，避免把兩種生命週期混在一起。

**驗收：** 新增巢狀 `Sequence`、連續兩次 `Choose`，以及 `Sequence(A, Coin(...), B)` 在有／無確認 pending 下的測試；確認沒有漏做或重做副作用。續體應經 `json.dumps` → `json.loads` 後仍能恢復，而不只驗證能輸出 JSON。

## R3 · P2：註冊介面缺少本次遷移必需的掛鉤契約

**提案位置：** [design.md:80–85](design.md#L80-L85)、[tasks.md:6](tasks.md#L6)、[tasks.md:21](tasks.md#L21)。

設計與任務 1.4 具體列出的樹入口只有 `event` 與 `spell_rider(..., on_damage=...)`，但任務 3.4 還要求移除 S-021／S-025 的宣告 handler，以及 S-026 的非戰鬥 handler：

| 卡片 | 現有入口 | 樹轉接需保留的資訊 |
|---|---|---|
| S-004、S-014 | `on_damage(game, batch, player)` | 效果擁有者與來源 |
| S-021、S-025 | `on_declare(game, batch, player, side)` | 四參數簽名及防禦方條件 |
| S-026 | `SPELL_NONBATTLE[number](game, batch, player)` | 獨立註冊表及非戰鬥使用入口 |

S-021／S-025 的現有 handler 明確檢查 `side == "defense"`（[spells.py:105–125](../../../src/gash/engine/effects/spells.py#L105-L125)），引擎也實際傳入第四個參數（[engine.py:687–688](../../../src/gash/engine/engine.py#L687-L688)）。S-026 則必須出現在 `SPELL_NONBATTLE`，否則使用時會得到 `spell.not_implemented`（[engine.py:434–443](../../../src/gash/engine/engine.py#L434-L443)）。

**建議修正：** 在設計與任務 1.4 明列 `on_declare` 的包裝簽名、`side` 如何進入 `ctx`、防禦條件如何表達，以及 `reg.spell_nonbattle(number, effect=…)` 入口。一起定義這些掛鉤的 `effect_id` 與重複註冊檢查，讓任務 3.4 有完整的前置支援。

**驗收：** 以實際引擎入口驗證三種掛鉤，不只直接呼叫 `run`；確認 S-026 仍走非戰鬥術的費用、時機與使用次數檢查。

## R4 · P2：E-001 延遲目標消失時的既有行為尚未保留

**提案位置：** [design.md:76](design.md#L76)、[tasks.md:13–14](tasks.md#L13-L14)、[specs/effect-tree/spec.md:43–45](specs/effect-tree/spec.md#L43-L45)。

提案將 `AddPower` 描述為包裝 `add_power`，並刪除 `e001_fire`。但原本的 `e001_fire` 會在待命觸發時，以玩家與 slot UID 重新查找目標；若目標已離場，直接結束，不建立 modifier，也不發出加魔力事件（[events.py:44–51](../../../src/gash/engine/effects/events.py#L44-L51)）。

`add_power` 本身沒有這個檢查，會直接加入 modifier 並發出 `modifier_added`（[primitives.py:15–30](../../../src/gash/engine/effects/primitives.py#L15-L30)）。如果只照提案包裝 primitive，便會對已不存在的 slot 留下效果與事件，違反可觀察行為不變的要求。

**建議修正：** 明定 `Choose` 綁定的是穩定 slot UID，並明確指定 `AddPower` 的目標參照（例如 `Ref("slot")`）或預設讀取規則。延遲效果執行時重新檢查目標；UID 不存在時無效果且不發事件。不可改選另一隻魔物。

**驗收：** E-001 選定後目標離場、目標仍在，以及兩筆待命分別指定不同 UID 的情境。現有 [test_e001_next_turn_power](../../../tests/test_cards.py#L473-L485) 只覆蓋單一魔物存活到下回合。

## R5 · P2：`Standby.then` 能否再次建立 pending 必須界定

**提案位置：** [design.md:62](design.md#L62)、[design.md:74](design.md#L74)、[specs/effect-tree/spec.md:40–45](specs/effect-tree/spec.md#L40-L45)。

設計將 `Standby.then` 描述為可繼續解決的效果子樹，並宣稱開始階段引擎不需修改。然而現有開始階段會直接遍歷、移除並觸發所有到期待命，不檢查 callback 是否建立 pending，之後也直接切換到戰鬥階段（[engine.py:254–260](../../../src/gash/engine/engine.py#L254-L260)）。

若同時有兩筆 `Standby(..., then=Choose(...))` 到期，第二次觸發會覆寫第一次的 pending，第一筆續體便遺失。`then=Coin(...)` 遇到重擲確認也有相同組合風險。

**適用範圍：** 此問題不影響本次 E-001 的 `then=AddPower` 路徑，但影響提案目前未設限制的通用節點組合契約。

**建議修正：** 本次可明文限定待命子樹只能同步完成，並在註冊時拒絕可能再次停下的子樹；若要支援任意 `then`，就必須把開始階段剩餘待命與階段切換納入可恢復流程，不能宣稱引擎完全不需修改。

**驗收：** 若支援，測試兩筆同時到期且需選擇的待命，確認依序解決、pending 不被覆寫；若不支援，測試非法組合於註冊時被明確拒絕。

## R6 · P2：既有測試不足以支持提案宣稱的確認鏈與遷移等價性

**提案位置：** [design.md:100](design.md#L100)、[tasks.md:14](tasks.md#L14)、[tasks.md:18](tasks.md#L18)、[specs/effect-tree/spec.md:62–64](specs/effect-tree/spec.md#L62-L64)。

提案稱可用既有 M-012／M-019 測試回歸，且任務 2.4 將 E-001 多魔物選擇列為既有測試。實際盤點如下：

- `tests/` 沒有 M-019／`opp_coin_redo` 的專門案例。
- M-012 既有測試覆蓋 S-025 重擲與 S-021 保留結果（[test_cards.py:251–262](../../../tests/test_cards.py#L251-L262)、[796–808](../../../tests/test_cards.py#L796-L808)）。
- E-001 現有案例只走單魔物自動指定；任務 2.1 雖有新增 Choose 單元測試，仍需明列透過引擎的多目標選擇與重試整合驗收。
- S-004／S-014、S-026 的現有測試只覆蓋無重擲確認的正面結果（[test_cards.py:706–726](../../../tests/test_cards.py#L706-L726)、[811–820](../../../tests/test_cards.py#L811-L820)）。

另外，現有腳本 RNG 在序列用完後固定回傳反面（[test_cards.py:12–19](../../../tests/test_cards.py#L12-L19)），不一定能抓到額外 RNG 消耗；`test_seed_reproducibility` 比較的是同一實作跑兩次的結果（[test_engine.py:403–408](../../../tests/test_engine.py#L403-L408)），也不等同遷移前後的事件序列比較。

**建議修正：** 將缺少的情境列為新增任務，並在遷移前固定相關指令序列的預期事件與公開 pending 快照。至少涵蓋 M-019 保留／重擲、M-019 → M-012 串接、兩枚硬幣的結果分支，以及三種擲幣入口（傷害後、宣告時、非戰鬥）的恢復。以會在超額呼叫時失敗的 RNG 或呼叫計數驗證消耗次數。

同時澄清 spec 中「resume 不得重新擲幣」的意思：效果樹恢復不得重跑初始擲幣；玩家合法要求的 M-012／M-019 重擲仍須消耗 RNG。

## 已執行的檢查

| 檢查 | 結果 | 能證明的範圍 |
|---|---|---|
| `openspec validate effect-tree-interpreter --strict` | 通過 | 文件結構符合 OpenSpec 格式 |
| `python -m pytest --collect-only -q` | 248 個測試 | 提案記載的既有測試數量正確 |
| `python -m pytest -q` | 248 passed，11.62 秒 | 現有實作的回歸基準通過 |
| 以既有 `flip_coins` 傳入假 `cont` | 兩種確認 pending 都保留 `cont` | R1 的資料傳遞衝突確實存在 |

本次只新增 review 文件。上述測試結果不代表尚未實作的效果樹已通過驗證。

## 建議修訂順序

1. 先修 R1 的 pending 分派，並在設計中補明 R2 的完整續行規則。
2. 補齊 R3 的註冊入口與 R4 的延遲目標行為，讓本次六張卡有完整遷移契約。
3. 對 R5 選定本次支援範圍，將 R6 與各項驗收納入 `tasks.md`，再開始實作。
