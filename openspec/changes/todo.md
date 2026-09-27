- 譯名核對
- 效果核對
- NPC對戰
- history
- 教學
- 商品卡包圖
- 卡片效果結構化
- 無關魔力勝負 on_declare?
- 干擾 回溯?

- 效果樹:其餘 89 張卡的遷移進度改追蹤於 change `effect-tree-migration`
  (`openspec/changes/effect-tree-migration/tasks.md` 為權威進度來源;
  E-020 的既有 MP 分配 bug、E-011 的專屬重試節點需求也記錄在該 change 的 design.md)
- 效果樹:前端 choice.title.* 改為依節點種類命名,取代帶卡號的 e001_pick 等 prompt
- 效果樹:支援會停下的 Standby.then(開始階段待命改為可恢復流程)
