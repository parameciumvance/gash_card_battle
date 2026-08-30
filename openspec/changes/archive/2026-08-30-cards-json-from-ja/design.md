## Context

`data/cards_ja.csv` 現在是乾淨完整的權威來源(135 筆,`related_mamodo_ja`/`related_partner_ja`/`power`/`ad` 等欄位皆已核對過真實頁面、零已知缺漏)。`data/cards.json`(引擎讀取的 `CardDef`)欄位結構與 `cards_ja.csv` 不同,需要一支轉換工具做欄位對應。

已查過 `attr_name` 在整個引擎裡只有 `mamodo.py:322`(`spell_card.attr_name == "Wood"`,M-023 的術相容性檢查)一處讀取,`grep` 全專案(含 frontend)確認沒有任何顯示邏輯讀取它——魔物卡的《技能名》顯示完全由 `cards.zh-TW.json` 的 `attr` 欄位負責(已於 `retranslate-zh-from-ja` 核對過)。這解決了先前探索階段的疑慮:不需要再擴充爬蟲去拆《技能名》成獨立欄位,`attr_name` 在新資料裡只需要正確服務 M-023 這一個讀取點。

`name_en`/`related_mamodo` 在引擎裡有兩種用法:
1. **動態互相比對**(如 `events.py:205`、`engine.py:176`:`game.db[X].name_en == card.name_en`)——語言無關,資料來源換成日文後自動正確,不需要改程式碼。
2. **寫死字面值比對**(如 `mamodo.py:395` 的 `"Zaker" in name_en`)——這才是真正需要逐一修正的地方,已完整列表於 proposal.md。

## Goals / Non-Goals

**Goals:**
- `data/cards.json` 由 `data/cards_ja.csv` 產生,135 筆,數值/行為完全反映權威日文來源。
- 8 個寫死英文字面值的識別比對全部改為對應日文字串,且逐一用真實對局場景(既有測試或手動核對)驗證改對。
- 既有 196 個測試核對過並修正,不因為改資料來源而讓引擎行為意外改變(除了已知的 JA/EN 數值落差修正)。

**Non-Goals:**
- 不重新命名 `CardDef.name_en` 欄位(如改叫 `name`/`name_ja`)。這是純粹的命名清晰度問題,不影響資料正確性,牽動範圍(欄位定義、8+ 處讀取、JSON schema key)會讓這次變更的焦點從「換資料來源」模糊成「順便重構欄位命名」,留待之後單獨評估。這次只要求欄位「裝的值」正確(日文),不要求欄位「名字」跟著改。
- 不處理 `attr_name` 對魔物/夥伴卡的「技能名」語意(維持留空,見 Context)。
- 不刪除 `openspec/specs/card-data/Zatch Bell CCG List for TTS.xlsx` 本體(僅刪除讀它的抽取腳本),保留作為歷史快照。
- ~~不處理 M-007/M-010 等「變身形態要對應回 base 形態」的 `related_mamodo` 遷移~~ ← **實作階段更正**:這件事其實無法略過。`related_mamodo` 是引擎用來比對「魔物卡與其對應術/夥伴卡是否同一家族」的結構性欄位(`engine.py`/`state.py`/`partners.py` 多處動態比對),魔物卡本身的 `related_mamodo` 若沒填對值,M-007/M-010/M-024/M-025/M-027/M-028 這 6 張變身/形態卡的家族比對會直接失效,不是可以留到之後的顯示層問題。實作時發現規則其實很單純:魔物卡的 `related_mamodo` = 該卡 `name_ja` 去除括號後綴(如「（変身後）」「（分身体）」「（完全体）」「（アーマー体）」「（本体）」)後的字串,套用在全部 135 筆上與現有 `data/cards.json` 的英文 `related_mamodo`(如 M-007 "Gofure (Transformed)" → related_mamodo "Gofure")語意完全對應,且已用 `related_mamodo_ja`/`related_partner_ja` 交叉核對過(如 P-004/S-012/S-013 的 `related_mamodo_ja` 皆為「ゴフレ」,與 M-006/M-007 去括號後的「ゴフレ」一致)。不需要人工個案表,`ja-scraper-partner-mamodo` 當初「留給效果內文人工判斷」指的是效果文字本身如何敘述變身關係,與這個結構性 key 欄位無關。

## Decisions

