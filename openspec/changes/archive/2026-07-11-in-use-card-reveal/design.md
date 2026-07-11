# Design: in-use-card-reveal

## Context

`views.py` 為視角過濾單點(不變量:不存在「先送全量、前端隱藏」)。`snapshot` 已公開 `battle_in`(含 `spell` 卡號與 `page`)與 `battle`(含 `attack_spell`/`defense_spell` 卡號);引擎 `Battle` 另有 `attack_page`/`defense_page`。`_player_view` 目前對非持有者一律只送頁碼。行動記錄為 i18n 模板 + `cname()` 內插的純文字(`textContent`);放大檢視已支援純展示模式(無 ctx 無按鈕)。

## Goals / Non-Goals

**Goals:**
- 宣告中的攻防術在魔本上翻正(所有視角),戰鬥結束自動恢復卡背。
- 記錄與對決舞台的卡名可點開檢視。
- 揭露邏輯只存在於 `views.py`;不動引擎。

**Non-Goals:**
- 事件卡揭露(使用即解決,無時間窗;記錄可點已補足回看)。
- 歷史揭露記憶(「曾經看過的頁」不持久標示;超出原規則)。

## Decisions

### D1. 揭露判定:`_player_view` 計算 `in_use_pages(p)`

集合構成:`st.battle_in` 且 `attacker == p` → `{battle_in["page"]}`;`st.battle` 時 `attacker == p` → `attack_page`、`defender == p` → `defense_page`(None 過濾,無術攻擊無頁)。翻開頁迴圈中,`page ∈ in_use_pages` 時即使 `not can_see_player` 也送 `{"page", "card", "cost?"}`,並附 `"in_use": true`(持有者視角同樣附標,供前端高亮)。戰鬥結束 `battle=None` → 集合為空 → 自然恢復。

替代:前端從 `battle` 狀態自行對映頁號(battle 已公開 spell 卡號)——需另送 attack/defense 頁號且揭露邏輯散到前端,違反單點不變量,否決。

### D2. 前端呈現:走既有 `openPageEl` 路徑 + `in_use` 高亮

對手使用中頁的 entry 含 `card` → `renderBookBlock` 既有分支自動渲染卡面;`entry.in_use` 時加 class(金色描邊/發光)標示「使用中」。檢視面板 `zoomActions(kind:"page")` 對非控制者生成零按鈕(既有 `iControl`/`canActNow` 守衛),自動成為純展示。

### D3. 記錄卡名可點:條目後處理包 span

`appendLog` 每條:先以模板產出純文字,再取事件的卡號欄位(`card`/`spell`/`source`/`top`/`partner` 等存在者),對每一卡號把行內**首次出現**的 `cname(num)` 片段以 DOM 分割方式包成 `<span class="card-ref" data-num>`(splitText,不用 innerHTML,維持注入安全),click → `zoom(num)`。找不到片段(模板未含該名)則跳過。對決舞台的攻防術名以同一 helper 處理。

替代:整條可點——一條多卡時語意含糊,否決;模板改標記語法——動全部 i18n 條目,成本高,否決。

### D4. 觀戰與本機

觀戰視角同樣適用揭露(宣告本就公開);本機模式全視角本就可見,僅多 `in_use` 高亮。

## Risks / Trade-offs

- [揭露頁判定漏歸屬(攻/防頁掛錯玩家)] → 單元測試覆蓋:攻方頁只在攻方 view、防方頁只在防方 view。
- [卡名片段比對失敗(模板不含名/重複名)] → 找不到即跳過(退回純文字),重複名只包首個——可接受的近似。
- [`in_use` 標記洩漏節奏資訊?] → 否:battle 狀態本就公開宣告內容與頁號歸屬。

## Migration Plan

純增量:後端揭露 → 前端高亮 → 記錄可點。各步獨立可回滾。

## Open Questions

(無)
