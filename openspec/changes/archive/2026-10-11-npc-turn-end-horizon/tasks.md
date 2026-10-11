## 1. 實作

- [x] 1.1 先寫測試確認修改前失敗:魔書剩餘頁數少、賈修裝著 P-001、沒有付得起的攻擊戰術時,`decide` 的第一名不是使用 P-001;有付得起的賈修攻擊戰術時,P-001 候選的評分包含之後攻擊的結果(不低於只 pass)
- [x] 1.2 `settle.turn_end_value` / `finish_turn`,`decide` 改用(design D1);既有 NPC 測試全過;量測 `decide` 時間(design D2);同時修正以送出前回合為停點(D1b)、平手處理(D1c),更新「有機會致勝時攻擊」測試
- [x] 1.3 使用者實際對戰確認

## 2. Reconciliation 與歸檔(指南 §13)

- [x] 2.1 同步 delta spec 回 `npc-opponent` 主 spec
- [x] 2.2 `npc-opponent/design.md` 的停點與評估說明補延伸評估
- [x] 2.3 確認 capability map 不需更新;`openspec validate --all --strict`(與既有基準相比沒有新增失敗)與 `pytest` 全過後歸檔
