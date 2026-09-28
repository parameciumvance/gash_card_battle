## Why

`effect-tree-interpreter`(已歸檔 `openspec/changes/archive/2026-09-23-effect-tree-interpreter/`)建立了效果樹架構並遷移了 6 張卡,之後又以直接提交(不開 change)分兩批遷移了 12 張卡,共 18 張。剩餘 **89 張卡、90 個掛鉤**仍是舊的「一卡一函式 + 字串 key」寫法,分散在 `mamodo.py`(29 卡)、`partners.py`(19 卡)、`events.py`(22 卡)、`spells.py`(19 卡)。

這是一個會橫跨很多次工作階段(session)才能做完的長期遷移,需要一個持續開啟、不隨每個 commit 關閉的 change 來:

- 記錄「已完成 / 剩餘」的權威進度(目前只靠 commit message 與 README 一句話帶過,無法一眼看出整體進度或哪些卡還沒動)。
- 記錄遷移過程中發現的既有邏輯缺陷與需要專屬節點設計的卡,避免下次工作階段重新踩雷(E-020 的 MP 分配 bug、E-011 的付費重擲迴圈已各撞過一次)。
- 讓每次工作階段都能從 `tasks.md` 直接挑下一批,不需要重新盤點剩餘清單。

## What Changes

- 新增本 change 作為效果樹遷移的**總覽與進度追蹤**;`tasks.md` 依來源檔案(events / mamodo / partners / spells)列出全部 89 張剩餘卡,每張一個 checkbox,遷移完成即勾選並補上完成的 commit。
- `design.md` 記錄遷移的分批策略、每批的既有作法(遷移前先補特徵測試、能通用就通用節點、不行就開專屬節點、遷移前後可觀察行為必須一致)、以及已知阻礙卡(E-020、E-011)的處理方式。
- 本 change 會維持開啟狀態,直到 89 張卡全部遷移完(或明確決定不遷移的卡都已在 `design.md` 記錄原因)才歸檔。

## Capabilities

### New Capabilities
(無)

### Modified Capabilities
- `effect-tree`:「效果樹與既有註冊方式並存」補上逐批遷移的不變性;遷移過程新增的節點能力(Coin 由對手擲幣、付費重擲節點、以對手視角執行子樹、When 的 otherwise、rider 的 on_win / on_defense_damaged 樹入口、註冊檔逐卡集中登記與排版)寫成對應需求。
- `card-effects`:遷移中發現 E-018、E-027 的實作與日版效果文不一致(E-020 另有 MP 給錯人的 bug),經使用者同意依效果文修正;第二彈需求補上具體情境。

## Impact

- 程式:`src/gash/engine/effects/{mamodo,partners,events,spells}.py` 逐步清空,對應內容搬進 `tree.py`(新節點)與 `tree_cards.py`(逐卡註冊)。
- 測試:每批遷移前為缺測試的卡補特徵測試,遷移後新增節點單元測試;現有測試數量會隨每批增加。
- 無新增外部依賴、無 API 格式變動;前端只新增新選擇種類的 i18n 標題(`frontend/i18n/zh-TW.json`)。
