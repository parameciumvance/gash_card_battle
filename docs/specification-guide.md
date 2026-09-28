# 規格指南

## 1. 目的

本文件定義此專案中規格與設計知識的組織方式、維護原則與操作流程。

目標如下：

- 提供目前系統行為的明確事實來源。
- 提供目前系統設計的明確描述。
- 保存理解目前行為仍有價值的解讀與理由。
- 支援既有 brownfield 系統逐步建立規格。
- 保存個別變更的理由、設計與歷史。
- 讓工程師與 AI Agent 都能理解並導航規格。
- 在可行範圍內，使規格制度不綁定特定 SDD 工具。

目前使用 OpenSpec 支援變更流程，但本文件定義的是專案的規格制度，而非 OpenSpec 本身的使用說明。

---

## 2. 核心概念

本專案區分下列不同類型的知識：

- **目前行為（Current Behavior）**：系統目前保證什麼。
- **目前設計（Current Design）**：系統目前如何設計。
- **目前理由（Current Rationale）**：為什麼目前採用某個仍有效的行為解讀或設計決定。
- **變更意圖與設計（Change Intent / Design）**：某次變更要修改什麼，以及預計如何修改。
- **歷史（History）**：過去為什麼以及如何進行某次變更。

這些資訊不得混為一談。

| Artifact | 用途 |
|---|---|
| `capability-map.md` | 導航系統及其 capabilities |
| `spec.md` | 描述目前可觀察且具規範性的行為 |
| capability `design.md` | 描述目前設計與目前仍有效的理由 |
| change `proposal.md` | 描述某次變更的原因與範圍 |
| change `design.md` | 描述某次變更預計如何實作 |
| `tasks.md` | 追蹤變更的實作與文件工作 |
| archived change | 保存歷史變更脈絡與決策 |

概念上：

```text
spec.md
    = 現行 WHAT

design.md
    = 現行 HOW
    + 目前仍有效的 WHY

capability-map.md
    = 系統地圖與跨 capability 導航

archived changes
    = 歷史 WHY / CHANGE HOW
```

---

## 3. 目錄結構

預期的 OpenSpec 結構如下：

```text
openspec/
├── capability-map.md
├── config.yaml
│
├── specs/
│   ├── <capability-a>/
│   │   ├── spec.md
│   │   └── design.md
│   │
│   └── <capability-b>/
│       ├── spec.md
│       └── design.md
│
└── changes/
    ├── <change>/
    │   ├── proposal.md
    │   ├── design.md
    │   ├── tasks.md
    │   └── specs/
    │
    └── archive/
```

並非每個 capability 都必須具有 `design.md`。

當記錄既有架構、實作決策、行為解讀或理由能實質提升理解與維護能力時，SHOULD 建立 `design.md`。

---

## 4. Capability

Capability 代表系統中一個具有一致責任的行為或功能領域。

Capability SHOULD 依穩定的系統責任劃分，而不是直接依個別程式檔案、class 或 function 劃分。

例如：

```text
app2-command
app2-communication
app2-control
```

當同一 repository 包含多個應用程式時，MAY 使用應用程式名稱作為 capability prefix：

```text
app1-command
app1-network

app2-command
app2-network
```

共用能力 SHOULD 使用適當的共用 namespace，而不是任意歸屬於其中一個應用程式。

---

## 5. Capability Map

`openspec/capability-map.md` 是理解目前規格集合的主要導航入口。

它回答：

> 系統有哪些主要 capability、各自負責什麼、彼此如何關聯，以及應該從哪裡開始閱讀？

Capability Map SHOULD 包含：

- 簡短的系統概觀。
- 已知應用程式或主要子系統。
- 已知 capabilities 及其責任。
- capability 間的重要關係。
- 重要的跨 capability flow 或 dependency。
- 必要時提供建議閱讀入口或順序。
- brownfield 區域目前的規格與設計覆蓋程度。

例如：

```markdown
## App2

App2 負責接收 Host 指令並控制目標裝置。

| Capability | 責任 | Spec 覆蓋 | Design 覆蓋 |
|---|---|---|---|
| app2-communication | Host / Device 通訊 | Partial | Partial |
| app2-command | 指令解析與分派 | Partial | Documented |
| app2-control | 裝置控制行為 | Not documented | Not documented |
```