- **新增獨立的轉換工具 `tools/build_cards_json.py`,不擴充 `tools/scrape_ja_effects.py`**:抓取(scrape)與轉換(build)是兩個不同關注點——前者對網路、後者對本機檔案;分開後任一支重跑都不會意外觸發另一支的副作用(如轉換時不小心重新打了 atwiki)。
- **`power` 字串解析規則**(逆轉 `scrape_ja_effects.py` 當初的編碼決定):
  - 純數字(如 `"4000"`,魔物基礎魔力,無加號)→ `{"base": 4000}`
  - 加號+數字(如 `"+4000"`,術的魔力加值)→ `{"bonus": 4000}`
  - `"特殊"` → `{"special": true}`
  - 數字+倍率後綴(如 `"2000×"`,擲幣倍率型)→ `{"special": true, "per_heads": 2000}`
  - 空字串(夥伴/事件卡)→ `{}`
- **`related_mamodo` 依卡片類型分別推導**:術卡/夥伴卡/事件卡直接對應 `related_mamodo_ja`(空字串視為 `None`,對應無指定對象的事件卡);魔物卡沒有 `related_mamodo_ja`(爬蟲規格本就不要求),改用「`name_ja` 去除括號後綴」推導(見上方 Non-Goals 更正說明的驗證結果);指示術(對所有魔物的命令)沿用舊有 `COMMAND_ALL` 機制,由 `related_mamodo_ja == "コマンド"` 判定並填入新的 `COMMAND_ALL = "コマンド"` 常數值。
- **`attr_name` 只在 `type=="spell"` 時填入 `attr_ja`,其餘一律 `None`**:對應 Context 段落的調查結論,只服務 M-023 這一個讀取點,不承擔顯示職責。
- **`image_url` 從現有 `data/cards.json` 逐卡沿用,不重新取得**:`cards_ja.csv` 沒有這個欄位(wiki 卡圖連結是否可用、授權範圍都還沒調查過),沿用舊的 Google Drive 連結是最低風險的做法;S-042 沒有舊值可沿用,`image_url` 為 `null`,由前端既有的「缺圖以文字卡面呈現」機制處理,card-data spec 的「卡圖資產與備援」需求已涵蓋這個情境,不需要新增規格。
- **`sets`(收錄產品清單)比照 `image_url` 從現有 `data/cards.json` 逐卡沿用**:實作階段發現 `frontend/app.js` 直接讀 `/data/cards.json` 的 `sets` 欄位做「依產品篩選」UI,但 `CardDef`(Python 端)並未定義此欄位,proposal/design 原先都沒提到它。`cards_ja.csv` 的 `sets_ja` 是完全不同的日文格式(如 `"LEVEL:2　Rパック・自販機|LEVEL:2　Nスターター"`),與舊有的英文 set 名稱(`"Series 1"`、`"Level 1"`)之間沒有已核對過的對應規則,貿然重新解析風險高於沿用舊值。S-042 沒有舊值可沿用,`sets` 為空陣列 `[]`,前端的產品篩選只是不會把 S-042 列入任何產品分類,不影響其他功能。
- **刪除 `tools/extract_cards.py`,不是標記淘汰或保留**:轉換完成後沒有任何東西再讀 xlsx,留著一支永遠不會被呼叫的腳本只會誤導未來的人以為它還是資料管線的一部分。`openpyxl` 依賴(`pyproject.toml`)一併移除。
- **測試核對原則:數值不同時一律以 `cards_ja.csv` 為準改測試斷言,不回頭改資料**:這是核心需求本身要求的方向(換權威來源),任何測試因此變紅,代表測試斷言記錄的是舊(錯誤)來源的行為,應該修正斷言而非資料。

## Risks / Trade-offs

- **8 個字面值即使全部修正,仍可能有測試沒覆蓋到的路徑(如 M-023/M-029 這類冷門相容性效果平常沒什麼測試案例會觸發)** → 逐一修正後,MUST 針對該識別比對所屬的效果補一個或確認既有一個測試案例會實際執行到該分支,不能只改字串就當作完成。
- **`power` 字串解析是全新程式碼,沒有先例可循** → 用 `data/cards_ja.csv` 全部 135 筆跑過一次轉換,人工核對輸出的 `power` 結構與現有 `data/cards.json`(未受 JA/EN 數值落差影響的卡)逐筆比對是否一致,作為轉換工具本身正確性的驗證手段。
- **刪除 `tools/extract_cards.py` 是不可逆的操作(雖然 git 歷史還在)** → 已確認沒有任何現存流程依賴它(README 的資料管線章節、`AGENTS.md`、CI 都不會呼叫這支腳本),風險低。
