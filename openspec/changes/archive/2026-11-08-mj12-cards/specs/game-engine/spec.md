## ADDED Requirements

### Requirement: 獨立卡區與 MJ12
MJ12 卡 SHALL 依規則頁:自己或對手的戰鬥階段(非戰鬥中)以 1 個行動從自己魔書今のページ放出,不裝在魔物上,放進該玩家的獨立卡區;每回合張數不限;同名的 MJ12 在自己場上限 1 張(`play.same_name`)。場上 MJ12 的效果以 `use_field_ability`(`zone: "field"`)使用,雙方的戰鬥階段皆可、每個效果每回合 1 次;沒有戰鬥圖示的效果只在非戰鬥中。「このカードを捨て札にする→」先把該卡移入棄牌區再解決。MJ12 的效果 MUST NOT 被「魔物の効果を使えない」「パートナーの効果を使えない」擋下。

#### Scenario: 對手回合放出 MJ12
- **WHEN** 對手的戰鬥階段非戰鬥中輪到自己行動,今のページ有 MJ-004
- **THEN** 自己可以放出 MJ-004,它進入自己的獨立卡區

#### Scenario: 同名限 1 張
- **WHEN** 自己場上已有 MJ-001,今のページ又有一張 MJ-001
- **THEN** 放出被拒絕(`play.same_name`)

#### Scenario: 每回合 1 次
- **WHEN** 本回合已用過 MJ-004 的效果
- **THEN** 再使用被拒絕(`ability.used`)

#### Scenario: 戰鬥中不能使用
- **WHEN** 戰鬥中的「效果的使用」時機
- **THEN** 使用 MJ12 的效果被拒絕(`ability.timing`)
