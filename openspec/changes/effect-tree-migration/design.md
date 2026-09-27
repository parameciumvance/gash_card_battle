## Context

效果樹架構(節點、直譯器、續體、註冊入口)已在 `effect-tree-interpreter` 定案並歸檔,規格見 `openspec/specs/effect-tree/spec.md`。目前 18 張卡已用這套架構重寫(E-001、E-005、E-006、E-022、E-026;S-004、S-014、S-021、S-025、S-026、S-027、S-035、S-037、S-040、S-041、S-045、S-046、S-057),`python -m pytest` 335 個測試全過。

剩餘 89 張卡的掛鉤分布(`tasks.md` 有逐卡清單):

| 檔案 | 卡數 | 常見掛鉤 |
|---|---|---|
| `events.py` | 22 | `event` |
| `mamodo.py` | 29 | `activated`、`static_power`、`on_play`、`start_phase`、`on_discard`、`spell_compat`、`mamodo_attack`、`trigger.*`、`damage_immunity` |
| `partners.py` | 19 | `activated`、`trigger.*` |
| `spells.py` | 19 | `rider.on_damage`、`rider.on_declare`、`rider.on_win`、`rider.counter`、`rider.damage_bonus`、`rider.injure_instead`、`rider.on_defense_damaged`、`spell_nonbattle` |

## Goals / Non-Goals

**Goals:**

- 把剩餘 89 張卡逐批遷移到效果樹,每批維持既有節奏:先確認/補齊該批卡的測試覆蓋(遷移前在舊實作上跑通),再遷移,新增節點都要有對應單元測試,全程 `python -m pytest` 保持全綠。
- 通用節點優先:能用既有節點(`Choose`/`Coin`/`Standby`/`When`/`Sequence` + 現有葉節點)組出來的卡,不開新節點;組不出來時才新增語意化的專屬節點,原則同 `effect-tree` spec 的「並非每張卡都是乾淨的樹」。
- `tasks.md` 是本次遷移的權威進度來源,每完成一批就勾選對應卡並記錄該批的 commit hash。

**Non-Goals:**

- 不要求每批遷移都各自開一個獨立 change/走完整 propose 流程——effect-tree 的架構決策已經定案,逐卡套用不再是新的架構決策,直接在本 change 底下累積 commit 即可;只有遇到需要新的架構性決定(例如要支援可停下的 `Standby.then`)時才另開 change。
- 不修正遷移過程中順帶發現的既有邏輯缺陷(見下方「已知阻礙」),除非該缺陷正好是本批要遷移的卡且使用者已決定要修。
- 不改前端 / i18n / API 格式;`choice.title.*` 依卡號命名的問題仍留到之後的 change。

## Decisions

### 1. 分批依「來源檔案 → 掛鉤複雜度」排序,不追求一次遷完

`spells.py` 的 rider 類型(`on_damage`/`on_declare`/`on_win`/`counter`/`damage_bonus`/`injure_instead`/`on_defense_damaged`)已有現成的節點與掛鉤入口,是風險最低、最快能繼續累積進度的一批。`events.py` 多數是 `Choose`/`Coin` 的組合,難度與已遷移的 E-005/E-006/E-022 相近。`mamodo.py`/`partners.py` 的 `activated`(啟動型效果:宣告使用 / 減 MP / 棄卡)、`trigger.*`(事件型觸發器)、`static_power`(常在魔力加成)是效果樹目前完全沒有掛鉤入口的類型,需要先在 `registry.py`/`tree.py` 補上對應的樹註冊入口(仿照 `register_event`/`rider_hook` 的模式),這部分建議留到 `spells.py`/`events.py` 剩餘的都遷完、對節點慣用法更熟悉之後再做,降低一次引入太多新概念的風險。

### 2. 每批沿用既有三步驟

1. **補特徵測試**:檢查該批卡是否已有行為測試;沒有的話,先在舊實作上寫測試並確認通過,再動手改。
2. **新增節點**:只新增這批卡實際會用到的節點/條件,不预先建可能用不到的通用能力(YAGNI,呼應 `effect-tree-interpreter` review 對「未使用的推測性節點」的疑慮)。
3. **遷移 + 全量測試**:改寫 `tree_cards.py` 的註冊行、刪除舊 handler、跑 `python -m pytest` 確認全綠,再勾選 `tasks.md` 對應項目並記錄 commit。

### 3. 已知阻礙,遷移到對應卡時處理

