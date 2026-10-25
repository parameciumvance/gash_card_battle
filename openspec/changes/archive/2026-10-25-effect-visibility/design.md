# Design

## Context

- 聚焦時間軸在 `frontend/anim.js` 的 `timeline()`:`CARD_EVENTS`(放出、使用、發動、宣告…)開卡片格,`TEXT_EVENTS` 併成結果行;行動者是自己時只留 `unfavorable()` 的事件。
- 常駐效果與待命 / ステイ造成的事件大多已帶來源卡:`pages_turned.source`、`mp_changed.reason`(效果時為卡號,支付費用時為 `spell:…` 等)、`card_discarded.reason`、`mamodo_healed.source`、`damage_negated.card`、`mp_reduction_prevented.source`、`mp_gain_prevented.source`。`damage_prevented` 沒有來源。
- 魔力明細:`power_breakdown(game, player, slot)` 已存在(對決明細用)。費用:`spell_cost` → `_spell_cost_by` → `_base_spell_cost_by` + `_spell_bonus_standbys`;`event_cost` 為卡面 + M-040,都只回傳數字。
- 卡面數值由 `cardEl` 的 `cmeta` 以字串串接(`opts.power` / `opts.cost`);放大檢視 `renderZoom` 只有卡與行動按鈕。

## Goals / Non-Goals

**Goals:**
- 生效時不新增引擎事件型別,以既有事件的來源欄位判斷「效果來源卡」;只有「一次性時點被擋下」新增 `effect_blocked`(原本沒有任何事件)。
- 數值明細由引擎算出一次,快照提供,前端只顯示。

**Non-Goals:**
- 觸發型常駐效果(P-013 / P-019 / P-030 / M-028)被擋下時不發事件:它們對每個同類事件都會被呼叫,要判斷「沒被擋下會不會有結果」須逐張處理;改由失效標示呈現。
- 出場時的效果(M-006 / M-007 / M-025)已由「放出」卡片格顯示,不另外處理。
- 對決中的合計魔力已有戰力明細,不重做。

## Decisions