Capability Map 是**導航與系統層級概觀文件**。

不得在其中重複 capability specification 的詳細 normative requirements。

跨 capability 的關係 SHOULD 在此提供高層次描述，但詳細行為與設計知識 SHOULD 由適當的 capability 持有。

Capability Map 中未列出的能力，不得因此被認定為不存在。

---

## 6. Current Specification

Capability 的：

```text
openspec/specs/<capability>/spec.md
```

描述該 capability **目前預期的可觀察行為**。

它回答：

> 系統目前保證什麼？

Specification SHOULD 著重於具有行為意義的 requirement，而不是不必要的實作細節。

例如：

- input / output
- 可觀察行為
- state-dependent behavior
- protocol behavior
- failure behavior
- compatibility requirements
- 重要 constraint 與 invariant
- 會影響可觀察結果的行為解讀

如果某個解讀會產生可觀察的系統行為，則在該領域已納入規格管理時，其**行為結果 MUST 寫入 spec**。

例如：

> 某個效果在特定遊戲狀態下不能使用。

這個限制本身屬於 specification。

至於：

> 為什麼這個效果被解讀為在該狀態下不能使用？

則屬於 rationale，可記錄於 `design.md`。

可以在不改變行為契約的情況下自由變更的實作細節，SHOULD NOT 寫入 specification。

---

## 7. Current Design 與 Rationale

Capability 可選擇具有：

```text
openspec/specs/<capability>/design.md
```

它描述該 capability **目前已成立的設計，以及理解目前狀態仍有價值的理由**。

它回答兩類問題：

> 這個 capability 現在是怎麼設計的？

以及必要時：

> 為什麼目前的行為或設計被理解成這樣？

### 7.1 Current Design

典型內容包括：

- architecture
- component responsibility
- 重要 data flow
- state ownership
- concurrency model
- persistence model
- protocol structure
- 重要 internal interface
- established implementation pattern
- 重要 technical constraint

Capability design 描述的是**現在的狀態**，而不是系統如何演變成現在的狀態。

### 7.2 行為決定與理由

`design.md` MAY 包含：

```markdown
## 行為決定與理由
```

用來記錄目前仍有效、且有助於理解 specification 的行為解讀與理由。

可以記錄：

- 為什麼模糊規則或效果採用目前的解讀。
- 解讀使用了哪些證據。
- 解讀是否經過明確確認。
- 解讀來自原始資料、既有實作、領域解讀或專案決定。
- 理解目前行為所需的重要假設。

**行為結果本身 MUST 寫入 `spec.md`。**

`design.md` 中的 rationale 負責解釋為什麼目前如此規定。

Rationale SHOULD 在可能的情況下，以 OpenSpec 中既有的 requirement 名稱、scenario 名稱或其他穩定名稱引用對應 specification。

不要求為既有 requirements 額外建立人工編號。

### 7.3 Rationale 確認狀態與決定權

本專案的行為解讀與專案規則，最終決定權屬於**專案負責人**。

§7.2「行為決定與理由」中的**每一項行為決定 MUST 標註確認狀態**。

純粹的設計理由，例如架構選擇、資料結構選擇或實作方式的理由，不需要使用此確認狀態。

行為決定僅能使用下列四種狀態：

| 狀態 | 意義 |
|---|---|
| `Confirmed` | 某個解讀已由專案負責人確認為效果文、規則或其他原始規範本身的正確意思 |
| `Project Decision` | 原始規範存在多種合理解讀，或不足以唯一決定行為，由專案負責人明確選定本專案採用的行為 |
| `Inferred` | 工程師或 Agent 根據現有證據所做的目前解讀，尚未經專案負責人確認 |
| `Pending Confirmation` | 已發現解讀問題或候選方案，目前仍等待專案負責人確認或決定 |

其中：

**`Confirmed` 與 `Project Decision` 的差別不在於「是否有人確認」，而在於規則本身是否具有唯一的正確解讀。**

如果專案負責人確認：

> 「這就是效果文原本的意思。」

則為：

```text
Confirmed
```

如果專案負責人決定：

