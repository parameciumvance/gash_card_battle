## 1. 準備

- [x] 1.1 scratchpad 腳本列出 197 張的日文 / 繁中 / 英文(另以腳本偵測句型與「」的不一致)

## 2. 翻譯

- [x] 2.1 繁中:design 表列的意思出入逐張改成直譯;另外 E-030(漏「選び」)、P-040 / PR-001(「術1つ」譯成「1張戰術」)、M-043(「1つ」)一併直譯
- [x] 2.2 繁中:固定句型統一(D2)、卡名補「」;逐張人工檢查。第 1、2 彈若有不一致一併修正並列在這裡(合計 93 張;第 1、2 彈只有 M-030「不翻魔書直接結束回合」多了「直接」,改為「不翻魔書就結束回合」)
- [x] 2.3 英文:197 張逐張核對,有偏差的改成直譯(有效果文的 190 張;修正 5 張:E-040 漏「選び」、Ex-047 多了「must」、M-032 漏「1つ」、S-067 / S-097 漏「できる」)
- [x] 2.4 `python tools/build_zh_cn.py` 重新產生簡中
- [x] 2.5 翻譯中若發現實作差異,記入 `implementation-diffs.md`(沒有發現,不建立此檔)

## 3. 驗證

- [x] 3.1 `python -m pytest tests -m "not slow and not browser" -q` 通過;寫死舊譯文的測試依新譯文更新(1409 passed,沒有寫死舊譯文的測試)
- [x] 3.2 全套 `python -m pytest tests -q` 通過;`openspec validate --all --strict` 與基準相比沒有新增失敗(全套 1459 passed、327 skipped:容器重建後 venv 沒有 playwright,瀏覽器測試全被略過;重新安裝 playwright 與 chromium-headless-shell 後另跑 `-m browser` 341 passed。`openspec validate`:battle-api、battle-ui、card-data 三個規格失敗,與基準相同)
- [x] 3.3 產生對照表(日文 / 舊繁中 / 新繁中 / 英文變更)給使用者抽查
- [x] 3.4 本機實際操作抽查(使用者)

## 4. Reconciliation(指南 §13)

- [x] 4.1 同步 delta spec 到 `openspec/specs/card-data/spec.md`
- [x] 4.2 `openspec/specs/card-data/design.md`「卡片文字檔」:記錄固定譯法對照表;「翻譯狀態」更新第 3 彈之後已依直譯核對
