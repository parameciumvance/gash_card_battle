# Tasks

## 1. 先寫依回報情境的測試

- [x] 1.1 `tests/test_npc.py` 新增測試:玩家 0 場上有ガッシュ・ベル(先放)與ロブノス,以ロブノス的戰術(S-042)宣告攻擊;NPC(玩家 1,`normal`)翻開頁有 E-024 並插入;斷言 NPC 對 E-024 的選擇以ロブノス為第一候選。確認修正前失敗(目前選ガッシュ・ベル)
- [x] 1.2 新增測試:插入行動使宣告作廢後,`Determinizer` 的已知頁含該戰術頁;攻擊方翻頁使該頁不再翻開、或回合結束後不再含。確認修正前失敗

## 2. 引擎記錄被打斷的攻擊宣告

- [x] 2.1 `GameState` 新增 `interrupted_attack`(預設 None);狀態只在記憶體、以 deepcopy 複製(NPC 副本、ジャマー快照),確認這兩處都會帶上新欄位;`python -m pytest tests/test_engine.py -q` 通過
- [x] 2.2 `_battle_in_response` 插入行動時記錄 `{attacker, page, mamodo_attack, slot, turn_no}`;`_declare_attack` 開始時清除;新增 `interrupted_attack(game, player)` 回傳有效記錄或 None(回合相同、戰術頁仍翻開)。以單元測試驗證記錄、清除與有效範圍

## 3. NPC 使用記錄

- [x] 3.1 `determinize.known_opponent_pages` 加入對手有效記錄中的戰術頁;1.2 的測試通過;既有的資訊隱藏測試(`test_hidden_information_never_changes_decisions` 等)通過
- [x] 3.2 `settle.respond` 對非 NPC 一方加入重新宣告規則;1.1 的測試通過;新增「不影響攻擊的插入行動」測試:對手宣告攻擊時,NPC 插入不影響攻擊的行動後,模擬中對手重新宣告(以 `settle` 直接驗證對手送出的指令)
- [x] 3.3 `python -m pytest tests/test_npc.py tests/test_npc_room.py -q` 全部通過(含自我對戰);記錄單次決策時間與修正前的比較

## 4. Reconciliation 與歸檔(指南 §13)

- [x] 4.1 同步 delta spec 回 `npc-opponent` 主 spec;`openspec validate --all --strict` 通過
- [x] 4.2 更新 `npc-opponent/design.md`:已知頁加上被打斷的宣告頁;回應規則加上重新宣告;已知限制補充「模擬中的對手只會重試被打斷的那次攻擊,不會從零挑選新的攻擊」;「行為決定與理由」新增「被打斷的攻擊宣告在當回合仍屬看得到的資訊」(使用者於 2026-10-28 explore 確認);確認 capability map 不需更新
- [x] 4.3 `todo.md` 移除「NPC 達爾丹尼安沒選擇有戰術的羅布諾斯」
- [x] 4.4 依使用者指示歸檔並提交
