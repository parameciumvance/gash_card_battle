## Context

`tests/test_cheat_editor.py` 定義 `server` / `browser`(module scope)與 `page`,33 個瀏覽器測試檔以 `from tests.test_cheat_editor import browser, page, server` 共用,所以每個檔各啟動一次 uvicorn 子行程與 Chromium(約 3 秒 × 33)。NPC 自我對戰集中在 `test_npc.py`(85 秒)、`test_choice_locations.py`(44 秒)、`test_battle_info.py` 的一項(15 秒)、`test_npc_ui.py`(12 秒)。

## Goals / Non-Goals

**Goals:** 開發中的快速跑法明顯縮短;全套的總時間也縮短;不改任何斷言。

**Non-Goals:** 自我對戰對局共用(要逐項確認覆蓋範圍,之後再評估);平行執行(只有 2 核心)。

## Decisions

### D1:共用的瀏覽器與伺服器
把 `server`、`browser`(含 `_Browser` 包裝與 `SEEN_RELEASE_SCRIPT`)移到 `tests/conftest.py`。`server` 改為 `scope="session"`;`browser` 原本也要改 session,但 Playwright 的同步 API 在主執行緒留著事件迴圈,整個 session 都開著時,之後用 asyncio 的 `test_npc_room` 17 項失敗,所以維持 `scope="module"`(實測後修正);`page` 仍是每個測試一個新的 context(各測試的 localStorage、路由互不影響)。現有的 `from tests.test_cheat_editor import ...` 改為直接使用 conftest 的 fixture(移除匯入),避免同名 fixture 被模組重新定義成 module scope。
- 風險:測試之間共用伺服器的房間狀態。現有測試各自建立新房間,且伺服器狀態原本就跨同一檔的測試共用,所以行為不變;若有測試依賴「全新的伺服器」(例如線上人數),在該檔保留自己的 module fixture。

### D2:`slow` 標記
`pyproject.toml` 登記 `markers = ["slow: ..."]`。標成 slow 的:NPC 自我對戰(`test_npc.py` 整檔、`test_choice_locations.py` 的自我對戰項、`test_battle_info.py` 的自我對戰項、`test_npc_ui.py` 整檔),以及單項超過約 2 秒的動畫 / 聚焦類瀏覽器測試(`test_showdown_ui.py`、`test_spotlight_ui.py` 等整檔)。預設仍跑全部;快速跑法 `pytest -m "not slow"`。

### D2b:`browser` 標記(使用者 2026-10-21 追加)
`tests/conftest.py` 的 `pytest_collection_modifyitems` 把用到 `browser` fixture 的測試自動標 `browser`,不改測試內容。只改引擎 / 卡片 / API 時跑 `-m "not slow and not browser"`。

### D3:跑法寫進 AGENTS.md
開發中改程式後跑 `pytest -m "not slow"` 加上與改動相關的檔;tasks 的「pytest 全過」與歸檔 / 提交前跑全套。

## 實測(2026-10-21,2 核心)

| 跑法 | 項數 | 時間 |
|---|---|---|
| 改動前全套 | 1302 | 約 420 秒 |
| 改動後全套 | 1302 | 約 380 秒 |
| `-m "not slow"` | 1258 | 約 181 秒 |
| `-m "not slow and not browser"` | 1022 | 約 8 秒 |

