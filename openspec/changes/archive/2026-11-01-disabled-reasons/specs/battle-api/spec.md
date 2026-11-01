## ADDED Requirements

### Requirement: 效果的使用可否快照
持有者本人視角的快照中,場上魔物槽 SHALL 附上 `ability_block`(頂層魔物的啟動效果)與 `partner_ability_block`(搭檔的啟動效果),玩家 SHALL 附上 `borrowed_block`(本回合借用的搭檔效果):目前不能使用時為原因代碼,可以使用或沒有該效果時為 null。代碼依指令的檢查順序取第一個:`partner_restricted`(搭檔效果失效)、`mamodo_locked` / `mamodo_restricted`(魔物效果被封鎖)、`timing_battle`(只能戰鬥中)、`timing_nonbattle`(只能非戰鬥中)、`own_turn`(只能自己的回合)、`used`(本回合已使用)、`per_game`(一場限 1 次已使用)、`mp`(MP 不足)、`condition`(使用條件不成立)。判斷 MUST 與 `use_field_ability` / `use_borrowed_effect` 指令相同,不含行動權(是否輪到該玩家、是否在等決策)。對手與觀戰視角 MUST NOT 含這些欄位。

#### Scenario: 只能戰鬥中的效果
- **WHEN** 非戰鬥中,自己場上的魔物有只能在戰鬥中使用的效果
- **THEN** 自己視角該槽的 `ability_block` 為 `timing_battle`;對手視角沒有這個欄位

#### Scenario: 使用條件不成立
- **WHEN** 自己場上有 M-030,魔書沒有翻開到最後一頁
- **THEN** 該槽的 `ability_block` 為 `condition`

#### Scenario: 可以使用
- **WHEN** 效果的時機、次數、MP 與條件都符合
- **THEN** `ability_block` 為 null,即使現在輪到對手行動
