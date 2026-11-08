# Tasks

## 1. 標題列

- [ ] 1.1 先寫 / 改瀏覽器測試並確認在修改前失敗:標題列沒有行動中標籤、MP、魔書進度、查閱魔書,只有名稱;行動方仍有外框(`test_timing_ui` 改為檢查外框)。
- [ ] 1.2 實作(design D1)。

## 2. 魔書旁的入口與魔書耗盡

- [ ] 2.1 先寫測試並確認失敗:自己的書皮下緣有「查閱魔書」,點擊開網格;對手視角沒有;魔書耗盡時書皮顯示「魔書耗盡」且沒有超出的頁碼(`test_endgame_clarity_ui` 改用書皮)。
- [ ] 2.2 實作(design D2、D3);移除不再使用的 i18n 鍵。

## 3. 驗證與文件

- [ ] 3.1 截圖確認桌面與手機(按鈕不與棄牌區格重疊)。
- [ ] 3.2 快速測試組與相關瀏覽器測試;`openspec validate header-cleanup --strict`。
- [ ] 3.3 更新 `battle-ui/design.md`。
- [ ] 3.4 使用者確認。

## Workflow follow-up

- 歸檔前依指南 §13 同步 delta spec 到主 spec(battle-ui)。
- 歸檔後以 `--no-ff` 合併回 `dev`。