- **E-020(對手擲幣正→對手 MP+3)**——**已解決**。根源在 `flip_coins` 把擲幣者寫進 `data["player"]`,覆寫了呼叫端傳入的效果擁有者;E-020 由對手擲幣,結果 MP 給回使用者本人。使用者決定修正:`71a699c` 改為擲幣者記在 `data["flipper"]`、呼叫端的 `data["player"]` 原樣保留(其他卡都是自己擲幣,行為不變);`1a97b92` 以 `Coin(flipper="opponent")` + `GainMp(target="opponent")` 遷移。這是本 change 唯一一次刻意改變可觀察行為,經使用者同意。
- **E-011(擲幣反面可付 2MP 重擲,可重複)**——**已解決**(`ca87c12`)。新增 `CoinWithPaidReflip`,在自己的 `resume_choice` 內付費後重新擲幣,迴圈只在節點內部;確認鏈與 RNG 消耗和舊寫法相同(嚴格 RNG 測試驗證),重擲次數由 MP 自然限制,pending kind 沿用 `e011_retry` / `e011_pick`。這是技術設計問題,不需要使用者決策。

### 4. 遷移時發現的規則差異(使用者決定以效果文為準,已修正)

以下是舊寫法與日版效果文不一致之處,使用者決定一律以效果文為準:

- **E-018「直前回合」的判定範圍**(`464faf7`):直前回合用過**任何**「減少對手 MP」的效果都使 E-018 減 0。會記錄的效果:E-018、S-020、P-002、P-019(被動;規則書「此卡在場上→」效果的使用為自動進行)、E-004(效果文註記:MP 為 1 以上時視為減少 MP 的效果)。E-018 被限制成減 0 時仍算使用過。紀錄保留本回合與前一回合,避免同回合重複使用蓋掉前一回合。
- **E-027 由誰選擇**(`d4a7ad3`):由各方玩家自己選擇保留哪張夥伴、從魔本哪一頁取、有多隻可裝的魔物時裝在哪一隻;只有一個選項時不詢問。新增 `AsOpponent` 以對手視角執行子樹。

- **M-029 術相容**(`d995cc9`):只能使用賈修名為「ザケル」的術;舊寫法以「名稱包含 ザケル」判斷,連「バオウ・ザケルガ」也能用。
- **M-025 登場效果**(`4e70210`):放回羅布諾斯改為可選擇不使用、MP+2 在其後;放回哪個空頁由玩家選(效果文未明說由誰選,依「放回是玩家的動作」解讀;舊寫法自動放回編號最小的空頁,通常是已翻過的頁)。
- **M-024「二身一体」**(`29e77c0`):原本完全沒有實作;場上兩隻分身體時 ビライツ 每張每回合可用兩次。術卡使用次數改為每頁計數,新增 `spell_use_limit` 查詢掛鉤。

以上都是讓實作回到 `card-effects` 既有需求(「行為與日版效果文一致」),delta spec 補上了具體情境。

- **M-026《裏切り者》(待使用者決定)**:效果文「相手が直前に使った『魔物の効果』1つを無効にする」,且帶ジャマー圖示(規則書:在對手指定的行動結束後立即使用,用來取消 / 無效化對手前一個行動)。舊寫法是戰鬥中可隨時主動使用、移除對手最近一筆本場戰鬥的魔力 / 傷害 modifier,與效果文差距大;忠實實作需要引擎提供「對手用完魔物效果後的回應時機」與「無效化(還原)已解決效果」的機制,已向使用者提出方案。在決定前 M-026 維持舊寫法、暫不遷移。

## Risks / Trade-offs

- **[89 張卡、跨多次工作階段]** 進度容易遺失或重工 → `tasks.md` 為權威進度來源,每次工作階段開始先讀 `tasks.md` 選未勾選項目,完成後立刻勾選並記錄 commit,不依賴記憶或 commit log 反查。
- **[`activated`/`trigger.*` 尚無樹掛鉤入口]** 貿然遷移 `mamodo.py`/`partners.py` 可能需要一次補齊多種新入口,範圍不易控制 → 決策 1 已把這兩個檔案排在最後,累積足夠的節點使用經驗後再做。
- **[專屬節點膨脹]** 每張特殊卡都可能催生一個只用一次的節點 → 遷移前先檢查能否用既有節點的組合(含新增條件/葉節點)表達,新節點命名 MUST 語意化、不含卡號,且要有單元測試,維持 `effect-tree` spec 的「節點與函式名不含卡號」要求。
