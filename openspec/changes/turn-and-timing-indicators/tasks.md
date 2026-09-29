## 1. 先寫測試

- [x] 1.1 瀏覽器測試:`battle-ui`「回合與時機指示」五個情境與「對手行動聚焦展示」的回合開始橫幅情境,確認修改前失敗

## 2. 實作

- [x] 2.1 `currentTiming()`(design D1)
- [x] 2.2 回合玩家記號、「行動中」標籤、輪到自己時行動欄醒目(design D3)
- [x] 2.3 中線的時機指示(design D2),含窄螢幕樣式
- [x] 2.4 行動欄摘要與詳細提示、展開狀態記在 localStorage(design D4),i18n
- [x] 2.5 可用卡發光(design D5)
- [x] 2.6 回合開始橫幅,`turn_started` 移出文字聚焦(design D6)
- [x] 2.7 截圖確認桌面與手機的顯示

## 3. Reconciliation 與歸檔(指南 §13)

- [ ] 3.1 同步 delta spec 回 `battle-ui` 主 spec
- [ ] 3.2 Reconcile affected capability design and rationale:`battle-ui/design.md` 補回合與時機指示(時機判斷、可用卡發光)與回合開始橫幅
- [ ] 3.3 Update capability map(確認無需變更)
- [ ] 3.4 `openspec validate --all --strict`、`python -m pytest` 全過後歸檔
