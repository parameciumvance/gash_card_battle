## ADDED Requirements

### Requirement: 魔書中卡片的使用條件
持有者本人視角的快照中,翻開的事件卡與非戰鬥戰術頁 SHALL 附上 `condition_ok`:該卡登記的使用條件目前是否成立(沒有登記條件時為 true)。只反映卡片的使用條件,不含 MP、時機與每回合次數(那些已由其他欄位判斷)。對手與觀戰視角 MUST NOT 含此欄位。

#### Scenario: S-048 沒有可選的對象
- **WHEN** 自己翻開 S-048,魔書中沒有 M-027
- **THEN** 該頁的 `condition_ok` 為 false

#### Scenario: 事件卡的使用條件
- **WHEN** 自己翻開 E-021,場上只有 1 隻魔物
- **THEN** 該頁的 `condition_ok` 為 false;場上有 2 隻時為 true
