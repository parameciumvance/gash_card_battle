# Tasks

## 1. 測試(先寫並確認失敗)

- [x] 1.1 5 張的行為測試:各分支、使用條件不成立時被拒絕(錯誤碼精確)、干擾無效 M-077。

## 2. 實作

- [x] 2.1 M-073(D1)。
- [x] 2.2 M-074 + S-135(D2)。
- [x] 2.3 M-077(D3)。
- [x] 2.4 M-084(D4)。
- [x] 2.5 `pending_cards.json` 移除 5 張;已實作集合;翻譯。

## 3. 驗證與文件

- [x] 3.1 快速測試組、相關瀏覽器測試、新 slow 測試;`openspec validate season4-mamodo-c --strict`。(新測試 18 項,實作前除 2 項對照組外失敗;快速組 2011 項;相關測試檔 94 項(含 test_pending_preview_ui、test_pool_filters_ui);自我對戰 9 局。尚未開放清單清空,相關測試改以 monkeypatch / 攔截 pending_cards.json 模擬)
- [x] 3.2 reconciliation:`card-effects/design.md`、`game-engine/design.md`、capability-map。
- [ ] 3.3 使用者確認。
