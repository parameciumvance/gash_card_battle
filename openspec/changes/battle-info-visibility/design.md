## Context

- **擲幣詢問**:引擎的 pending 資料裡已有目前結果:
  - `coin_confirm` / `opp_coin_redo`:在 `pending.data["results"]`。
  - E-011 的 `paid_reflip`:在效果樹續體的 `ctx["results"]`。

  但快照的 pending 只送 kind / player / source / options。`choice_required` 事件雖帶 results,對非決策者會被裁掉(`views._CHOICE_PRIVATE_FIELDS`)。
- **魔力合計**:由 `engine._side_total` 與 `engine.slot_power` 計算。
  - 待命提供的術加成(M-008 / P-007)在戰鬥開始時加總進 `battle.data["attack_spell_bonus"]`,來源卡沒有留下。
  - 無效化只發 `attack_negated` / `defense_negated` 事件,戰鬥狀態沒有記來源。
  - `showdown` 事件只有雙方合計。
- **作用中效果**:待命在 `state.standby`,持續效果在 `state.modifiers`。
  - 建立時都發公開事件(`standby_set` / `modifier_added`),所以內容是公開資訊。
  - 但待命的 `data` 含效果樹續體等內部資料,不能原樣送出。
- 專案負責人確認的範圍:
  - 擲幣三種詢問都要。
  - 對戰中舞台的即時明細在不增加負擔的前提下一起做。
  - 作用中效果只放頂欄入口,戰鬥中已被消耗的待命不列。

## Goals / Non-Goals

**Goals:**

- 明細與合計出自同一段計算,不可能對不上。
- 快照只多送公開資訊,不外洩任何隱藏資訊或內部資料。
- 合計魔力的數值與改寫前完全相同。

**Non-Goals:**

- 列出戰鬥中已被消耗、但本場仍有效的待命(例如「不可防禦」已變成戰鬥狀態)。
- 在魔物卡上顯示效果標記。
- 傷害值的明細(只做魔力)。

## Decisions

### D1:合計由明細推得(單一來源)

新增兩個函式,回傳 `(total, items)`:

```text
power_breakdown(game, player, slot)   → 魔物魔力的明細;slot_power 改為取它的 total
side_breakdown(game, battle, side)    → 一方合計魔力的明細;_side_total 改為取它的 total
```

`items` 的每一項為 `{"kind", "source", "amount"}`,**各項 amount 加總恆等於 total**。原本的「不低於 0」「視為 0」「無效化」都寫成明確的調整項,數值等於被補上或扣掉的量,所以加總不變式永遠成立。

```text
kind              來源               數值
mamodo            魔物卡號           本身魔力
static            常駐效果的卡號     加減
modifier          持續效果的來源     加減(power)
partnered         持續效果的來源     加減(power_partnered,E-023)
power_zero        P-011              把魔物魔力調成 0 的調整量
mamodo_floor      —                  魔物魔力不低於 0 的調整量
spell             術卡號             術魔力(特殊為 0)
defense_self      術卡號             術自身的防禦加值(S-016 / S-017)
spell_bonus       待命的來源         術加成(M-008 / P-007)
spell_floor       —                  術魔力加減不低於 0 的調整量
fixed             魔物卡號           無術攻擊的固定魔力(M-027)
negated           無效化的來源       把合計調成 0 的調整量
```

- 防方不防禦時 `items` 為空、`total` 為 0。
- 替代方案「另寫一個只給畫面用的明細函式」:兩份計算會分歧。不採用。

### D2:記下術加成與無效化的來源

- 術魔力的加減原本有 4 個寫入點,都只累加數字:
  - 戰鬥開始 / 防禦宣告時消耗的待命(M-008 / P-007)。
  - 效果樹的 S-040(依正面數)、S-017(攻擊時自身加值)、S-016(防禦時自身加值)。
- 實作改為共用 `primitives.add_spell_power(battle, side, source, amount, kind)`,每筆 `{kind, source, amount}` 記進 `battle.data["attack_spell_power"]` / `["defense_spell_power"]`,取代原本的加總欄位 `attack_spell_bonus` / `defense_spell_bonus` / `defense_self_bonus`。合計由清單加總,明細直接取清單。
- `attack_negated` / `defense_negated` 被設為 True 的兩處(`tree.py`)同時記下來源卡:`battle.data["attack_negated_by"]` / `["defense_negated_by"]`。
- 無術攻擊記下 `battle.data["attack_fixed_source"]`(攻擊的魔物),魔物離場後明細仍有來源。

### D3:明細放進 `showdown` 事件與戰鬥快照

