# Tasks

## 1. 核對重組前後等價

- [x] 1.1 以腳本比對:原 5 條說明的每一句都逐字出現在新需求中,只有 design 第 3、4 點的三處例外;原 12 個情境逐字出現且各只在一條需求,另加 3 個新情境
- [x] 1.2 確認新情境描述的是現有行為:`python -m pytest tests/test_level3.py -k "m041 or s070_attacker or m039_mamodo_defense" -q` 通過
- [x] 1.3 確認各卡歸屬的家族與 `data/cards.json` 的 `related_mamodo` 一致(事件卡為 null),以腳本列出 12 條需求中每個卡號的家族
- [x] 1.4 `openspec validate card-effects-family-requirements --strict` 通過

## 2. Reconciliation 與歸檔(指南 §13)

- [x] 2.1 同步 delta spec 回 `card-effects` 主 spec,把新需求移回原需求的位置;再套用一次 delta 結果相同(歸檔不會重複套用);`openspec validate --all --strict` 通過且沒有新增說明過長的提示
- [x] 2.2 Reconcile `card-effects/design.md`:第三彈第 1 / 2 / 4 批「效果文解讀」的「相關規格」改指向新需求名稱;決定、理由、確認狀態不變;行為沒有改變,不新增行為決定
- [x] 2.3 以 5 個舊需求名稱 grep `openspec/specs`、`openspec/capability-map.md`、`docs`、`tests`、`src`,確認只剩封存區;確認 capability map 不需更新
- [x] 2.4 `todo.md` 移除「規格整理:card-effects 以批次命名的解讀需求…」一項
- [x] 2.5 依使用者指示歸檔並提交
