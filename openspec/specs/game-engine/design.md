# game-engine — 設計

## 架構

- 純 Python、無 IO:`engine.submit(game, command)` 收指令、回傳事件列表。前端、API、測試都只透過指令與事件互動。
- 狀態(`engine/state.py`)維持純資料:不存閉包或函式,將來的 history / 重播才可行。
- 卡片效果經 `engine/effects/registry.py` 的掛鉤表接入:引擎在規則的各個時點查表呼叫,效果本身由 `card-effects` / `effect-tree` 持有。
- `engine/awaiting.py` 提供對狀態的純查詢:`awaited_player`(目前等誰輸入)與 `default_command`(安全預設指令)。規則不依賴它們;房間層的計時器、逾時代打與 NPC 共用(見 `online-room/design.md`)。

## 中途決策(pending)

- 等待玩家決策時建立 `PendingChoice`,期間只接受該玩家的 `choose` 指令。
- resolver 驗證失敗(拋出 `IllegalCommand`)時保留 pending 讓玩家重選,所以 resolver 必須先驗證、再改狀態。
- 引擎內建的決策種類保留給引擎使用,卡片效果不可重用(`tree.RESERVED_KINDS` 與 `reg.CHOICE_RESOLVERS` 的 key):`protect`、`damage_order`、`deploy_page`、`injure_instead_target`、`coin_confirm`、`opp_coin_redo`、`jammer_negate`、`spell_discount`。
- 由效果樹建立的決策如何分派回樹,見 `effect-tree/design.md`。
- **選項的位置**:目標為卡片的選項一律用 `primitives.slot_option` / `page_option` / `discard_option` 建立,帶 `zone`(`slot` / `book` / `discard`)、`player` 與定位欄位(`slot` uid / `page` / `index`),前端據此在畫面上的位置選擇。`value` 是指令值,與位置欄位無關;`extra` 附加欄位不可覆寫位置欄位。受傷順序(`damage_order`)的魔物項另外標上同樣的位置欄位,魔書項維持按鈕。新增選項來源時要用這些函式,`tests/test_choice_locations.py` 以 NPC 自我對戰掃描所有卡片選項都帶正確位置。
- `PendingChoice.data` 是私有的(續體、傷害佇列等內部資料),不送出;`PendingChoice.info` 是公開的決策脈絡,快照對所有視角附上。目前擲幣相關的詢問(M-012 `coin_confirm`、M-019 `opp_coin_redo`、E-011 `paid_reflip`)在 `info.results` 放目前各枚的結果(`primitives.coin_info`)。

## 戰鬥開始與待命表

- `_start_battle` 在戰鬥開始確認通過時呼叫:先依攻擊來源準備(`_prepare_spell_attack` / `_prepare_mamodo_attack`:再驗證、付費、記錄頁與 P-015 任意頁待命),得到 `AttackStart`(BattleState 初始參數、`battle.data`、`battle_started` 欄位、`is_spell`、使用魔物家族 `mamodo_name`、是否選擇 M-008 減費);之後共用建立戰鬥、啟用「下一場戰鬥」待命、發出 `battle_started`、消耗待命、戰術的宣告時效果。
- 戰鬥開始時消耗的待命由 `BATTLE_START_STANDBYS` 表驅動,依表的順序消耗,每個發 `standby_resolved`:

| 待命 | 適用條件 | 套用 |
|---|---|---|
| `spell_bonus`(M-008、P-007) | 戰術;`mamodo` 為 None 或等於使用魔物家族;可選者須選擇使用 | 攻擊戰術魔力加值 |
| `attack_undefendable`(S-019、S-026、P-001) | `mamodo` 為 None;或戰術且等於使用魔物家族 | 攻擊不可被防禦 |
| `no_protect_book`(E-013) | 都適用 | 本場不能保護魔書 |
| `injure_instead`(S-057) | 戰術 | 獲勝改為負傷對手魔物 |

- 效果文寫「術」的待命只適用於戰術攻擊;無戰術攻擊(M-027)不消耗它們,留到下一場戰鬥。
- **新增作用於下一場戰鬥的待命**:在表加一列,寫明對戰術攻擊與無戰術攻擊是否適用;`tests/test_battle_start_characterization.py` 以期望檔鎖定兩種攻擊在各待命下的事件序列,刻意改變行為時以 `GOLDEN_UPDATE=1` 重新產生並說明。

## 魔力勝負明細

- 合計魔力由逐項明細推得,只有一份計算:`power_breakdown`(魔物魔力)與 `side_breakdown`(一方合計)回傳 `(total, items)`,`slot_power` / `_side_total` 只取 total。所以明細與合計不可能對不上。
- 每一項為 `{"kind", "source", "amount"}`,各項 amount 加總恆等於 total。「視為 0」(P-011)、「不低於 0」、「無效化」都寫成明確的調整項,數值為被補上或扣掉的量:

```text
mamodo / static / modifier / partnered / power_zero / mamodo_floor   ← 魔物魔力
spell / defense_self / spell_bonus / spell_floor                      ← 戰術魔力
fixed                                                                  ← 無戰術攻擊(M-027)
negated                                                                ← 無效化(合計歸 0)
```

- 戰鬥中戰術魔力的加減一律經 `primitives.add_spell_power` 記進 `battle.data["<side>_spell_power"]`(每筆含來源卡);無效化的來源記在 `battle.data["<side>_negated_by"]`;無戰術攻擊的魔物記在 `attack_fixed_source`。新增會改變戰術魔力的效果時,也要經這個函式,明細才會有來源。
- `showdown` 事件附 `attacker`、`attacker_breakdown`、`defender_breakdown`;快照的 `battle` 附同樣的即時明細。
- `showdown` 事件另附對峙的卡:`attack_mamodo` / `defense_mamodo`(魔物槽最上面的卡)、`attack_spell` / `defense_spell`;不防禦時防禦兩欄為 None,無戰術攻擊時 `attack_spell` 為 None。前端的對峙演出只靠事件本身,不依賴快照時序。
- `protected` 事件附 `target`(`book` / `slot`)與 `target_slot`(被保護的魔物槽),供保護演出知道保護者要移到哪裡。

## 場上魔物的欄位

- `MamodoSlot.column`(0–2,由左至右)只表示位置,不影響任何規則;`slots` 清單順序的既有語意(預設選擇、NPC 候選等)不變。
- 魔物登場一律經 `state.place_slot(slots, slot)`,放到最左邊的空欄;疊放、負傷、恢復、搭檔都不改欄位;離場後那一欄留空。新增登場路徑時要用它。
- 測試或金手指直接建立、沒有欄位的魔物槽,`slot_columns` 依清單順序補最左空欄(只在快照輸出時計算,不寫回)。
- 位置記在伺服器而不只在前端:重新整理、重連、對手與觀戰的畫面都要一致。
