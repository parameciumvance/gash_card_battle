# Proposal

## Why

新手試玩回饋(todo「新手評論 10」):「迎戰」之後才選擇防禦,新手以為按「迎戰」就是防禦。「迎戰」是使用者翻譯規則術語「バトル・イン」時的用詞;查 atwiki 規則頁([pages/94](https://w.atwiki.jp/zatchbell/pages/94.html))後,規則原文是:

- 「バトル・インの確認」:回合玩家問非回合玩家「バトル・インしていいですか?」(這個步驟)。
- 「バトル・イン」:回合玩家使用攻擊效果,從非戰鬥中進入戰鬥中。
- 非回合玩家插入行動時,「バトル・イン」の確認は無効になる。

遊戲原本稱這個步驟「戰鬥開始確認」(日文「バトル開始の確認」、英文「BATTLE start check」),也不是規則用語;規則頁的日文翻譯寫「開始の確認」,同樣是專案自己的翻譯。

曾考慮把確認與防禦合併成一步,或提供「進入戰鬥,不防禦」:進入戰鬥後到防禦步驟之間還要處理攻擊的宣告時效果(擲硬幣的「不能防禦」等),無法完全合併;使用者決定不加「進入戰鬥,不防禦」。

## What Changes

- 用語全面依規則原文(使用者採用):步驟名稱「進入戰鬥確認 / バトル・インの確認 / Battle-in check」;非回合玩家的按鈕「同意進入戰鬥 / バトル・インを認める / Allow battle-in」;進入戰鬥「進入戰鬥 / バトル・イン / Battle in」。
- 範圍:行動欄按鈕與附註(「接著宣告防禦或不防禦」)、對決舞台的提示、行動記錄、回合轉盤、詳細提示、錯誤訊息、規則頁(三語,簡中由工具產生)、引擎錯誤訊息,以及程式與測試的註解。過去的更新內容不改。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `battle-ui`:新增「進入戰鬥確認的用語與提示」;修改「行動選項附註」。

## Impact

- `frontend/i18n/*.json`、`frontend/i18n/rules.*.json`、`src/gash/engine/engine.py`(錯誤訊息與註解);各 capability 的 design 改用新用語。
- 測試:新增 `tests/test_battle_in_options_ui.py`;`tests/test_turn_dial_ui.py` 依新文字更新。
