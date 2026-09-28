## 1. P-018 第一頁可用(行為變更)

- [x] 1.1 以依效果文的測試取代 `test_p018_not_usable_on_first_page`:第一頁可用、棄掉卡片、不回翻、不觸發對手 P-019、之後同回合回翻效果不發生(第二張同卡號的 P-018 原本就被每回合一次的規則擋下,不在此驗證);E-005 在第一頁回翻 0 張後 P-018 仍可用
- [x] 1.2 確認新測試在修正前失敗
- [x] 1.3 修改 P-018 / P-010 的使用條件(拿掉 `pos > 2`,改為檢查「用過或已受限制」),全部測試通過

## 2. Spec 補充

- [x] 2.1 `card-effects` delta:P-018 第一頁可用、S-026 / S-057 不詢問、回翻 0 張不算用過
- [x] 2.2 `game-engine` delta:非回合玩家不能宣告攻擊
- [x] 2.3 更新 `effect-tree`、`docker-deployment`、`standalone-release` 的 `## Purpose`(直接修改主 spec,寫明 scope)
- [x] 2.4 補上情境的測試:非回合玩家不能宣告攻擊(`test_engine.py`,原本沒有測試)、S-057 擲出正面時沒有 pending(原本只隱含於後續 pass 成功)

## 3. Capability design 與 capability map

- [x] 3.1 建立 `game-engine/design.md`、`effect-tree/design.md`、`card-effects/design.md`,內容取自 `openspec/design.md`,解讀依指南 §7.4 格式與核可的確認狀態改寫
- [x] 3.2 刪除 `openspec/design.md`
- [x] 3.3 建立 `openspec/capability-map.md`
- [x] 3.4 補 `effect-tree` 慣例需求的靜態測試(節點名稱不含卡號、註冊檔依卡號排序且無邏輯、沒有逐卡 handler 檔),覆蓋程度才能標為 Documented

## 4. Agent 與工具設定

- [x] 4.1 `AGENTS.md`:規格流程改為指向指南;卡片效果規則中的解讀紀錄改為依指南 §7
- [x] 4.2 `openspec/config.yaml`:context 與 tasks 規則依指南 §13、§16
- [x] 4.3 README 的文件指引加入 capability map,移除 `openspec/design.md`

## 5. Reconciliation 與歸檔(指南 §13)

- [x] 5.1 同步 delta spec 回主 spec
- [x] 5.2 Reconcile affected capability design and rationale(本 change 的決策 2、3 已反映在 `card-effects/design.md`)
- [x] 5.3 Update capability map(覆蓋程度反映本 change 的結果)
- [x] 5.4 `openspec validate`、`python -m pytest` 全過後歸檔
