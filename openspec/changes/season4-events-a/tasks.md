# Tasks

## 1. 測試(先寫並確認失敗)

- [x] 1.1 依效果文的行為測試:9 張的主要分支、使用條件不成立被拒絕(錯誤碼精確)、選擇者(PR-013 由對手先選)、非法選擇保留 pending、Ex-071 對常駐 / 啟動 / 之後裝上的搭檔。

## 2. 實作

- [x] 2.1 引擎:`EFFECTS_LOCKED` 與 `partner_effect_block_sources`(D1)、`battle_phase_mp_lost`(D4)、`has_discard_cost_effect`(D3)。
- [x] 2.2 節點與登記(D2、D3、D4)。
- [x] 2.3 `pending_cards.json` 移除 9 張;已實作集合。

## 3. 驗證與文件

- [x] 3.1 快速測試組、相關瀏覽器測試、新 slow 測試;`openspec validate season4-events-a --strict`。(新測試 23 項,實作前全部失敗;快速組 1841 項;相關瀏覽器測試 246 項;自我對戰 9 局。金手指 / 構築器的產品與 LEVEL:4 測試改為依資料計算預期值,之後分批開放不必再改)
- [x] 3.2 reconciliation:`card-effects/design.md`、`game-engine/design.md`。
- [ ] 3.3 使用者確認。
