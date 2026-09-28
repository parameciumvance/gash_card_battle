## Context

`openspec/design.md` 是在指南成形前建立的單一專案設計檔,混合了引擎、效果樹、卡片規則機制與效果文解讀。指南改為每個 capability 各自持有 `design.md`,並規定行為解讀的格式與確認狀態(§7)、跨 capability 知識的歸屬(§8)、覆蓋程度的判斷(§10.1)。解讀的確認狀態已由專案負責人核可(見決策 3)。

## Goals / Non-Goals

**Goals:**

- 現有文件符合指南:capability map、各 capability design、解讀格式與確認狀態、行為結果寫在 spec。
- 依專案負責人決定拿掉 P-018 的第一頁限制,先寫依效果文的測試並確認修正前失敗。

**Non-Goals:**

- 不替其他 8 個 capability 補寫 design(沒有現成內容可搬,依指南 §10 漸進補充)。
- 不逐項核對各 capability 的覆蓋程度;capability map 的覆蓋評估標明為初評。
- 不調整 `effect-tree` 是否獨立為 capability(專案負責人決定先保留)。

## Decisions

### 1. `openspec/design.md` 各節的去處

| 原內容 | 去處 | 理由 |
|---|---|---|
| 1. 引擎 | `game-engine/design.md` | 指令、狀態、pending 屬於引擎 |
| 2. 效果樹、5. 已知限制中與效果樹有關的部分 | `effect-tree/design.md` | |
| 3. 規則機制的共通決定 | `card-effects/design.md` | 雖然部分實作在 `engine.py`,但這些是卡片效果規則的實現方式,由 card-effects 持有 |
| 4. 效果文解讀紀錄 | 行為結果 → `card-effects` spec;理由與確認狀態 → `card-effects/design.md`「行為決定與理由」 | 指南 §6、§7.2 |
| 開頭說明、spec 與 design 的分界 | 刪除 | 已由指南涵蓋 |

「房間狀態只在記憶體,所以續體不會遇到樹版本不一致」是效果樹的限制,放在 `effect-tree/design.md`,引用 `online-room` 的現況,不為此新建 `online-room/design.md`。

### 2. P-018 的使用條件

拿掉 `pos > 2` 的條件後,在第一頁使用 P-018:回翻 0 張(不發 `pages_turned`,不觸發對手 P-019),但 P-018 本身仍算一次「もどす」效果(已確認的解讀:限制卡本身算 1 次),之後同回合的回翻效果不發生。

目前「回翻 0 張不算用過」(`Inferred`)只影響 `page_back_effect_used`,限制旗標 `page_back_effect_limited` 仍會設定。P-018 / P-010 的使用條件改為檢查「用過 **或** 已受限制」,直接表達「合計1回」。目前這個差異觀察不到:同一卡號的效果本來就每回合只能用一次(`ability.used`),而會回翻自己魔本的另一張卡 E-005 使用時不檢查這個條件、只是結果不發生;條件寫成這樣,是為了讓旗標的意義不依賴「回翻張數是否大於 0」。

- **替代方案:在第一頁使用時把 `page_back_effect_used` 設為真。** 會讓 P-018 與 E-005 對「回翻 0 張算不算用過」的處理不一致,等於改變一個 `Inferred` 的解讀,需要另外確認。不採用。

### 3. 確認狀態的對應(專案負責人已核可)

- 效果文明寫、或專案負責人以「照效果文」回應的讀法 → `Confirmed`:E-027 由誰選、P-013 依張數、「次のバトル」只作用於下一場、P-010 / P-018 的合計1回計入 E-005、M-008 在宣告術時決定、P-018 第一頁可用。
- 專案負責人在多種讀法中選定 → `Project Decision`:「〇〇の術」以使用術的魔物判定、M-026 完整還原、S-026 / S-057 不詢問。
- Agent 的解讀、告知後未另外表示 → `Inferred`:E-027 裝在哪一隻、無術攻擊算「次のバトル」、M-008 的細節、M-026 還原範圍的細節、E-018 減 0 仍算用過、M-025 由玩家選空頁、回翻 0 張不算用過。

### 4. Purpose 的修改方式

OpenSpec 的 delta 只處理需求,不處理 `## Purpose`。三個 spec 的 Purpose 在本 change 中直接修改主 spec,並列入 tasks 追蹤。

### 5. 覆蓋程度為初評

依指南 §10.1 判斷,但本 change 沒有逐項比對程式與測試。capability map 標明評估依據,之後的 change 碰到該 capability 時再修正。

## Risks / Trade-offs

- **[覆蓋程度初評可能偏差]** → capability map 註明為初評;依指南 §13.3,之後的 change 發現落差時更新。
- **[P-018 在第一頁使用只會棄掉卡片]** → 符合效果文,且與 P-010 在最後一頁可用的處理一致;棄掉的卡記入本回合入墓,E-022 可以取回。
