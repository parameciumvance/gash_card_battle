## ADDED Requirements

### Requirement: 連續 pass 次數快照
狀態快照 SHALL 對所有視角(雙方玩家與觀戰者)公開非戰鬥中雙方的連續 pass 次數:任一方在非戰鬥中 pass 加 1,任一方進行行動或進入新的回合時歸零。這個次數是公開資訊,與引擎判斷「雙方連續 pass 結束戰鬥階段」所用的次數相同;戰鬥中效果步驟的 pass 不計入。

#### Scenario: pass 後次數為 1
- **WHEN** 非戰鬥中回合玩家 pass
- **THEN** 雙方與觀戰者的快照中連續 pass 次數皆為 1

#### Scenario: 行動後歸零
- **WHEN** 連續 pass 次數為 1 時,非回合玩家放了一張卡
- **THEN** 快照中的連續 pass 次數為 0

#### Scenario: 新回合歸零
- **WHEN** 雙方連續 pass,進入下一個回合
- **THEN** 快照中的連續 pass 次數為 0

#### Scenario: 戰鬥中的 pass 不計入
- **WHEN** 戰鬥效果步驟中一方 pass
- **THEN** 快照中的連續 pass 次數不因此增加
