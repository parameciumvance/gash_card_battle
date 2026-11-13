# Design

## Decisions

### D1:防禦時機的入口

- 行動欄的 `defense` 分支在「不防禦」之後,依快照的 `any_page_spells` 篩出防 / 攻防圖示的攻防戰術,有的話加一顆按鈕開魔書網格(與攻擊時相同的文字)。網格與卡片選單原本就會依防禦時機提供「防禦」按鈕(`pageButtons` 的 defenseStep),不需更動。
- 可用與否仍由快照決定(引擎的 `_spell_any_page_standby`);前端只依卡片圖示過濾掉不能防禦的,避免出現點進去沒有可按按鈕的入口。