> 「效果文可以有多種合理解讀，本專案採用這一種。」

則為：

```text
Project Decision
```

Agent 或工程師不得自行將自己的解讀標記為 `Confirmed` 或 `Project Decision`。

若尚未取得專案負責人的確認，應使用 `Inferred` 或 `Pending Confirmation`。

不得自行建立意義相近但名稱不同的狀態。

### 7.3.1 Pending Confirmation 與 Current Specification

`Pending Confirmation` 表示**行為解讀尚待確認**，不表示 current specification 應保持空白。

在等待確認期間，`spec.md` MUST 照常描述系統**目前實際採用或實作的行為**。

例如：

```text
目前實作行為
      │
      ├── spec.md：照常記錄目前行為
      │
      └── design.md：
            行為決定與理由
            確認狀態：Pending Confirmation
```

確認後：

- 若確認結果與目前行為一致，更新 rationale 的確認狀態即可；
- 若確認結果要求改變目前行為，則應建立或使用適當的 change 修改 specification 與 implementation，而不是直接把尚未實作的新行為當成 current specification。

因此：

```text
spec.md
    = 現在系統做什麼

確認狀態
    = 我們對「為什麼應該這樣做」有多確定
```

兩者是不同維度。

### 7.4 Rationale 建議格式

建議使用以下格式：

```markdown
### 某效果在特定狀態下的使用限制

**相關規格：**
`card-effects` › 需求「某效果的使用條件」 › 情境「特定狀態下不能使用」

**決定：**
該效果在此狀態下不能使用。

**理由：**
依目前效果文與相關規則的解讀，此狀態不符合效果的使用條件。

**依據：**
- 效果文字
- 相關遊戲規則

**確認狀態：** `Inferred`
```

此處使用明顯泛化的例子，避免指南中的示例被誤認為正式遊戲規格。

如果之後由專案負責人確認該解讀確實是效果文的正確意思：

```text
Inferred
    ↓
Confirmed
```

如果效果文仍存在多種合理解讀，而專案負責人決定採用其中一種：

```text
Inferred
    ↓
Project Decision
```

如果原本的解讀被推翻：

- 更新 `spec.md` 的目前行為；
- 更新 `design.md` 的目前 rationale；
- 舊解讀及變更原因保留在 archived change。

Capability `design.md` 不應累積已失效的 rationale。

---

## 8. 跨 Capability Ownership

一個行為或設計可能同時涉及多個 capability。

每項詳細知識 SHOULD 有一個主要 owning capability。

原則是：

> 由最直接負責該行為或設計決策的 capability 持有。

其他受影響 capability SHOULD 引用 owning capability，而不是複製相同的 normative requirement 或 rationale。

例如：

```text
game-engine

    owns:
    「只有目前回合玩家能攻擊」

              ↑ dependency

card-effects

    「下一場戰鬥」相關效果依賴
    game-engine 的攻擊資格規則
```

`card-effects` 的 specification 或 design 可以引用 `game-engine` 的 requirement，而不是重新定義一次攻擊資格。

跨 capability design：

- 詳細設計 SHOULD 由主要 capability 持有。
- 其他 capability SHOULD 在需要時建立 reference。
- `capability-map.md` SHOULD 描述重要的系統層級關係與 flow。

如果某個決策確實是 system-wide，無法合理指定單一 capability：

1. 在 `capability-map.md` 提供高層次說明；
2. 詳細內容放入適當的 shared capability 或獨立 system-level documentation。

SHOULD 避免在多個 capability 重複 normative requirement。

---

## 9. Change-Level Design

某次 change 的：

```text
openspec/changes/<change>/design.md
```

與 capability `design.md` 的目的不同。

它回答：

> 這一次變更預計怎麼做？

因此可以包含：

- migration strategy
- temporary compatibility mechanism
- implementation sequence
- alternatives considered
- rejected approaches
- transition architecture
- change-specific risks

變更完成後，change design 成為歷史的一部分。

不得直接把 change design 視為目前 capability design。

---

## 10. Brownfield 規格政策

本 repository 包含尚未被完整文件化的既有軟體。

因此採用**漸進式規格化**。

沒有 specification 不代表：

