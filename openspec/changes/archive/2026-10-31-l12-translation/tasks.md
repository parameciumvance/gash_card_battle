## 1. 準備

- [x] 1.1 確認 design D3(戰術卡固定句型是否全部改成直譯)的使用者決定,更新 design 與範圍
- [x] 1.2 scratchpad 腳本列出 135 張的日文 / 繁中 / 英文;抓齊 atwiki 卡頁 FAQ 供翻譯時參考措辭

## 2. 翻譯

- [x] 2.1 魔物卡 31 張:繁中效果文直譯、英文核對
- [x] 2.2 搭檔卡 19 張:同上
- [x] 2.3 事件卡 27 張:同上
- [x] 2.4 戰術卡 58 張:同上(含 D3 決定的固定句型)
- [x] 2.5 `python tools/build_zh_cn.py` 重新產生簡中
- [x] 2.6 翻譯中發現的實作差異記入 `implementation-diffs.md`(魔物卡已決定的 M-001 / M-010 / M-017、M-005、M-031 與不改的 M-020 / M-021、M-025 一併記入)

## 3. 驗證

- [x] 3.1 `python -m pytest tests -m "not slow and not browser" -q` 通過(含 `tests/test_i18n_languages.py`);寫死舊譯文的測試依新譯文更新
- [x] 3.2 卡片顯示相關的瀏覽器測試通過;全套 `python -m pytest tests -q` 通過;`openspec validate --all --strict` 與基準相比沒有新增失敗(1778 passed;`tests/test_cheat_editor.py` 4 項在全套負載下等待逾時,單獨執行修改前後皆 8 passed,與本 change 無關)
- [x] 3.3 產生對照表(日文 / 舊繁中 / 新繁中 / 英文變更)給使用者抽查
- [x] 3.4 本機實際操作抽查(使用者)

## 4. Reconciliation(指南 §13)

- [x] 4.1 同步 delta spec 到 `openspec/specs/card-data/spec.md`
- [x] 4.2 `openspec/specs/card-data/design.md`「卡片文字檔」:記錄直譯原則、用語對照與 D3 的決定;「翻譯狀態」更新第 1、2 彈繁中已依日文重譯
