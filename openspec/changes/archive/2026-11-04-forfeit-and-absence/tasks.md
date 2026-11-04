# Tasks

- [x] 1.1 API 測試:棄權(對手回合也可、NPC 房可、本機房 409、未開局 / 已結束 409、觀戰 403);連續逾時 2 次判定、1 次不判定、自己行動歸零;結束(原因 absent)與限制;繼續等後再逾時 2 次才再判定;雙方都逾時關閉房間與牌桌;不計時房輪到時斷線 60 秒判定、雙方斷線關閉。修改前失敗(端點與檢查函式不存在)
- [x] 1.2 瀏覽器測試:棄權按鈕與確認 / 取消、結算原因;本機與觀戰不顯示;沒有回應的提示與兩個選擇;4404 關閉回首頁。修改前 3 項失敗
- [x] 2.1 引擎 `end_game`、房間欄位、端點與 `check_absence` / `_close_room`(D1–D3)
- [x] 2.2 前端(D4),四語錯誤碼與文字
- [x] 3.1 快速測試組(1530 passed)、全部非 slow 瀏覽器測試(382 passed)與 NPC / 牌桌 / API 測試通過;`openspec validate forfeit-and-absence --strict`
- [x] 3.2 本機實際操作抽查(使用者)
- [x] 3.3 同步 online-room、battle-ui、game-tables 主 spec 與 design
