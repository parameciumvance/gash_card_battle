## Context

pending 的 `kind` 同時是引擎分派 resolver 的 key、前端 `choice.title.<kind>` 的 i18n key、`rooms.py` 逾時預設的判斷依據。效果樹建立的決策以 `tree_choice` 續體分派,`kind` 不參與分派,所以改名不影響引擎邏輯;引擎內建的種類(`protect`、`coin_confirm`⋯)本來就不含卡號,不在本次範圍。pending 已帶來源卡號 `source`,快照對所有視角公開。

## Goals / Non-Goals

**Goals:**

- 效果樹的決策種類不含卡號,相同選擇共用種類;新卡沿用既有種類時不必新增 i18n。
- 對話框用通用標題,並以來源卡提供原本卡片專屬標題裡的脈絡。

**Non-Goals:**

- 不改引擎內建的決策種類。
- 不改選項的呈現方式(選項仍依 `card` / `label` / `page` 顯示)。
- 不處理多語系(只有 zh-TW)。

## Decisions

### 1. 依選擇內容命名

種類描述「選的是什麼」,以 `pick_` 開頭;只有非選取型的詢問(付費重擲)例外。對照:

| 新種類 | 取代 | 通用標題 |
|---|---|---|
| `pick_own_mamodo` | e001 / e006 / e009 / e015 / e019_pick | 選擇自己的魔物 |
| `pick_own_injured_mamodo` | e007_pick | 選擇自己的負傷魔物 |
| `pick_opponent_mamodo` | e024 / p011_pick | 選擇對手的魔物 |
| `pick_opponent_injured_mamodo` | m029_pick | 選擇對手的負傷魔物 |
| `pick_opponent_partner` | e010 / m022 / p008 / s039_pick | 選擇對手的搭檔卡 |
| `pick_partner_in_discard` | e011 / e022_pick | 選擇棄牌區的搭檔卡 |
| `pick_partner_in_own_book` | e027_fetch、m020 / m021_pick | 選擇自己魔本中的搭檔卡 |
| `pick_partner_to_keep` | e027_keep | 選擇要保留的搭檔卡(其餘棄掉) |
| `pick_mamodo_for_partner` | e027_slot | 選擇要裝備搭檔的魔物 |
| `pick_mamodo_in_own_book` | e012_pick、s043_place_complete、s048_place | 選擇自己魔本中的魔物卡 |
| `pick_opponent_book_card` | e016_pick(E-016 / E-017)、m011_pick | 選擇對手魔本中的卡 |
| `pick_card_in_own_discard` | m025_pick | 選擇自己棄牌區的卡 |
| `pick_own_empty_page` | m025_page | 選擇自己魔本的空頁 |
| `pick_own_open_page` | m016_open | 選擇自己翻開頁的卡 |
| `pick_own_earlier_page` | m016_prev | 選擇自己之前頁的卡 |
| `pick_transform_mode` | s043_choice | 選擇變換方向 |
| `paid_reflip` | e011_retry | 擲出反面 — 是否付費重擲? |

- **替代方案:依節點或選項規格類別自動產生種類。** 同一個選項規格可能用在意義不同的選擇(例如 `OwnBookCopiesOf` 只是「魔本中某張卡」),自動命名會失去可讀性,也會讓規格類別改名時連帶改變 API 值。不採用,由登記處明寫。
- **替代方案:保留每張卡的專屬標題(`choice.title.<卡號>.<種類>` 覆寫)。** 專案負責人選擇通用標題 + 顯示來源卡。

### 2. 對話框顯示來源卡

`showDialog` 增加來源卡參數;pending 有 `source` 時,在標題下方顯示來源卡名稱(`cname`)與中譯效果文(`ZH[num].effect`,只供閱讀)。沒有來源卡或查不到譯文時不顯示該區塊。引擎內建的決策(如保護)也會顯示,因為它們同樣帶 `source`。

### 3. 以測試守住命名規則

- 靜態測試:`tree_cards.py` 中所有 `prompt="…"` 不含卡號樣式。
- 靜態測試:所有效果樹決策種類與引擎內建種類都有 `choice.title.<kind>`,避免新增種類時漏掉 i18n(AGENTS.md 原本只以文字要求)。

## Risks / Trade-offs

- **[通用標題少了卡片專屬的說明(如「+3000」)]** → 對話框顯示來源卡的效果文補足脈絡;選項本身也顯示卡片。
- **[API 的 `kind` 值改變]** → 只有本 repo 的前端與 `rooms.py` 使用,一併更新;測試中的舊名稱全數改掉,以全量測試確認。
