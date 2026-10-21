## Why

全部測試約 7 分鐘,每個 change 開發中要跑好幾次。量測(2026-10-21,1302 項、約 420 秒)顯示時間主要在兩類固定成本:瀏覽器測試的每個檔各自啟動伺服器與 Chromium(約 100 秒),以及 NPC 自我對戰與動畫等待(約 150 + 160 秒);卡片與規則測試本身很便宜,加卡不會明顯變慢。

## What Changes

- 瀏覽器測試的伺服器與 Chromium 改為整個測試期間共用一次(session scope),不改任何測試內容。
- 新增 `slow` 標記:NPC 自我對戰與動畫類瀏覽器測試標成 `slow`。開發中跑 `pytest -m "not slow"`;歸檔或提交前跑全套。不刪除、不放寬任何測試。
- 在 AGENTS.md 寫明兩種跑法與時機。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

(無:只調整測試的執行方式,不改變系統行為;`.openspec.yaml` 設 `skip_specs: true`)

## Impact

- `tests/conftest.py`(新增:共用的瀏覽器與伺服器 fixture、`slow` 標記)、`tests/test_cheat_editor.py`(fixture 移出)、慢的測試檔加標記、`pyproject.toml`(登記標記)、`AGENTS.md`
