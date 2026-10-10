## ADDED Requirements

### Requirement: 戰術頁的可使用魔物
持有者本人視角的快照中,翻開的戰術頁 SHALL 附上可使用此戰術的自己場上魔物清單 `users`:每項含魔物的 `slot_uid`、依該魔物使用時的費用 `cost`、是否被封鎖 `locked`。清單以引擎的戰術相容判定為準(家族相符、戰術相容性擴充;指令戰術為所有魔物)。待命允許從魔書任意頁使用的戰術(P-015)SHALL 以 `any_page_spells` 列出(不含翻開的頁與已離開魔書的頁),每項含頁碼 `page`、卡號 `card`、費用 `cost` 與同樣的 `users`。對手與觀戰視角 MUST NOT 含這些欄位。

#### Scenario: 兩隻魔物都能使用
- **WHEN** 自己場上有賈修與 M-029 ゼオン,翻開一張名為「ザケル」的賈修戰術
- **THEN** 該頁的 `users` 含兩隻魔物,各附其費用

#### Scenario: 名稱只部分相符時不列入
- **WHEN** 自己場上有賈修與 M-029 ゼオン,翻開「バオウ・ザケルガ」
- **THEN** 該頁的 `users` 只有賈修

#### Scenario: 任意頁戰術的頁
- **WHEN** 自己 P-015 的待命生效中,魔書第 20 頁(未翻開、未離開魔書)是「ビライツ」
- **THEN** 快照的 `any_page_spells` 含第 20 頁,附卡號、費用與 `users`;待命用掉或回合結束後不再列出

#### Scenario: 對手看不到
- **WHEN** 對手或觀戰者取得快照
- **THEN** 翻開頁不含 `users`,也沒有 `any_page_spells`
