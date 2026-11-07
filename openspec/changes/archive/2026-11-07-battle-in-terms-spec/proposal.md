# Proposal

## Why

battle-in-options 依規則原文(atwiki「④バトル・インの確認」)把介面、規則頁與 design 的用語改為「進入戰鬥確認 / 同意進入戰鬥」,但各 capability 的規格(spec.md)仍有 17 條需求使用「戰鬥開始確認」「迎戰」。使用者決定另開 change 統一規格的用語(battle-in-options 的「規格用語」後續)。

## What Changes

- 規格中的「戰鬥開始確認」改為「進入戰鬥確認」、「迎戰」改為「同意進入戰鬥」、時機軌的「開始確認」改為「進入確認」、「確認失效」改為規則原文的「確認無效」。只改文字,行為不變。
- 需求或情境的標題含舊用語的 3 條改名(驗證工具不允許在 MODIFIED 中改情境名稱,以刪除舊需求、新增新需求處理,內容不變):
  - `game-engine`「戰鬥開始確認(バトル・イン)」→「進入戰鬥確認(バトル・インの確認)」
  - `battle-ui`「行動選項附註」→「行動選項的附註」
  - `battle-api`「非回合玩家的可用行動快照」→「非回合玩家可用行動的快照」

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `game-engine`、`battle-ui`、`battle-api`、`npc-opponent`、`online-room`:需求文字的用語(行為不變)。

## Impact

- 只改規格文件;測試與程式的說明文字中引用上述需求名稱者一併更新。
