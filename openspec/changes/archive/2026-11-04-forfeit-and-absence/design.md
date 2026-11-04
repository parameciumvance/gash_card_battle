# Design

## Decisions

### D1 結束對局在引擎之外判定

棄權與沒有回應不是遊戲規則的勝負,由房間層判定;引擎提供 `end_game(game, winner, reason)` 呼叫既有的 `_game_over`(發 `game_ended`)。端點走與指令相同的房間鎖與推送,回應格式同指令。

### D2 沒有回應的判定

- 房間記 `timeout_streak`(各座位連續被逾時代打的次數;逾時代打時 +1,自己送出指令時歸零)、`streak_base`(對方選繼續等時的次數)、`absent_since`(沒有連線的開始時刻)、`wait_from`(繼續等的時刻)。
- 計時房:`streak - base >= 2`;不計時房:輪到該方且 `now - max(absent_since, wait_from) >= 60`。連續 2 次而不是 1 次:一次逾時可能只是長考。
- `check_absence` 在每秒的計時迴圈執行,只處理 mode 為 online(含牌桌)且對局中的房間;判定改變時推送房間資訊。

### D3 雙方都沒有回應

計時房雙方 `streak >= 2`(不看繼續等的基準),不計時房雙方都斷線 60 秒:`_close_room` 刪除房間、清空牌桌、以 4404 關閉連線。前端遇到 4404 / 4401 不重連,移除記錄回首頁(4401 原本會無限重連)。

### D4 前端

「棄權」放頂欄(離開房間旁),以決策對話框確認。沒有回應的提示放行動欄最上方,與輪到誰無關都顯示。原因文字 `ui.reason.forfeit` / `ui.reason.absent` 點名敗方,沿用 `endReasonText`。
