# Tasks

## 1. 測試(先寫並確認失敗)

- [x] 1.1 Ex-060 的行為測試:發動被拒(錯誤碼精確)、既有待命不能從其他頁使用、放出與重疊只剩翻開的頁、E-027 對手受限、M-016 不能用、對手影響持有者魔書不受限、Ex-060 被「使えない」擋下時不作用。

## 2. 實作

- [x] 2.1 常駐效果表與 `outside_page_locked`(D1)。
- [x] 2.2 使用其他頁卡片的效果(D2)。
- [x] 2.3 魔書頁的選項規格(D3)。
- [x] 2.4 `pending_cards.json` 移除 Ex-060;已實作集合;翻譯。

## 3. 驗證與文件

- [x] 3.1 快速測試組、相關瀏覽器測試、新 slow 測試;`openspec validate season4-ex060 --strict`。(新測試 14 項,實作前除 2 項對照組外失敗;快速組 1987 項;相關測試檔 53 項(含瀏覽器的 test_pending_preview_ui、test_nonbattle_ui);自我對戰 9 局,其中 6 局 Ex-060 作用中)
- [x] 3.2 reconciliation:`card-effects/design.md`、`game-engine/design.md`、capability-map。
- [x] 3.3 使用者確認。
