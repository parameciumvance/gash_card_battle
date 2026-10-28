## Why

M-027、M-046、M-039 這類卡的效果文都是「MPを1へらす→合計魔力Xで攻撃(防御)する」,是同一種機制:不用戰術卡,以魔物的效果攻擊或防禦(受「魔物の効果を使えない」限制、每回合 1 次)。專案中卻有三種叫法:

- 「無戰術攻擊」:第二彈 M-027 時從引擎角度命名(攻擊宣告沒有戰術卡),用於 game-engine 需求名稱、對峙演出、程式註解與測試。
- 「直接攻擊 / 直接防禦」:放大檢視的按鈕、行動記錄、錯誤訊息、規則頁、部分規格情境。
- 「魔物效果防禦」:第三彈 M-039 時從卡片角度命名,用於 game-engine 需求名稱、對峙演出與記錄。

同一概念多種叫法,玩家與維護者都容易混淆;「無戰術攻擊」只說明它沒有什麼。專案負責人決定統一為「魔物效果攻擊 / 魔物效果防禦」。

## What Changes

- 用語統一:中文「魔物效果攻擊 / 魔物效果防禦」;英文「MAMODO-effect attack / defense」(英文全站以 MAMODO 稱魔物);日文「魔物の効果で攻撃 / 防御」。取代「無戰術攻擊」「直接攻擊 / 直接防禦」「術を使わず攻撃 / 防御」「Attack / Defend without a SPELL」「No-spell attack」「Monster-effect defense」等寫法。
- 需求改名:`game-engine`「無戰術攻擊」→「魔物效果攻擊」(與既有的「魔物效果防禦」成對);`battle-ui`「無戰術攻擊顯示」→「魔物效果攻擊的顯示」。
- 範圍:畫面字串(四語,簡中由工具產生)、規則頁、伺服器錯誤訊息、各 capability 的規格與 design(需求本文與情境名稱)、程式註解、測試的說明與字串斷言。
- 不改:程式識別字與錯誤碼(`mamodo_attack`、`attack.no_mamodo_attack` 等)、事件格式、行為;更新內容(`releases.*.json`)與封存區是歷史紀錄,不改。NPC 程式註解中「直接攻擊」意為「馬上攻擊」,不是這個概念,不改。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `game-engine`:需求「無戰術攻擊」改名為「魔物效果攻擊」;其他需求本文與情境的用語統一。
- `battle-ui`:需求「無戰術攻擊顯示」改名為「魔物效果攻擊的顯示」;其他需求本文與情境的用語統一。
- `card-effects`、`npc-opponent`、`effect-tree`:需求本文與情境的用語統一(不改需求名稱)。

## Impact

- 前端:`frontend/i18n/{zh-TW,en,ja}.json`、`frontend/i18n/rules.{zh-TW,en,ja}.json`(簡中重新產生)。
- 伺服器:`src/gash/engine/engine.py` 錯誤訊息文字與註解,其他模組的註解。
- 規格與 design:`game-engine`、`battle-ui`、`card-effects`、`npc-opponent`、`effect-tree`。
- 測試:說明與斷言畫面字串的測試(`tests/test_level3_ui.py`、`tests/test_showdown_ui.py`、`tests/test_battle_stage_ui.py` 等)。
