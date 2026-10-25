## ADDED Requirements

### Requirement: 魔力明細快照
快照中每隻場上魔物 SHALL 附 `power_breakdown`:逐項明細(`kind`、`source` 卡號或 null、`amount`),各項 `amount` 加總等於該魔物的 `power`,與魔力勝負明細的魔物部分相同(魔物的魔力、常駐效果、持續效果、設為某值、不低於 0 等)。場上魔物的魔力是公開資訊,所有視角都提供。

#### Scenario: 常駐效果的加成
- **WHEN** 場上的 M-003 負傷
- **THEN** 該魔物的 `power` 為 5000,`power_breakdown` 為魔物的魔力 4000 與 M-003 常駐效果 +1000

### Requirement: 費用明細快照
快照中帶 `cost` 的翻開頁(戰術頁、事件頁)SHALL 同時附 `cost_breakdown`(`kind`、`source`、`amount`),各項加總等於 `cost`:卡面費用、最後一頁(ADV)使本來費用為 0、本來費用為 0 的效果(S-088、P-005 等)、待命的費用加減(M-008 等)、對手 M-040 等的事件卡費用增加、費用不低於 0。戰術頁的明細對應 `cost` 所取的那隻使用魔物。可見範圍與 `cost` 相同。

#### Scenario: M-040 使事件卡費用增加
- **WHEN** 對手場上有 M-040,自己翻開費用 1 的事件卡
- **THEN** 該頁的 `cost` 為 2,`cost_breakdown` 為卡面 1 與 M-040 +1

#### Scenario: 最後一頁
- **WHEN** 自己翻到最後一頁,該頁的戰術卡面費用為 3
- **THEN** 該頁的 `cost` 為 0,`cost_breakdown` 為卡面 3 與最後一頁 -3

### Requirement: 傷害被防止事件的來源
`damage_prevented` 事件 SHALL 在由效果防止時附 `source`(造成防止的卡號):魔物的不受傷害效果(M-031、M-051、M-053、M-047 等)為該魔物的卡號,持續效果(M-013、M-015、S-037 等)與保護時不受傷害(S-079)為其來源卡。對象已消失而作廢的傷害沒有 `source`。

#### Scenario: M-031 擋下傷害
- **WHEN** 合計魔力 6000 以下的戰術傷害以 M-031 為對象
- **THEN** `damage_prevented` 的 `source` 為 M-031

### Requirement: 失效中的常駐效果快照
快照中每隻場上魔物 SHALL 附 `blocked_effects`:該魔物頂層與搭檔中,「このカードが場にある→」的效果目前被「使えない」擋下者,每項為 `card`(卡號)與 `by`(造成限制的來源卡號清單,依限制的建立順序)。沒有失效的效果時為空清單。只列持續中或之後仍可能發動的常駐效果;出場時的效果(已解決)與效果文寫明「使えないときにも使える」者(M-038)不列。限制是公開資訊,所有視角都提供。

#### Scenario: E-025 使 M-031 失效
- **WHEN** 對手使用 E-025,玩家場上有 M-031
- **THEN** M-031 的 `blocked_effects` 為 `[{card: "M-031", by: ["E-025"]}]`

#### Scenario: E-008 使搭檔失效
- **WHEN** E-008 生效中,玩家場上的魔物裝有 P-030
- **THEN** 該魔物的 `blocked_effects` 含 `{card: "P-030", by: ["E-008"]}`

#### Scenario: 已解決的出場效果不列
- **WHEN** 玩家受 E-025 限制,場上有 M-006
- **THEN** M-006 的 `blocked_effects` 為空

### Requirement: 一次性時點的效果被擋下事件
出場時、捨て札になったとき、開始階段的常駐效果,以及魔物的不受傷害效果,在該時點因「使えない」而不發動時,引擎 SHALL 發出 `effect_blocked` 事件(`player`、`card`、`slot`、`by` 來源卡號清單、`when`:`play` / `discard` / `start_phase` / `damage`)。傷害免疫只在「沒被擋下就會免疫」時發出。觸發型常駐效果(事件發生時)被擋下時 MUST NOT 發出此事件。

#### Scenario: M-031 的免疫被擋下
- **WHEN** 玩家受 E-025 限制,合計魔力 6000 以下的戰術傷害以 M-031 為對象
- **THEN** 發出 `effect_blocked`(`card` M-031、`by` 含 E-025、`when` damage),M-031 受到傷害

#### Scenario: 不會免疫的傷害不發出
- **WHEN** 玩家受 E-025 限制,合計魔力 7000 的戰術傷害以 M-031 為對象
- **THEN** 不發出 `effect_blocked`

#### Scenario: 觸發型不發出
- **WHEN** 持有 P-013 的玩家受「パートナーの効果を使えない」限制,對手的魔物卡入墓
- **THEN** 不發出 `effect_blocked`,也不翻頁
