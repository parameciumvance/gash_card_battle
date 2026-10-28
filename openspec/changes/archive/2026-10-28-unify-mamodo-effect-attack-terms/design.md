## Context

動機見 proposal.md。三種叫法的分布(本 change 開始時盤點):

- 「無戰術攻擊」:`game-engine` 需求名稱與多條需求本文 / 情境、`battle-ui`「無戰術攻擊顯示」、`card-effects` / `npc-opponent` / `effect-tree` 的本文與情境、對峙演出字串 `anim.showdown.no_spell`、引擎與前端註解、測試。
- 「直接攻擊 / 直接防禦」:畫面字串 `ui.mamodo_attack` / `ui.mamodo_defense`、`ui.battle_in_hint_mamodo`、`log.battle_started_mamodo`、`log.battle_in_check_mamodo`、錯誤訊息 `error.attack.no_mamodo_attack` / `error.defense.no_mamodo_defense`(字典與引擎內的中文訊息)、規則頁、`game-engine` 情境與 design、`battle-ui` 情境、測試。
- 「魔物效果防禦」:`game-engine` 需求名稱、對峙演出、記錄 `log.mamodo_defense_declared`。

## Goals / Non-Goals

**Goals:** 同一概念只有一種叫法,畫面、規則頁、規格、design、註解、測試一致。

**Non-Goals:** 不改識別字、錯誤碼、事件欄位與行為;不改更新內容與封存區;不改 NPC 註解中意為「馬上攻擊」的「直接攻擊」。

## Decisions

### 1. 用語對照

| 概念 | 中文 | 英文 | 日文 |
| --- | --- | --- | --- |
| 以魔物效果攻擊 | 魔物效果攻擊 | MAMODO-effect attack | 魔物の効果で攻撃 |
| 以魔物效果防禦 | 魔物效果防禦 | MAMODO-effect defense | 魔物の効果で防御 |

- 句中動詞形照語意改寫,例如「以〔魔物〕直接攻擊」→「以〔魔物〕的魔物效果攻擊」、「不用戰術卡直接攻擊」→「以魔物效果攻擊」、「Attack without a SPELL」→「MAMODO-effect attack」。
- 英文沿用全站以 MAMODO 稱魔物的慣例(既有「MAMODO effects」);上一個 change 加的「Monster-effect defense」一併改正。
- 「魔物效果攻擊」取自卡片本身的性質(它是「魔物の効果」,受「魔物の効果を使えない」限制、每回合 1 次),攻擊與防禦對稱;「無戰術攻擊」只描述引擎層面的「沒有戰術卡」,不採用。

### 2. 需求改名用 RENAMED,本文與情境名稱直接改主規格

- `game-engine`「無戰術攻擊」→「魔物效果攻擊」、`battle-ui`「無戰術攻擊顯示」→「魔物效果攻擊的顯示」以 delta 的 RENAMED 表達。
- 需求本文與情境名稱的用語在 reconciliation 時直接改主規格。OpenSpec 的 MODIFIED 必須帶上主規格既有的全部情境名稱,無法表達情境改名;若以 MODIFIED 改本文、再直接改情境名稱,歸檔時 MODIFIED 區塊的舊情境名稱會與主規格衝突。這與 `spec-scenario-fixes` 直接改主規格情境名稱的做法相同。內容只有用語替換,行為不變。
- 替代方案:REMOVED 各需求再以新名稱 ADDED(可表達情境改名)。會連帶改掉「第二彈 68 種卡全數可用」「ジャマー的使用時機」等不相干的需求名稱,得不償失。

### 3. 需求名稱的引用

改名後更新引用:`card-effects/design.md` 的「`game-engine` › 需求『無戰術攻擊』」等。

## Risks / Trade-offs

- [替換過頭,改到不同意思的「直接」] → 只改明列的詞,逐處檢視上下文;NPC 註解的「直接攻擊」(馬上攻擊)保留,在任務中以 grep 列出殘留並說明。
- [測試以畫面字串斷言] → 同步改測試字串,跑相關瀏覽器測試。
