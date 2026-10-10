## MODIFIED Requirements

### Requirement: 非戰鬥戰術的使用魔物
使用非戰鬥戰術時 SHALL 可指定使用的魔物:指定的魔物 MUST 能使用該戰術(家族相符、戰術相容性擴充,或指令戰術的任一魔物),否則拒絕(`spell.no_mamodo`);費用 SHALL 依指定的魔物計算。未指定時 SHALL 以能使用且未被封鎖的魔物中費用最低的第一隻為使用魔物。使用事件(`book_card_used`)SHALL 帶使用魔物的卡號(`mamodo`)。被 E-024 封鎖的魔物 MUST NOT 使用戰術:指定被封鎖的魔物時拒絕(`spell.mamodo_locked`);未指定時不考慮被封鎖的魔物,只有被封鎖的魔物能用時拒絕(`spell.mamodo_locked`)。

#### Scenario: 指定使用的魔物並依其計費
- **WHEN** 一張非戰鬥戰術由自己場上兩隻魔物使用時費用不同(例如指令戰術由受 P-005 影響的スギナ使用時為 0),玩家指定費用較高的魔物使用
- **THEN** 依指定的魔物計費,MP 依此扣除

#### Scenario: 指定不能使用的魔物
- **WHEN** 玩家指定一隻不能使用該非戰鬥戰術的魔物
- **THEN** 被拒絕(`spell.no_mamodo`)

#### Scenario: 只有被封鎖的魔物能使用
- **WHEN** 能使用某非戰鬥戰術的魔物只有一隻,且被 E-024 封鎖
- **THEN** 使用被拒絕(`spell.mamodo_locked`)

#### Scenario: 使用事件帶使用魔物
- **WHEN** 玩家指定賈修使用 S-026
- **THEN** `book_card_used` 事件的 `mamodo` 為賈修的卡號;未指定時為實際採用的魔物
