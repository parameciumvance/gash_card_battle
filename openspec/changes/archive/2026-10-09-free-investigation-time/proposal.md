## Why

有玩家把「本機測試模式」當成 NPC 對戰:在本機測試中替對手按了 pass,卻回報成「NPC 在最後一頁可以 0MP 用術卻不用」。這個入口排在 NPC 對戰、與朋友對戰之後,名稱又像一種對戰模式,容易被誤認為有電腦對手。

## What Changes

- 「本機測試模式」對玩家顯示的名稱改為「自由調查時間」(四種語言),包含首頁入口、設定頁標題,以及提到這個模式的錯誤訊息。
- 入口簡介改為強調「沒有電腦對手,在同一畫面操作雙方」(原本是「兩人共用此畫面輪流操作」,沒有點出沒有電腦對手)。
- 首頁入口順序改為:NPC 對戰、與朋友對戰、牌組構築、自由調查時間、規則、意見回報(自由調查時間與牌組構築互換),讓它不再緊接在兩種對戰之後。
- 功能、建房模式(`mode=local`)與入口 id 都不變。規格與程式中的技術名稱「本機房」「本機測試模式」保留,只有顯示名稱改變。
- README 的模式介紹同步改名。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `battle-ui`:「首頁入口」的順序與這個模式的顯示名稱。

## Impact

- 前端:`index.html`(入口順序)、四種語言的 i18n 字典(`ui.landing.local`、`ui.landing.local_desc`、`error.room.not_local`、`error.room.not_joinable`;簡中由 `tools/build_zh_cn.py` 產生)。
- 測試:`tests/test_landing_ui.py` 的入口順序與名稱。
- 文件:README、`battle-ui/design.md`。
- 伺服器、引擎、API 不變。
