## 1. 先寫測試

- [x] 1.1 瀏覽器測試(寬螢幕與窄螢幕):以金手指或指令讓一隻魔物負傷,量測橫卡外框寬高比約 1.4、寬度不超過魔物欄;欄內有與健康卡同尺寸的直式虛線框且中心與橫卡對齊;回復健康後恢復直放、無虛線框
- [x] 1.2 確認新測試在修改前失敗(比例與虛線框)

## 2. 實作

- [x] 2.1 `style.css`:負傷尺寸變數(由 `--cell-w` 推得)、負傷卡旋轉不縮放、懸停樣式、虛線直框樣式
- [x] 2.2 `app.js`:魔物欄在負傷時渲染虛線直框與橫卡
- [x] 2.3 以截圖在桌面與手機尺寸目視確認十字樣式,給專案負責人確認(截圖已送出)

## 3. Reconciliation 與歸檔(指南 §13)

- [ ] 3.1 同步 delta spec 回 `battle-ui` 主 spec
- [ ] 3.2 Reconcile affected capability design and rationale(`battle-ui` 尚無 design.md;確認不需新增)
- [ ] 3.3 Update capability map(確認無需變更)
- [ ] 3.4 從 `openspec/changes/todo.md` 移除「UI負傷橫向顯示」
- [ ] 3.5 `openspec validate --all --strict`、`python -m pytest` 全過後歸檔
