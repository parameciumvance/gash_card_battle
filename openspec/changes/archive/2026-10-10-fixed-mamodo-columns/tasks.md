## 1. 引擎與快照

- [x] 1.1 先寫測試確認修改前失敗:三隻魔物在 0/1/2 欄,第 0 欄送墓後其餘仍為 1/2;之後放出新魔物在第 0 欄;疊放維持欄位;效果放出(primitives)與分裂(S-043)放在最左空欄;快照三種視角都帶 `column`;沒有欄位的魔物槽在快照中補最左空欄
- [x] 1.2 `MamodoSlot.column`、`place_slot`,替換所有新增魔物槽的地方,`_slot_view` 加 `column`(design D1、D2);1.1 與 `pytest` 引擎測試全過

## 2. 前端

- [x] 2.1 先寫瀏覽器測試確認修改前失敗:左邊魔物送墓後(以金手指或指令製造),原本中間的魔物仍在中間欄,左邊為空的魔物欄
- [x] 2.2 `renderFieldBlock` 依欄位排列(design D3);2.1 全過
- [x] 2.3 使用者在瀏覽器實際操作確認

## 3. Reconciliation 與歸檔(指南 §13)

- [x] 3.1 同步 delta spec 回 `game-engine`、`battle-api`、`battle-ui` 主 spec
- [x] 3.2 Reconcile affected capability design:`game-engine/design.md` 記錄欄位與 `place_slot`;`battle-ui/design.md` 盤面依欄位排列
- [x] 3.3 確認 capability map 不需更新;`openspec validate --all --strict`(與既有基準相比沒有新增失敗)與 `pytest` 全過後歸檔
