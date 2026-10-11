## 1. 實作

- [x] 1.1 先寫測試確認修改前失敗:兩張 S-043(不同頁)用了一張後另一張仍可用、用過的那頁被拒絕(`spell.used`);快照 `used_nonbattle_pages` 為頁碼(持有者可見、他方不含)
- [x] 1.2 引擎與快照改以頁記錄(design D1),前端依頁判斷(design D2);更新依卡號的既有測試;`pytest` 全過
- [x] 1.3 使用者在瀏覽器實際操作確認

## 2. Reconciliation 與歸檔(指南 §13)

- [x] 2.1 同步 delta spec 回 `game-engine`、`battle-api`、`battle-ui` 主 spec
- [x] 2.2 `battle-api/design.md`「持有者私有的戰術使用資訊」改為頁碼;`card-effects/design.md`「戰術卡使用次數以頁計數」補非戰鬥戰術
- [x] 2.3 確認 capability map 不需更新;`openspec validate --all --strict`(與既有基準相比沒有新增失敗)與 `pytest` 全過後歸檔
