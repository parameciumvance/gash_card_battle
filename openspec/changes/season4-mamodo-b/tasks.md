# Tasks

## 1. 測試(先寫並確認失敗)

- [x] 1.1 12 張的行為測試:各分支、使用條件不成立時被拒絕(錯誤碼精確)、常駐效果被「使えない」擋下時不作用。

## 2. 實作

- [x] 2.1 不能被選擇(D1、D2)。
- [x] 2.2 Ex-051、Ex-053、Ex-054(D3~D5)。
- [x] 2.3 Ex-059、M-070、M-079(D6、D7)。
- [x] 2.4 P-047、P-048、P-049、PR-012(D8~D10)。
- [x] 2.5 `pending_cards.json` 移除 12 張;已實作集合;翻譯。

## 3. 驗證與文件

- [x] 3.1 快速測試組、相關瀏覽器測試、新 slow 測試;`openspec validate season4-mamodo-b --strict`。(新測試 26 項,實作前除對照組外失敗;快速組 1973 項;相關瀏覽器測試 109 項;自我對戰 9 局。尚未開放卡的瀏覽器測試改用 M-073)
- [x] 3.2 reconciliation:`card-effects/design.md`、`game-engine/design.md`、capability-map。
- [ ] 3.3 使用者確認。
