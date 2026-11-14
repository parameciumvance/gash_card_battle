# Tasks

## 1. 標題列

- [x] 1.1 先寫 / 改瀏覽器測試並確認在修改前失敗:玩家區沒有標題列;名稱在中線(我方左、對手右,與時機指示同一列,手機在其上方同一列),行動方名稱標示,以 textContent 呈現;行動方仍有外框(`test_timing_ui` 改為檢查外框)。
- [x] 1.2 實作(design D1)。

## 2. 魔書旁的入口與魔書耗盡

- [x] 2.1 先寫測試並確認失敗:自己的書皮下緣有「查閱魔書」,點擊開網格;對手視角沒有;魔書耗盡時書皮顯示「魔書耗盡」且沒有超出的頁碼(`test_endgame_clarity_ui` 改用書皮)。
- [x] 2.2 實作(design D2、D3);移除不再使用的 i18n 鍵。

## 3. 頂欄的對局狀態

- [x] 3.1 先改測試並確認失敗:頂欄沒有 `#identity` / `#turn-info` / `#phase-info` / `#acting-info`;中線有「第 N 回合」(手機在名稱列中間)、觀戰中;終局資訊與重新開啟按鈕在 `#stage-result`;等待對手決策時行動欄有「對手決策中…」與擲幣結果。
- [x] 3.2 實作(design D4);移除 `ui.you_are`、`ui.acting`。

## 4. 驗證與文件

- [x] 4.1 截圖確認桌面與手機(按鈕不與棄牌區格重疊)。(書皮上下緣的按鈕凸出約 11px,魔書區的列距改為 14px)
- [x] 4.2 快速測試組與相關瀏覽器測試;`openspec validate header-cleanup --strict`。(快速組 1661 項;非 slow 瀏覽器測試 515 項通過)
- [x] 4.3 更新 `battle-ui/design.md`。
- [x] 4.4 使用者確認。(2026-11-08 使用者同意歸檔)

## Workflow follow-up

- 歸檔前依指南 §13 同步 delta spec 到主 spec(battle-ui)。
- 歸檔後以 `--no-ff` 合併回 `dev`。
