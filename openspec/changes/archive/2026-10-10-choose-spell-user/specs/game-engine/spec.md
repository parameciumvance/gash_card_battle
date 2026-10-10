## ADDED Requirements

### Requirement: 非戰鬥戰術的使用魔物
使用非戰鬥戰術時 SHALL 可指定使用的魔物:指定的魔物 MUST 能使用該戰術(家族相符、戰術相容性擴充,或指令戰術的任一魔物),否則拒絕(`spell.no_mamodo`);費用 SHALL 依指定的魔物計算。未指定時 SHALL 取能使用的魔物中費用最低者。被 E-024 封鎖的魔物 MUST NOT 使用戰術:指定被封鎖的魔物時拒絕(`spell.mamodo_locked`);未指定時不考慮被封鎖的魔物,只有被封鎖的魔物能用時拒絕(`spell.mamodo_locked`)。

#### Scenario: 指定使用的魔物並依其計費
- **WHEN** 一張非戰鬥戰術由自己場上兩隻魔物使用時費用不同(例如指令戰術由受 P-005 影響的スギナ使用時為 0),玩家指定費用較高的魔物使用
- **THEN** 依指定的魔物計費,MP 依此扣除

#### Scenario: 指定不能使用的魔物
- **WHEN** 玩家指定一隻不能使用該非戰鬥戰術的魔物
- **THEN** 被拒絕(`spell.no_mamodo`)

#### Scenario: 只有被封鎖的魔物能使用
- **WHEN** 能使用某非戰鬥戰術的魔物只有一隻,且被 E-024 封鎖
- **THEN** 使用被拒絕(`spell.mamodo_locked`)

### Requirement: 搭檔卡的裝備對象
放出搭檔卡時 SHALL 可指定要裝備的魔物。候選為自己場上對應該搭檔(頂層魔物的對應魔物相符)且尚未裝搭檔的魔物。指定的魔物不對應時拒絕(`play.no_mamodo`),已裝搭檔時拒絕(`play.partner_exists`)。未指定時 SHALL 裝到第一隻候選;有對應的魔物但都已裝搭檔時拒絕(`play.partner_exists`),沒有對應的魔物時拒絕(`play.no_mamodo`)。

#### Scenario: 兩隻對應魔物時指定裝備對象
- **WHEN** 自己場上有兩隻 M-024,玩家放出 P-015 並指定第二隻
- **THEN** P-015 裝在第二隻 M-024 上

#### Scenario: 第一隻已有搭檔時裝到第二隻
- **WHEN** 自己場上兩隻 M-024 中第一隻已裝搭檔,玩家放出另一張對應的搭檔卡且未指定
- **THEN** 裝到第二隻 M-024

#### Scenario: 指定已裝搭檔的魔物
- **WHEN** 玩家指定一隻已裝搭檔的魔物
- **THEN** 被拒絕(`play.partner_exists`)
