## Why

`data/cards.json`(引擎讀取的權威數值/行為資料)目前仍由 `ref/raw`(現已搬到 `openspec/specs/card-data/`)的 xlsx 英文資料抽取而來,但這條來源已被證實不可靠——S-017 的自身魔力加值觸發時機、E-027 的費用、M-013 的基礎魔力都曾發現與已核對過真實頁面的權威日文來源(`data/cards_ja.csv`)不一致。`cards.zh-TW.json` 的翻譯層已改以 `cards_ja.csv` 為準(見 `retranslate-zh-from-ja`),但 `cards.json` 本身——真正驅動遊戲數值與規則判定的資料——還沒跟上,兩份資料實質上已經分岔。核心需求很單純:**把 `cards.json` 的權威來源整個從 xlsx 換成 `cards_ja.csv`**,底下的欄位轉換、識別字串修正、測試核對都只是這件事的子步驟,不是各自獨立、可以分別決定要不要做的選項。

## What Changes

- 新增轉換工具,由 `data/cards_ja.csv`(135 筆,含 S-042)產生 `data/cards.json`:
  - `power` 統一字串欄位解析回 `{base/bonus/special/per_heads}` 結構(依格式標記:純數字→base、加號→bonus、「特殊」→special、數字+倍率後綴→special+per_heads)。
  - `ad`/`class`/`cost`/`damage` 直接對應。
  - `attr_name` 只在術卡填入元素(`attr_ja`);魔物/夥伴卡的 `attr_name` 留空——已確認此欄位在引擎裡只有 M-023 一處讀取(檢查術卡是否為「木」屬性),從未被當成顯示欄位讀取,魔物卡的《技能名》顯示完全由 `cards.zh-TW.json` 的 `attr` 欄位負責。
  - `image_url` 逐卡從現有 `data/cards.json` 沿用舊值(`cards_ja.csv` 沒有這個欄位);S-042 是新卡,沒有舊值可沿用,`image_url` 留空(前端既有的缺圖容錯機制會以文字卡面呈現,不是新問題)。
  - S-042 隨著整批轉換自然併入 135 張,不特判、不額外處理。
- 修正寫死英文字面值的身分識別比對,改為對應的日文字串。原提案估計 8 個/約 15 處呼叫點,實作階段對 `mamodo.py`/`partners.py` 全文重新 grep 後,發現另有 3 組遺漏(`"Gofure"`、`"Sugino"`、`"Fein"`——P-004/M-007 相容判定、M-007/P-005 的須基納家族、P-007 的菲恩家族),實際合計 11 組字面值、18 處呼叫點:`"Command: All"`→`コマンド`、`"Wood"`→`木`、`"Zatch Bell"`→`ガッシュ・ベル`、`"Zaker"`→`ザケル`、`"Tia"`→`ティオ`、`"Hyde"`→`ハイド`、`"Sugino"`→`スギナ`、`"Gofure"`→`ゴフレ`、`"Fein"`→`フェイン`、`"Brago"`→`ブラゴ`、`"Biraitsu"`→`ビライツ`,分布於 `cards.py`/`mamodo.py`/`partners.py`。其餘「拿卡片自己的欄位值互相動態比對」的地方(如 `events.py`/`engine.py` 數處 `name_en == name_en`)不需要修改,語言無關。
- 淘汰舊的 xlsx 抽取管線:刪除 `tools/extract_cards.py`(不再有任何東西呼叫它,成為死程式碼);`openspec/specs/card-data/Zatch Bell CCG List for TTS.xlsx` 保留作為歷史快照,不刪除。
- 重新產生 `data/cards.json` 後,核對 196 個既有測試;因數值差異(已知至少 E-027/M-013)導致的斷言錯誤,一律以 `cards_ja.csv` 的值為準修正測試,不得為了讓測試通過而回頭竄改資料。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `card-data`:「卡片資料抽取」需求(xlsx → cards.json)REMOVED,以「卡片資料轉換」(cards_ja.csv → cards.json)ADDED 取代,標誌權威來源正式從英文切換為日文。

## Impact

- 新增轉換工具(暫定 `tools/build_cards_json.py`,或直接擴充 `tools/scrape_ja_effects.py` 的輸出後處理——留待 design.md 決定)
- `data/cards.json`:全面重新生成,134→135 筆
- `src/gash/engine/cards.py`/`effects/mamodo.py`/`effects/partners.py`:8 個字面值修正
- `tools/extract_cards.py`:刪除
- `tests/test_cards.py` 等既有測試:核對數值差異後修正受影響的斷言
- 不影響:`data/cards.zh-TW.json`(已於前一變更完成)、`tools/scrape_ja_effects.py`(輸入端不變)
