# Tasks

## 1. 引擎與快照

- [x] 1.1 先寫測試並確認修改前失敗(`tests/test_effect_visibility.py`):`damage_prevented` 的 `source`(M-031、M-051、M-013 / M-015 類、S-037 類、S-079)、魔物的 `power_breakdown` 加總等於 `power`(M-003 負傷、M-014、E-001 類持續效果、P-011 設為某值)、翻開頁的 `cost_breakdown` 加總等於 `cost`(卡面、最後一頁、S-088 / P-005、M-008 類待命、M-040)、對手視角看不到翻開頁內容時也沒有 `cost_breakdown`
- [x] 1.2 `engine.py`:費用明細(`spell_cost_breakdown` / `event_cost_breakdown`,`spell_cost` / `event_cost` 改由它們取數字)、`damage_prevented` 的 `source`;既有費用相關測試不變,快速層通過
- [x] 1.3 `views.py`:`power_breakdown`、`cost_breakdown`(含 `any_page_spells`);1.1 全過
- [x] 1.4 先寫測試並確認修改前失敗:`blocked_effects`(E-025 → M-031 by E-025、E-024 只限一隻、E-008 → 搭檔、P-031 家族、M-006 / M-038 不列、沒限制時為空)、`effect_blocked` 事件(M-007 出場、M-009 入墓、M-002 開始階段、M-031 會免疫時才發、P-013 不發)
- [x] 1.5 `engine.py` 的 `effect_block_sources`(`card_effect_blocked` 改由它判斷)、`reg.PASSIVE_TABLES`、各時點的 `effect_blocked`;`views.py` 的 `blocked_effects`;1.4 全過,快速層通過

## 2. 前端:數值分色與明細

- [x] 2.1 先寫瀏覽器測試並確認修改前失敗:M-003 負傷的魔力為綠色、M-040 使事件卡費用為紅色、相同時不著色;放大檢視列出明細、相同時不列;M-031 受 E-025 時顯示「失效」標記,放大檢視列出失效的效果與原因
- [x] 2.2 `cardEl` 數值分段與著色(`style.css` 淺 / 深色 token)、失效標記、`renderZoom` 明細區與失效中的效果、`breakdown.*` 等 i18n(zh-TW / en / ja,`tools/build_zh_cn.py`);2.1 通過

## 3. 前端:效果來源卡聚焦與記錄

- [x] 3.1 先寫瀏覽器測試並確認修改前失敗:對手的 P-013 因自己的行動翻自己的魔書時出現 P-013 卡片格;自己的 M-002 開始階段 +1 MP 出現卡片格;使用的事件卡自己的效果不另起格;`damage_prevented` 帶來源時記錄寫出卡名;`effect_blocked` 的記錄與卡片格
- [x] 3.2 `anim.js` 的 `effectSource` 與 `timeline` 另起卡片格;`TEXT_EVENTS` 加入傷害被防止 / 無效、MP 增減被擋下;`app.js` 的 `log.damage_prevented_by`、`log.effect_blocked`(i18n 同上);3.1 與既有聚焦測試(`test_spotlight_ui.py`)通過

## 4. 驗證與收尾

- [x] 4.1 全套 `python -m pytest tests -q` 通過;`openspec validate --all --strict` 沒有新增失敗
- [x] 4.2 Reconciliation:`battle-api/design.md` 記明細欄位與 `damage_prevented.source`;`battle-ui/design.md` 的「對手行動聚焦展示」補效果來源卡格的條件、「卡片元件」補數值分色;`todo.md` 移除「常駐效果/作用中效果生效時醒目」

## Workflow follow-up

- 使用者指示後歸檔並提交。
