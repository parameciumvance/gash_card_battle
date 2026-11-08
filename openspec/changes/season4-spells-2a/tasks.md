# Tasks

## 1. 測試(先寫並確認失敗)

- [x] 1.1 依效果文的行為測試:8 張各自的正反分支、使用條件不成立被拒絕(錯誤碼精確)、選擇者與非法選擇、被無效時限制解除、S-146 放回與搭檔、Ex-063 追加與否。

## 2. 實作

- [x] 2.1 引擎:限制的 `lift_side`(design D1)、`spell_names_by_turn`、`declare_condition` / `once_per_turn`(D4)、`defense_extra_cost`(D5)。
- [x] 2.2 節點與登記(D1〜D5);i18n 追加費用選項文字。
- [x] 2.3 `pending_cards.json` 移除 8 張;已實作集合。

## 3. 驗證與文件

- [x] 3.1 快速測試組、相關瀏覽器測試、新 slow 測試;`openspec validate season4-spells-2a --strict`。(新測試 31 項,實作前 24 項失敗;快速組 1788 項;相關瀏覽器測試 204 項;自我對戰 9 局。構築器 LEVEL:4 已開放的卡加上這批)
- [x] 3.2 reconciliation:`card-effects/design.md`、`game-engine/design.md`。
- [ ] 3.3 使用者確認。
