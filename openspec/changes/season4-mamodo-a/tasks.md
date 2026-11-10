# Tasks

## 1. 測試(先寫並確認失敗)

- [x] 1.1 15 張的行為測試:各分支、使用條件不成立時被拒絕(錯誤碼精確)、選擇者、常駐效果被「使えない」擋下。

## 2. 實作

- [x] 2.1 MP 增加的限制(D4)。
- [x] 2.2 干擾的費用棄卡依 zone、`opponent_turn`、分開計次(D5)。
- [x] 2.3 魔物效果攻擊的條件、Ex-061 的再用(D1、D7)。
- [x] 2.4 M-071、M-072、P-045 的觸發與擲硬幣(D2、D3、D8)。
- [x] 2.5 M-081、M-082、M-083、M-078、P-050 與登記(D6、D9)。
- [x] 2.6 `pending_cards.json` 移除 15 張;已實作集合;前端標籤。

## 3. 驗證與文件

- [x] 3.1 快速測試組、相關瀏覽器測試、新 slow 測試;`openspec validate season4-mamodo-a --strict`。(新測試 32 項,實作前除對照組外失敗;快速組 1945 項;相關瀏覽器測試 116 項;自我對戰 9 局)
- [x] 3.2 reconciliation:`card-effects/design.md`、`game-engine/design.md`、capability-map。
- [ ] 3.3 使用者確認。
