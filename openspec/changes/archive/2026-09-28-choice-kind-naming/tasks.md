## 1. 先寫測試

- [x] 1.1 靜態測試:`tree_cards.py` 的 `prompt` 不含卡號;所有決策種類(效果樹 + 引擎內建)都有 `choice.title.<kind>`
- [x] 1.2 行為測試:E-001 與 E-009 的 pending `kind` 都是 `pick_own_mamodo`;E-016 與 E-017 都是 `pick_opponent_book_card`
- [x] 1.3 UI 測試:決策對話框顯示通用標題與來源卡名稱、效果文;沒有來源卡時不顯示該區塊
- [x] 1.4 確認 1.1 的命名測試、1.2、1.3 在修改前失敗(1.1 的 i18n 標題測試是防護,修改前後都應通過)

## 2. 改名

- [x] 2.1 `tree_cards.py` 的 prompt 依 design 決策 1 對照表改名
- [x] 2.2 `rooms.py` 逾時預設:`e011_retry` → `paid_reflip`
- [x] 2.3 `frontend/i18n/zh-TW.json`:移除以卡號命名的 `choice.title.*`,加入通用標題
- [x] 2.4 更新引用舊種類名稱的測試

## 3. 對話框顯示來源卡

- [x] 3.1 `index.html` 加入來源卡區塊,CSS 樣式(窄螢幕可讀)
- [x] 3.2 `app.js`:`showDialog` 接受來源卡,`renderPendingDialog` 傳入 `pending.source`
- [x] 3.3 指令術選魔物的對話框(`pickSlotThen`)原本借用 E-009 的標題「選擇本回合 +3000 的魔物」,改用專屬標題 `ui.pick_command_user`
- [x] 3.4 全部測試通過;以瀏覽器截圖確認桌面與窄螢幕的對話框呈現

## 4. 文件

- [x] 4.1 `AGENTS.md`:決策種類依選擇內容命名、先沿用既有種類;新增種類才補 i18n
- [x] 4.2 `openspec/changes/todo.md` 移除「choice.title.* 改為依節點種類命名」

## 5. Reconciliation 與歸檔(指南 §13)

- [x] 5.1 同步 delta spec 回主 spec
- [x] 5.2 Reconcile affected capability design and rationale:`effect-tree/design.md` 移除「prompt 含卡號」的已知限制,補上決策種類的命名方式
- [x] 5.3 Update capability map(確認後無需變更:effect-tree 新需求有測試,仍為 Documented;battle-ui / battle-api 仍為 Partial)
- [x] 5.4 `openspec validate`、`python -m pytest` 全過後歸檔
