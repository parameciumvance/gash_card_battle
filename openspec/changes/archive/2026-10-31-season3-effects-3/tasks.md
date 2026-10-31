## 1. 測試先行

- [x] 1.1 `tests/test_season3_effects_3.py`:12 張每張至少一個依效果文寫的行為測試(可選效果的使用 / 不使用、選擇者、使用條件的錯誤碼、合計 1 次、最後一頁除外);執行並確認修改前失敗
- [x] 1.2 機制測試:Ex-046 依序放出與重算、排除疊放、無法放 2 隻時被拒絕;M-062 只棄掉 / 只放出 / 棄掉唯一魔物後必須放出 / 不能使用;P-036 以棄掉後的場面判斷;PR-007 該頁變空頁;game-engine「棄掉後再放出同編號的卡」被拒絕;確認修改前失敗(既有行為的測試除外)
- [x] 1.3 `tests/test_restriction_kinds.py`:守門測試(效果文字樣 ↔ 推導結果 / 排除名單)與 FAQ 清單核對;確認修改前失敗

## 2. 引擎機制

- [x] 2.1 `RESTRICTION_KINDS`、節點的 `restricts` 屬性、登記表的種類、`restriction_kinds(number)`(design D1);守門測試通過
- [x] 2.2 `DeployableMamodoInOwnBook(no_stack=True)` 與「放出後仍有第 2 張」的過濾(D2)
- [x] 2.3 M-062 的棄掉與放出流程(D3)
- [x] 2.4 `AttachablePartnerPagesInOwnBook(excluding_self=True)`(D4)
- [x] 2.5 `DiscardThisEventFromBook`(D5)

## 3. 卡片登記

- [x] 3.1 12 張登記於 `effects/cards/` 對應檔案(依卡號排序)
- [x] 3.2 `data/pending_cards.json` 移除 12 張;`tests/test_season3_cards.py` 的開放張數更新;`python -m pytest tests -m "not slow and not browser" -q` 全過

## 4. 前端與 NPC

- [x] 4.1 新的選項或記錄文字(zh-TW / en / ja,`build_zh_cn.py` 產生 zh-CN),新的決策種類補 `choice.title.<kind>`;規則頁「效果」一節補「相同編號的卡算同一個效果」(四語);相關瀏覽器測試通過
- [x] 4.2 NPC 自我對戰牌組含這批卡不卡住(slow 自我對戰測試)

## 5. 驗證

- [x] 5.1 全套 `python -m pytest tests -q` 通過;`openspec validate --all --strict` 與基準相比沒有新增失敗
- [x] 5.2 本機實際操作抽查(使用者)

## 6. Reconciliation(指南 §13)

- [x] 6.1 同步 delta spec 回 `card-effects`、`game-engine` 主 spec
- [x] 6.2 `card-effects/design.md`:「行為決定與理由」加入這批的解讀(依 design D7 的狀態)、限制種類的推導;`game-engine/design.md`:每回合 1 次以卡號計(規則書第 20 頁)
- [x] 6.3 capability map 視需要更新

## Workflow follow-up

- 歸檔:`openspec archive season3-effects-3 --skip-specs -y`(主 spec 已手動同步),在 `season3-effects-3` 分支提交;合併 main 與推送等使用者指示
