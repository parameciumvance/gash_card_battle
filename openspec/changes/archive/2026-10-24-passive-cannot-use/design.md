# Design

## Context

常駐效果分散在多張登記表,各有自己的消費端:

| 登記表 | 卡 | 消費端 |
| --- | --- | --- |
| `START_PHASE` | M-002 | `engine` 開始階段迴圈 |
| `STATIC_POWER` | M-003 / M-004 / M-014 | `power_breakdown` |
| `ON_PLAY` | M-006 / M-007 / M-025(與 M-047 的規則) | `engine` 3 處、`primitives` 2 處、`tree` 2 處、開局 1 處 |
| `ON_DISCARD` | M-009 | `engine` 入墓 2 處 |
| `TRIGGERS` | M-028 / P-013 / P-019 / P-030 | `GameState._dispatch_triggers` |
| `SPELL_COMPAT` | M-023 / M-036(與 M-029 的規則) | `_spell_usable_by` |
| `SPELL_USE_LIMIT` | M-024 | `spell_use_limit` |
| `DAMAGE_IMMUNITY` | M-031 / M-051 / M-053 / M-047 | 傷害結算 |
| `OPPONENT_EVENT_COST` | M-040 | `event_cost` |
| `REVEAL_OPPONENT_PAGES` | P-024 | `reveals_open_pages` |

全部都沒有檢查「使えない」;第 4 批的 M-047 免疫(`ImmuneWhileEffective`)、M-049(`partner_discard_guarded`)、P-020(`battle_phase_mp_lock`)、P-031(`_opponent_family_blocks`)是各自在查詢時檢查。

## Goals / Non-Goals

**Goals:**
- 一個共用判斷,所有常駐效果的消費端都用它;專用規則走另外的登記,不經這個判斷。

**Non-Goals:**
- 不發出「效果被擋下」的事件或記錄(屬於下一個 change 的醒目顯示)。
- M-006 已產生的禁術限制不因之後受限或離場而解除。
- 前端與 NPC 不改:魔力、費用、公開頁、戰術使用者都由引擎查詢得出。

## Decisions

- **共用判斷 `card_effect_blocked(game, player, slot, number) -> bool`**(`engine.py`,與 `mamodo_effect_block` 放在一起):`number` 是 `slot.partner` 時看 `restricted(game, player, NO_PARTNER_EFFECTS)`,否則看 `mamodo_effect_block(game, player, slot) is not None`(含 E-024 / E-043 的個別限制與 P-031 家族)。不在 registry 包裝函式,因為 `STATIC_POWER` 的 fn 收的是被加成的魔物,判斷要看來源魔物,只有消費端知道。
- **專用規則用獨立的登記與表**:在 `registry.py`「純資料登記(不是效果)」一節新增 `rule_on_play(number, effect)`(`RULE_ON_PLAY`)與 `rule_spell_compat(number, check)`(`RULE_SPELL_COMPAT`)。M-047 的 `ScheduleDetachSelf`、M-029 的 `CanUseSpellNamed`(現有節點)改用它們。替代方案是在原本的函式加 `rule=True` 旗標——同一張表混兩種東西,新增卡時容易漏,不採用。
- **`ON_PLAY` 的呼叫點收斂成 `run_on_play(game, batch, player, slot, number)`**(`primitives.py`):先執行 `RULE_ON_PLAY`,再於未受限時執行 `ON_PLAY`。8 個呼叫點都改呼叫它,之後新增放出路徑不會漏檢查。
- **`_dispatch_triggers` 在呼叫 handler 前檢查**,以該卡在 slot 上的位置(頂層或搭檔)決定看哪種限制。目前 `TRIGGERS` 全是常駐效果;日後若有規則型觸發,比照新增規則表。
- **M-024**:`spell_use_limit` 的「場上有此卡」改為「場上有此卡且其效果未受限」;節點本身仍數場上的張數(含受限的那隻)。
- **M-047 免疫**:改用共用判斷後,`ImmuneWhileEffective` 換成 `AlwaysImmune`,行為不變。M-049 / P-020 / P-031 的既有檢查保留(它們不在上表的消費端內)。
- **持續型查詢不快取**:每次查詢都重算,限制解除即恢復,不需要事件。

## Risks / Trade-offs

- [遺漏某個 `ON_PLAY` / `ON_DISCARD` 呼叫點] → 以 `grep "reg.ON_PLAY\["` 確認只剩 `run_on_play` 內一處;`ON_DISCARD` 同樣收斂。
- [既有測試假設常駐效果無條件生效,且剛好在受限情境下] → 跑快速層找出;若是測試情境本身就違反規則,依 AGENTS.md 列出差異告知使用者,不默默改測試期望。
