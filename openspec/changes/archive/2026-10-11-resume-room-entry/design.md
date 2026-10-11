## Context

- 每個房間的身分存在 `localStorage` 的 `gash-room-<房號>`(`saveSession`:模式、視角、token;觀戰不存)。`resumeRoom(code)` 以它向 `GET /api/rooms/{code}/state` 取快照並接回;失敗時移除記錄。
- `leaveRoom()` 關閉 WS、清除畫面狀態、網址換回 `/`,不通知伺服器、不移除記錄。房間 2 小時無活動才回收。
- 頂欄標題字 `#title` 目前只是圖片。

## Goals / Non-Goals

**Goals:** 首頁可返回進行中的對局;標題字回首頁。

**Non-Goals:** 不改伺服器;不新增「放棄對局」(離開仍不退出);不改「離開房間」按鈕的名稱。

## Decisions

### D1:列出可返回的對局

- `refreshResumeRooms()`:進入首頁時(`show("landing")`)掃描 `gash-room-*`,各以記錄的 token 請求 `/api/rooms/{code}/state`(本機模式用玩家 0 的 token):
  - 請求失敗(房間不存在 / token 無效)→ 移除記錄、不列出;
  - `state.phase === "game_over"` → 不列出(保留記錄,不影響);
  - 其餘列出:模式(`ui.landing.<mode>`)、對手名稱(本機模式不顯示對手)、房號、`第 N 回合` 或「等待對手加入」(`room.started` 為 false)。
- 點選:網址設為 `/?room=<房號>` 後呼叫 `resumeRoom`。
- 並行請求;區塊放在入口卡片上方,沒有項目時隱藏。

### D2:標題字回首頁

`#title` 加 `role="link"`、`tabIndex=0`、點擊 / Enter 呼叫 `goHome()`:在房間中走 `leaveRoom()`;否則網址換回 `/`、`renderLanding()`、`show("landing")`(設定頁、牌組編輯器、等待畫面都適用)。

### D3:手機的標題

窄螢幕原本整個隱藏頂欄標題字;改為只隱藏文字、保留徽章,手機也能點回首頁。

## Risks / Trade-offs

- [瀏覽器記得很多房間時請求多] → 只在進入首頁時查一次;記錄會隨房間回收而清除。