- capability 不存在；
- 行為不存在；
- 既有行為是偶然的；
- 未記錄行為可以安全移除。

不要求在開始開發前完整 reverse-spec 整個 repository。

當某個區域與目前 change 相關時，SHOULD 補充或改善其 specification 與 design knowledge。

### 10.1 覆蓋程度

每個 capability specification SHOULD 在其 `## Purpose` 中描述該 specification 的 scope。

Coverage 狀態是相對於此 scope 判斷，而不是相對於整個系統或 capability 所有可能存在的行為判斷。

使用以下三種狀態。

#### `Documented`

在 `## Purpose` 所宣告的 scope 中，目前**已知**的行為已有相應 requirements / scenarios，且在合理可測試的情況下具有對應 verification 或 tests。

`Documented` 不表示未知行為不可能存在，也不表示該 capability 未來不會發現新的行為。

#### `Partial`

在 `## Purpose` 所宣告的 scope 中，只記錄了一部分已知行為，或仍缺少重要 scenario、requirement 或 verification coverage。

#### `Not documented`

該領域尚未建立具有實質內容的 current specification。

Design coverage MAY 使用相同狀態，但判斷對象改為目前已知 architecture、design decisions 與 rationale。

Coverage 僅提供導航資訊，不得被解讀為絕對完整性證明。

---

## 11. Required Reading Procedure

在提出或實作 change 前，工程師與 Agent SHOULD：

1. 閱讀本指南。
2. 閱讀 `openspec/capability-map.md`。
3. 找出可能受到影響的 capabilities。
4. 閱讀其現有 `spec.md`。
5. 在相關時閱讀 capability `design.md`。
6. 檢查相關既有程式碼。
7. 檢查相關既有 tests。
8. 找出 change 可能影響的既有行為與設計。
9. 找出跨 capability dependencies。
10. 必要時釐清重要的模糊或未文件化行為。

對 brownfield code，不得假設未文件化的行為無效或可以安全修改。

本指南其他章節提到 **Required Reading Procedure** 時，均指本節，不再另外定義另一套閱讀流程。

---

## 12. Change Workflow

正常開發流程：

```text
Required Reading
        ↓
Propose
        ↓
Specify / Clarify
        ↓
Design
        ↓
Plan Tasks
        ↓
Implement
        ↓
Verify
        ↓
Reconcile Current Documentation
        ↓
Archive
```

並非每個 change 都需要每個 artifact 有大量內容。

Specification 與 design 工作量 SHOULD 與 change 的範圍及風險相稱。

如果 change 可能影響 current spec、current design、rationale 或 capability map，`tasks.md` SHOULD 明確列出相應的 reconciliation 工作。

---

## 13. Archive 前的 Current-State Reconciliation

完成的 change 在 archive 前 MUST 與 current-state documentation 完成 reconciliation。

### 13.1 Current Specification

行為變更 MUST 反映至受影響 capability 的 `spec.md`。

OpenSpec 對 specification 提供 delta-spec synchronization。

同步完成後的 specification 必須描述**目前行為**，而不是變更歷史。

### 13.2 Current Design 與 Rationale

OpenSpec 標準的 delta-spec synchronization **不會自動 reconciliation capability-level `design.md`**。

因此 current design 與 rationale 的 reconciliation 是本專案明確要求的額外流程。

Archive 前 MUST：

1. 檢查 change-level `design.md`。
2. 檢查實際 implementation。
3. 找出受影響的 capability-level `design.md`。
4. 若 established design 或目前仍有效的 rationale 發生改變，更新它們。
5. 確認 capability design 描述的是變更完成後的目前狀態。

當 change 可能影響 current design 或 rationale 時，`tasks.md` SHOULD 明確包含此 reconciliation task。

例如：

```markdown
- [ ] Reconcile affected capability design and rationale
```

Capability `design.md` SHOULD 在以下項目發生持續性改變時更新：

- architecture
- component responsibility
- data flow
- state ownership
- concurrency model
- persistence model
- protocol structure
- important internal interface
- established implementation pattern
- behavioral interpretation
- current rationale
- 其他 persistent design decision

不得直接把 change design 全文複製至 capability design。

下列 transition-only information 不應進入 current design：

