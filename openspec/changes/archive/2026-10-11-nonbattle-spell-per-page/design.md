## Context

- `PlayerState.used_nonbattle_spells: set[str]`(卡號),`_use_book_card` 檢查與記錄,回合結束清除;快照只給持有者;前端 `nonbattleUsable` 以 `entry.card` 判斷。
- 戰鬥戰術以 `spell_page_uses: dict[頁, 次數]` 計次,上限由 `spell_use_limit`(M-024 的ビライツ每張 2 次)決定,快照 `used_spell_pages`。

## Goals / Non-Goals

**Goals:** 非戰鬥戰術每頁每回合一次。

**Non-Goals:** 不併入 `spell_page_uses`(那是戰鬥戰術的計次,上限掛鉤只為戰鬥戰術設計,混用會讓非戰鬥戰術受 M-024 影響);不改事件卡每回合一張的規則。

## Decisions

### D1:改以頁記錄

`used_nonbattle_spells` 改為 `used_nonbattle_pages: set[int]`,檢查與記錄都用頁碼;回合結束照舊清除。快照欄位同步改名為 `used_nonbattle_pages`,值為頁碼。改名而不沿用舊欄位放頁碼,避免卡號與頁碼混用。

### D2:前端

`nonbattleUsable` 改以 `entry.page` 是否在 `used_nonbattle_pages` 判斷。

## Risks / Trade-offs

- [其他地方依卡號讀 `used_nonbattle_spells`] → 以 grep 全部替換;測試涵蓋快照、引擎、瀏覽器。
