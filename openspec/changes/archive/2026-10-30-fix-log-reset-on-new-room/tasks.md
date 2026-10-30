## 1. 測試先行

- [x] 1.1 `tests/test_log_reset_ui.py`:打完一局後回首頁再開好友房，記錄沒有上一局的條目且第一條是「對局開始」;確認修改前失敗

## 2. 修正

- [x] 2.1 `showWaiting` 進入等待畫面時呼叫 `resetLog()`;相關瀏覽器測試(牌桌、首頁、接回)通過

## 3. 驗證

- [x] 3.1 全套 `python -m pytest tests -q` 通過;`openspec validate --all --strict` 與基準相比沒有新增失敗
- [x] 3.2 本機實際操作抽查(使用者)

## 4. Reconciliation(指南 §13)

- [x] 4.1 同步 delta spec 回 `battle-ui` 主 spec;`battle-ui/design.md` 記錄清空的位置與理由
