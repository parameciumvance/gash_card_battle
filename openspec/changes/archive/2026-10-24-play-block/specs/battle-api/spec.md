## ADDED Requirements

### Requirement: 魔書中卡片的放出可否
持有者本人視角的快照中,翻開的魔物頁與搭檔頁 SHALL 附上 `play_block`:目前不能放出時為 `play_card` 會回傳的錯誤碼(不含 `play.` 前綴,例如 `spell_only`、`no_base`、`field_full`、`same_name`、`no_mamodo`、`partner_exists`),可以放出時為 null。判斷與 `play_card` 指令相同,只反映卡片與場面,不含時機(是否輪到該玩家行動)。搭檔頁 SHALL 另附 `targets`:可裝備的自己魔物槽 uid 清單(對應且尚未裝搭檔,家族依視為的名稱判定)。對手與觀戰視角 MUST NOT 含這些欄位。

#### Scenario: 只能經戰術疊放的魔物
- **WHEN** 自己翻開 M-046,場上有ウマゴン
- **THEN** 該頁的 `play_block` 為 `spell_only`

#### Scenario: 場上魔物已滿
- **WHEN** 自己場上已有 3 隻魔物,翻開另一張非疊放的魔物卡
- **THEN** 該頁的 `play_block` 為 `field_full`

#### Scenario: 疊放型沒有可疊的魔物
- **WHEN** 自己翻開 M-007,場上沒有ゴフレ
- **THEN** 該頁的 `play_block` 為 `no_base`;場上有 M-006 時為 null

#### Scenario: 同名魔物已達上限
- **WHEN** 自己場上已有 1 隻ガッシュ・ベル,翻開另一張ガッシュ・ベル(非疊放型)
- **THEN** 該頁的 `play_block` 為 `same_name`

#### Scenario: M-047 視為ガッシュ・ベル時的搭檔
- **WHEN** 自己場上的ガッシュ・ベル疊著 M-047 且未裝搭檔,翻開對應ガッシュ・ベル的搭檔卡
- **THEN** 該頁的 `play_block` 為 null,`targets` 含該魔物槽

#### Scenario: 對手視角不含
- **WHEN** 對手的翻開頁因 P-024 對自己公開
- **THEN** 那些頁不含 `play_block` 與 `targets`
