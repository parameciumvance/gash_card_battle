# Tasks

## 1. 測試(先寫並確認失敗)

- [x] 1.1 卡片效果:
  - Ex-000 兩個 ● 的條件、對象、保護;都不能選時被拒絕。
  - Ex-049 封住石版魔物的啟動效果、常駐效果、之後放出的,不影響其他魔物。
  - Ex-069 之後放出的也加、對手的不加、Ex-070 可取除。
  - M-085:E-011、E-022、S-090、E-033、M-025、M-058 與 E-052;M-085 被「使えない」時照常。
  - Ex-056~058 的戰術相容,被 Ex-049 擋下。
- [x] 1.2 瀏覽器:石版標籤;規則頁說明石版魔物、不出現石版狀態。

## 2. 實作

- [x] 2.1 `CardDef.stone_tablet`、`is_stone_tablet`(D1)。
- [x] 2.2 節點、限制旗標、modifier、常駐表與登記(D2~D6)。
- [x] 2.3 前端標籤、i18n、規則頁(D7)。
- [x] 2.4 `pending_cards.json` 移除 7 張;已實作集合。

## 3. 驗證與文件

- [x] 3.1 快速測試組、相關瀏覽器測試、新 slow 測試;`openspec validate season4-stone-tablets --strict`。(新測試 22 項與瀏覽器 2 項,實作前除對照組外全部失敗;快速組 1911 項;相關瀏覽器測試 112 項;自我對戰 9 局。金手指魔物家族的測試改為依資料計算)
- [x] 3.2 reconciliation:`card-effects/design.md`、`game-engine/design.md`、capability-map。
- [x] 3.3 使用者確認。
