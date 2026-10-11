## 1. 實作

- [x] 1.1 先寫測試確認修改前失敗:M-011 在對手魔書沒有魔物時使用成立、發出檢視事件、沒有棄卡、算使用過;E-016 沒有可選戰術卡時使用成立、檢視、不棄卡、MP 只減少 E-016 本身的費用、算本回合使用過事件卡;E-017 在對手魔書沒有事件卡時快照 `condition_ok` 為 true 且使用成立;有對象時原本的行為不變(既有測試)
- [x] 1.2 移除 M-011 的 `condition`、E-016 / E-017 的 `when`(design D1);1.1 與 `pytest` 全過

## 1b. 前端顯示整本

- [x] 1.3 先寫瀏覽器測試確認修改前失敗:沒有可選的卡時自動開啟唯讀網格、顯示整本卡面、標題註明、關閉後清除;有決策時不自動開啟,開啟後非候選頁也有卡面、只有候選頁發光
- [x] 1.4 前端記下 `book_revealed`、`showBookReview` 顯示整本、i18n(design D3,簡中以工具產生);1.3 全過
- [x] 1.5 檢視阻塞對手(design D4):先寫引擎測試(沒有對象時停在 `end_book_review`、選項附整本卡面、對手不能行動、結束後完成;唯一對象也由玩家選),修改前失敗;實作 `Choose.auto_single`、`AwaitBookReviewEnd`、`HasOptions.test`;更新依賴自動選的既有測試(P-013、E-017);前端結束檢視按鈕、開啟對手魔書按鈕、決策結束後網格關閉,i18n;全部測試通過
- [x] 1.6 自動開啟(design D5):先寫瀏覽器測試(M-025 式棄牌區 → 魔書空頁依序自動開啟、關閉後同一決策不再跳出、場上目標不自動開啟),修改前失敗;實作 `autoOpenPick`;既有瀏覽器測試全過
- [x] 1.7 使用者在瀏覽器實際操作確認(線上或 NPC 對戰的 M-011;M-025)

## 2. Reconciliation 與歸檔(指南 §13)

- [x] 2.1 同步 delta spec 回 `card-effects`、`battle-ui` 主 spec;`battle-ui/design.md`「決策互動」的魔書網格說明改為自動開啟規則、對手魔書顯示整本
- [x] 2.2 `card-effects/design.md`「行為決定與理由」新增本決定(design D2,Confirmed)
- [x] 2.3 確認 capability map 不需更新;`openspec validate --all --strict`(與既有基準相比沒有新增失敗)與 `pytest` 全過後歸檔
