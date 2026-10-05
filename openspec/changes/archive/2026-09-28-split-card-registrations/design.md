## Context

`tree_cards.py` 目前以四個區段(事件卡 / 魔物卡 / 搭檔卡 / 術卡)依卡號排序登記全部卡片,開頭的說明寫著排版規則。`effects/__init__.py` 匯入它以完成登記。登記順序決定 `reg.START_PHASE` 等表的迭代順序。

## Goals / Non-Goals

**Goals:**

- 依卡片類別分檔,每檔依卡號排序、只含該類別的卡;行為與登記順序不變。

**Non-Goals:**

- 不改任何卡片的登記內容。
- 不再細分(例如依彈別或依掛鉤種類);之後若單一類別仍太長再另案處理。

## Decisions

### 1. 放在 `effects/cards/` 子套件

`effects/cards/{events,mamodo,partners,spells}.py`,由 `cards/__init__.py` 依序匯入。

- **替代方案:平放在 `effects/` 下(`tree_cards_events.py` 等)。** 檔名冗長,且 `effects/` 會混雜機制與逐卡登記;子套件讓「機制」(tree / primitives / registry)與「卡片登記」分開。不採用。
- 檔名與遷移前已刪除的舊 handler 檔(`effects/events.py` 等)相同,但位置不同、內容是效果樹登記;spec 的「沒有逐卡 handler 檔」情境改為以位置與內容描述。

### 2. 登記順序以匯入順序保持

`cards/__init__.py` 依 events → mamodo → partners → spells 匯入,整體登記順序與拆分前(依卡號排序)相同,`reg.START_PHASE` 等表的迭代順序不變。

### 3. 各檔只匯入用到的名稱

拆分時依各檔實際使用的識別字產生匯入清單,避免四個檔各帶一份完整清單。排版規則集中在 `cards/__init__.py` 開頭,各檔開頭只寫一行說明並指向它。