- migration steps
- temporary compatibility mechanisms
- rejected alternatives
- implementation sequencing
- obsolete architecture
- temporary workarounds

這些資訊保留於 archived change。

### 13.3 Capability Map

Change 發生以下情況時 SHOULD 更新 `openspec/capability-map.md`：

- 新增 capability；
- 移除 capability；
- capability responsibility 發生實質改變；
- capability relationship 發生實質改變；
- 已知 specification/design coverage 改變。

適用時，`tasks.md` SHOULD 明確包含：

```markdown
- [ ] Update capability map
```

---

## 14. Archive 的語意

Archived OpenSpec changes 是**歷史紀錄**。

主要回答：

> 當時為什麼進行這項變更？

> 當時考慮過哪些方案？

> 變更過程如何規劃？

> 當時有哪些限制？

如果已有 applicable current specification 或 current design，archive 不應作為理解目前系統的主要來源。

```text
Current spec.md
    = 現行 WHAT

Current design.md
    = 現行 HOW
    + 目前仍有效的 WHY

Archived changes
    = 歷史 WHY
    + CHANGE HOW
```

---

## 15. 文件導航

理解目前系統時，建議閱讀：

```text
capability-map.md
        ↓
affected capability
        ↓
spec.md
        ↓
design.md（相關時）
        ↓
code / tests
```

只有需要了解歷史理由或演進時，才通常需要進一步閱讀 archived changes。

開始 change 時應遵循 §11 的完整 **Required Reading Procedure**。

---

## 16. Agent 與 OpenSpec 整合

AI Agent 在此 repository 工作時 MUST 遵循本指南。

Repository-level `AGENTS.md` SHOULD 指向本文件，而不是複製完整規則。

例如：

```text
進行 specification-driven development 前，
請先閱讀：

docs/specification-guide.md
```

`openspec/config.yaml` 的 project context 也 SHOULD 指向本指南，使 OpenSpec 產生 artifact 時知道此 repository 有額外的 specification policy。

例如：

```yaml
context: |
  本專案的規格制度與 brownfield 開發規則定義於：
  docs/specification-guide.md

  進行 OpenSpec change 時必須遵循該指南。
```

Tool-specific configuration SHOULD 儘量引用本指南，而不是複製完整政策。

本 repository specification workflow 的 authoritative definition 是**本文件**，而不是 `AGENTS.md` 或 OpenSpec configuration。

---

## 17. Source of Truth

### Current Behavior

```text
openspec/specs/<capability>/spec.md
```

在該行為已有文件化時，是 normative specification。

### Current Design / Rationale

```text
openspec/specs/<capability>/design.md
```

在已有文件化時，是目前 established design 與仍有效 rationale 的維護位置。

### System Navigation

```text
openspec/capability-map.md
```

是已知 capability 與重要關係的導航地圖。

它不能取代 capability specification。

### Change History

```text
openspec/changes/archive/
```

保存歷史 intent、alternatives、transition design 與 change-specific decisions。

由於本專案採 brownfield 漸進式規格化，當相關 behavior/design 尚未完整文件化時，既有 code 與 tests 仍 MUST 被檢查。

---

## 18. 文件語言與術語

以下 current-state 文件原則上使用**繁體中文**：

- `capability-map.md`
- capability `spec.md`
- capability `design.md`

本指南亦使用繁體中文。

技術術語 MAY 保留英文，特別是在翻譯可能造成歧義時。

以下內容 SHOULD 保留 canonical form，不任意翻譯：

- code identifiers
- protocol identifiers
- card / effect identifiers
- requirement 名稱
- scenario 名稱
- API names
- class / function names
- stable domain identifiers

同一概念在不同 capability 中 SHOULD 使用一致術語。

必要時 MAY 建立專案 glossary。

術語一致性與語意明確性優先於強制將所有內容翻譯成中文。

---

## 19. 本框架的演進

此 specification framework MAY 隨專案實際使用經驗調整。

OpenSpec 是目前使用的 workflow tool，但本指南中的核心原則應儘可能與特定工具解耦。

修改本指南時 SHOULD 保持以下概念清楚分離：

- current behavior；
- current design；
- currently relevant rationale；
- proposed change；
- historical record。