- `showdown` 事件新增 `attacker_breakdown` / `defender_breakdown`,事後從記錄回看、將來重播都能用;另補上 `attacker`(攻方玩家),明細檢視才能標出攻防雙方是誰。
- 快照的 `battle` 新增同名欄位,由同一函式即時算出,供舞台的合計點開。
- 明細內容全是公開資訊:場上的卡、已宣告的術、已公開的效果。

### D4:`PendingChoice.info`:公開的決策脈絡

- `PendingChoice` 新增 `info: dict`(可 JSON 序列化),放「所有人都能看的決策脈絡」;`data` 維持私有(續體等)。
- 快照的 pending 對所有視角附上 `info`。
- 擲幣三種詢問填入 `info = {"results": ["heads", "tails", ...]}`,依擲出順序。
- 替代方案「views 依 kind 從 data 挖結果」:views 必須知道每種決策內部的資料結構,E-011 的結果還藏在續體的 ctx 裡。不採用。
- `choice_required` 事件的過濾規則不變;擲幣結果本來就由 `coin_flipped` 事件公開。

### D5:作用中效果清單

- 快照新增 `effects`(待命在前、持續效果在後,各自依建立順序):
  - 待命:`{"type": "standby", "kind", "source", "owner", "expires", "created_turn", "target_slot"}`,`target_slot` 取自 data 的 `slot_uid`。
  - 持續效果:`{"type": "modifier", "kind", "source", "owner", "duration", "created_turn", "target_player", "target_slot", "amount", "flag"}`。
  - 兩者再附上 data 中白名單內的欄位(`views._PUBLIC_EFFECT_DATA`):`mamodo`、`card`、`power_delta`、`cost_delta`、`optional`,型別不符的不送。其餘 data(續體等)一律不送。
- 被消耗的待命已從 `state.standby` 移除,自然不列。
- 持續效果到期時會由回合收尾移除,所以 `state.modifiers` 裡的全部列出;「下一回合才生效」這類尚未生效的也列,以時效文字標明(例如「下一回合」)。
- 盤點結果:
  - 待命 8 種:`attack_undefendable`、`injure_instead`、`negate_damage`、`no_protect_book`、`skip_end_flip`、`spell_any_page`、`spell_bonus`、`start_phase`。
  - 持續效果 11 種:`power`、`power_partnered`、`power_zero`、`damage_delta`、`damage_double`、`spell_cost_zero`、`restriction`、`protect_discard`、`no_damage`、`full_immune`、`borrow_partner`,以及 `restriction` 的 7 種旗標。
  - 全部都是真正作用中的效果,沒有純內部記帳用的種類,不排除任何種類。

### D6:前端

- **擲幣對話框**:依 `pending.info.results` 在選項上方逐枚列出結果;重擲按鈕文字帶枚次與目前結果。非決策者在頂欄的等待提示後附上目前結果。
- **明細檢視**:獨立的純展示對話框(`#info-overlay`,標題 + 內容 + 關閉),與決策對話框分開,不會被 pending 的重繪蓋掉。
  - 行動記錄的魔力勝負條目加上「明細」可點元素,點開後讀該事件的明細。
  - 舞台上的雙方合計可點,點開後讀快照的即時明細。
  - 每項以 `breakdown.<kind>` 的 i18n 文字呈現,來源卡名沿用可點卡名。
- **作用中效果**:
  - 頂欄按鈕「作用中效果(N)」,在對局畫面顯示。
  - 清單依擁有者分組。說明取 `effect.<type>.<kind>`(restriction 依 `flag`)的 i18n 文字,帶數值與對象;效果限定某魔物、且有 `<key>.mamodo` 文字時改用該版本(例如 P-001「以賈修的術攻擊時」);沒有對應文字時退回來源卡效果文。
  - 清單開啟中時隨狀態更新。
  - 時效取 `effect.duration.<duration>` / `effect.expires.<expires>`;「至下回合結束」這類依建立回合相對於目前回合換算。
- **測試**:檢查所有程式中出現的 standby / modifier 種類都有 i18n 說明,與決策種類的檢查同樣做法;退回效果文只是保底。

## Risks / Trade-offs

- [改寫合計計算可能改到數值] → 先寫測試:以 NPC 自我對戰收集大量戰鬥,比對改寫前後每場的雙方合計完全相同,且每份明細加總等於合計。
- [戰鬥中已被消耗的待命不在清單,玩家可能以為效果沒了] → 專案負責人選擇先不列;舞台已顯示「不可防禦」等戰鬥狀態。之後需要時再擴充。
- [`showdown` 事件變大] → 每場戰鬥一筆、各十項以內,可接受。
