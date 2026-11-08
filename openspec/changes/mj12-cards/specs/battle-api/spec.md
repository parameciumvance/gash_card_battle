## ADDED Requirements

### Requirement: 獨立卡區快照
每位玩家的快照 SHALL 含 `field_cards`:依出場順序的獨立卡區卡片 `{uid, card, ability_used}`,對所有視角公開;持有者另含 `ability_block`(效果目前不能使用的原因代碼,同魔物槽)。翻開頁的 MJ12 SHALL 對持有者附 `play_block`(與 `play_card` 同一判斷)。

#### Scenario: 場上的 MJ12
- **WHEN** 自己場上有 MJ-004 且本回合已使用
- **THEN** 雙方的快照都列出該卡且 `ability_used` 為真;只有自己的快照有 `ability_block`