- **來源卡取法(前端 `effectSource(ev)`)**:依事件型別取 `source`(`pages_turned`、`mamodo_healed`、`damage_prevented`、`mp_reduction_prevented`、`mp_gain_prevented`)、`card`(`damage_negated`)、`reason`(`mp_changed`、`card_discarded`,只在符合卡號格式時)。取不到時照舊。
- **另起卡片格的條件**:來源卡存在且不等於目前卡片格的卡(`cur.card`)時,另起 `{kind: "card", card: source}` 格,這一格不經 `others` / `unfavorable` 過濾。替代方案是引擎在觸發前發出 `effect_triggered` 事件——要在每個觸發點判斷「會不會產生結果」,事件也會比結果早出現在記錄;既有事件已帶來源,不採用。
- **`damage_prevented.source`**:免疫(`DAMAGE_IMMUNITY`)為 `slot.top`;`no_damage` 持續效果為該 modifier 的 `source`;`_full_immune` 改回傳生效的 modifier 以取得來源;S-079 的保護(`_guard_immune`)同樣回傳來源。`no_target` 不帶。
- **費用明細**:`_spell_cost_by` 改為內部建 `items`(`card` 卡面、`last_page`、`base_zero`、`cost_bonus`、`cost_floor`),新增 `spell_cost_breakdown(...) -> (cost, items)`,`spell_cost` 取其數字,行為不變。`event_cost_breakdown`:`card` + 每隻未受限 M-040 的 `opponent_event`。`base_zero` 依序取最後一個使本來費用為 0 的來源(最後一頁 / S-088 / P-005 的 `spell_cost_zero`),以一項調整寫出。
- **快照欄位**:`_slot_view` 加 `power_breakdown`(所有視角);`_player_view` 在加 `cost` 的同一處加 `cost_breakdown`。`any_page_spells` 也有 `cost`,一併加。
- **分色**:`cardEl` 的 `cmeta` 改為逐段建立,魔力與費用各包一個 `span`,依 `opts.power` 與卡面 `power.base`、`opts.cost` 與卡面 `cost` 比較加 `class="val-good"` / `"val-bad"`(費用低為 good)。盤面卡片的 `cmeta` 是隱藏的(只留卡名),所以帶有目前數值的卡(`opts.power` / `opts.cost`:場上魔物、翻開頁)一律以絕對定位的數值徽章(`val-badge`)顯示,相同時為中性深色(使用者要求一致顯示,不只在有增減時出現)。魔力徽章(`val-power`)在左下、卡名下方;費用徽章(`val-cost`)只寫數值,依卡圖寬(`--card-w` - 16px)的比例定位在原圖費用格(465 寬中 x 380–432、y 30–78)上並蓋住它,手機尺寸也對齊。盤面卡片加 `isolation: isolate`,卡內徽章的 z-index 不會浮到行動區上(疊放張數標記原本也有這個問題);放大檢視則看 `cmeta` 本身的顏色。顏色沿用既有 token(`--accent-green` / `--danger` 一類,卡面為淺底,用較深的同色系)。
- **放大檢視明細**:`renderZoom` 在 ctx 為 `slot` / `page` / `any_page` 且數值與卡面不同時,於按鈕下方加明細區,沿用 `infoRow` 與 `breakdown.*` i18n;費用的項目同樣用 `breakdown.<kind>` 鍵(既有測試要求每種明細項目都有翻譯;待命的費用加減叫 `cost_bonus`,與魔力的 `spell_bonus` 區分)。來源卡名可點開檢視(沿用 `infoRow` 的卡片連結)。
- **記錄**:`log.damage_prevented` 有 `source` 時改用新鍵 `log.damage_prevented_by`。
- **限制來源 `effect_block_sources(game, player, slot, number) -> list[str]`**(`engine.py`,與 `card_effect_blocked` 並列):搭檔看 `NO_PARTNER_EFFECTS` 限制的 `source`;魔物看 `mamodo_effect_block` 所依據的限制(`NO_MAMODO_EFFECTS` / `NO_EFFECTS_AND_SPELLS` / 這隻的 `MAMODO_LOCKED` / 非選定的 `ONLY_MAMODO`)的 `source`,以及 P-031 家族禁止的搭檔卡號;依 modifier 順序、去重。`card_effect_blocked` 改為 `bool(effect_block_sources(...))`,兩者不會分歧。
- **哪些卡會列在 `blocked_effects`**:`reg.PASSIVE_TABLES`(新增,集中列出)= `START_PHASE`、`STATIC_POWER`、`ON_DISCARD`、`TRIGGERS` 的卡、`SPELL_COMPAT`、`SPELL_USE_LIMIT`、`DAMAGE_IMMUNITY`、`OPPONENT_EVENT_COST`、`REVEAL_OPPONENT_PAGES`、`PARTNER_DISCARD_GUARD`、`BATTLE_PHASE_MP_LOCK`、`BLOCK_OPPONENT_FAMILY`;`ON_PLAY` 與 `IGNORE_SPELL_BLOCK`(M-038)不列。`_slot_view` 對頂層與搭檔各查一次。
- **`effect_blocked` 事件**:在 `run_on_play`(`when: play`)、兩個 `ON_DISCARD` 呼叫點(`discard`)、開始階段迴圈(`start_phase`)檢查到被擋時發出;傷害免疫在 `immunity(...)` 為真但被擋時發出(`damage`)。為了判斷「會不會免疫」,免疫查詢改為先算 `immunity(...)` 再看是否被擋。記錄:`log.effect_blocked`;聚焦以 `card` 為來源卡(`effectSource`)。
- **失效標記**:`cardEl` 的 `opts.badges` 沿用既有的徽章機制加「失效」;放大檢視明細區下方列「失效中的效果」(以卡名寫出:「{卡名} 的效果被 {來源} 擋下」)。

## Risks / Trade-offs

- [來源卡格太多造成干擾(例如每回合 M-002)] → 只在事件確實改變了東西時才會有事件;演出設定可調快或關閉。
- [`reason` 欄位不全是卡號] → 只接受卡號格式(`/^[EMPS]-\d{3}$/`,與 `mpByEffect` 相同)。
- [對手看得到的事件才會被聚焦] → 只用該視角收到的事件(既有 `filter_event`),不額外揭露。
