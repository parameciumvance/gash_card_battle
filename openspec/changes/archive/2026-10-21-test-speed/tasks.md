## 1. 量測基準

- [x] 1.1 記錄目前全套時間(約 420 秒)與各類別時間,作為比較基準

## 2. 共用瀏覽器與伺服器

- [x] 2.1 `tests/conftest.py`:session scope 的 `server` / `browser`、每個測試的 `page`;`test_cheat_editor.py` 改用 conftest
- [x] 2.2 移除各瀏覽器測試檔對 `test_cheat_editor` fixture 的匯入;確認依賴全新伺服器的檔(如線上人數)維持自己的 fixture
- [x] 2.3 全套通過,記錄時間(Chromium 改回每檔一次,伺服器 session:見 design D1 的修正)

## 3. slow 標記

- [x] 3.1 `pyproject.toml` 登記標記;依 design D2 標記 NPC 自我對戰與動畫類瀏覽器測試
- [x] 3.2 `pytest -m "not slow"` 與全套各跑一次,記錄時間與項數(全套項數不變)

## 3b. browser 標記(使用者追加)

- [x] 3b.1 conftest 自動標記用到 `browser` fixture 的測試;`-m "not slow and not browser"` 的項數與時間

## 4. 文件

- [x] 4.1 AGENTS.md 寫明快速跑法與全套跑法的時機
