# Tasks

## 1. 測試先行

- [x] 1.1 引擎測試:先攻第 1 回合翻頁不得 MP(頁照翻、`mp_gained` 0)、後攻第 1 回合照常、先攻第 1 回合結束階段強制翻頁照常 +2、第 3 回合照常;P-035 在先攻第 1 回合記 0。執行並確認修改前失敗
- [x] 1.2 構築驗證測試:同一張 PR 卡 2 張 → `deck.pr_copies`;不同 PR 卡各 1 張通過;同一 Ex 卡 4 張通過;建房 API 回 422 `deck.pr_copies`。執行並確認修改前失敗
- [x] 1.3 構築器瀏覽器測試:同一張 PR 卡放 2 張顯示違規,移掉後消失。執行並確認修改前失敗

## 2. 引擎與驗證

- [x] 2.1 `_flip_pages`:`turn_no == 1` 時翻頁不增加 MP(D2)
- [x] 2.2 `validate_deck`:`PR-` 卡同號 ≤1(D3)
- [x] 2.3 既有測試中依賴先攻第 1 回合翻頁得 MP 的部分逐一調整:只有 `tests/test_api.py::test_token_identity_overrides_payload`(改以頁數判斷翻的是誰的魔書)與 `tests/test_engine.py::test_flip_pages_gains_mp`(改在第 3 回合);開局特性 golden 沒有差異,不需重新產生

## 3. 前端

- [x] 3.1 `frontend/decks.js` 加 PR 檢查;四語 `deck.err.pr_copies`、`error.deck.pr_copies`(簡中由 `tools/build_zh_cn.py` 產生)
- [x] 3.2 規則頁內容檔:開始階段補先攻第 1 回合;新增「魔書構築」段落(D4),三種撰寫語言段落一致
- [x] 3.3 開始階段的翻頁按鈕依回合顯示 MP(先攻第 1 回合為 MP +0),詳細提示在先攻第 1 回合改用 `hint.start_first`(四語);瀏覽器測試(`test_book_browse_ui`、`test_timing_ui`)修改前失敗

## 4. 驗證

- [x] 4.1 快速測試組(1493 passed)、相關瀏覽器測試(`test_tournament_rules`、`test_rules_page`、`test_rules_ui`、`test_builder_card_info_ui`、`test_language_ui`、`test_pool_filters_ui` 共 86 passed)與非瀏覽器的 slow 測試(77 passed,含各批 NPC 自我對戰)通過;`openspec validate --all --strict` 與基準相比沒有新增失敗
- [x] 4.2 本機實際操作抽查(使用者)

## 5. Reconciliation(指南 §13)

- [x] 5.1 同步 delta spec 到 `game-engine`、`card-data`、`deck-builder`、`battle-ui` 主 spec
- [x] 5.2 `game-engine/design.md` 記錄大會規則的出處、不設開關的決定(使用者決定)與「第 1 回合」的判定;`card-data/design.md` 記錄 PR 範圍
