## ADDED Requirements

### Requirement: 棄牌事件標明來源魔物槽
場上的卡被棄掉時(搭檔卡以代價棄掉、隨魔物送墓、被效果棄掉;疊放魔物的頂層單獨入墓),`card_discarded` 事件 SHALL 另含該卡所在的魔物槽(`slot`),供前端從原位置播放棄牌演出。魔書中的卡被棄掉時沿用既有的頁碼(`page`)。

#### Scenario: 搭檔隨魔物送墓
- **WHEN** 裝有搭檔的魔物送墓
- **THEN** 搭檔的 `card_discarded` 事件帶該魔物槽的 `slot`

#### Scenario: 效果棄掉搭檔
- **WHEN** 效果棄掉某魔物的搭檔
- **THEN** `card_discarded` 事件帶該魔物槽的 `slot`
