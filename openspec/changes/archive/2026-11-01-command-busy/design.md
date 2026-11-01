# Design

## Context

- 對局指令都經 `send(command)`(`frontend/app.js`):POST `/commands`,回應以 `applyPayload` 套用;錯誤以 toast 顯示。伺服器本來就拒絕不合時機的指令,問題只在前端沒有回饋。
- 操作入口分散:行動欄(`#action-main`,含決策區塊)、決策對話框(`#dialog-overlay`)、放大檢視(`#zoom-actions`,按下即關閉)、場上 / 魔書網格的可選目標(`.pickable`)。

## Decisions

### D1 以全域旗標加 CSS 擋操作

`SENDING`(進行中的指令數)> 0 時在 `<body>` 加 `sending` 類別,CSS 對上述入口設 `pointer-events: none` 並降低不透明度。不逐一改 `disabled`:入口很多且每次重繪都會重建,以 CSS 一處涵蓋,收到回應後重繪時自然恢復。鍵盤操作(Enter / Space 觸發按鈕)另在 `send()` 開頭檢查 `SENDING`,送出中直接忽略,確保不會重複送出。

替代方案:每個按鈕依 `SENDING` 設 `disabled`。不採用:要改所有產生按鈕的地方,漏改就失效。

### D2 延遲顯示「處理中…」

送出後 200 毫秒仍未回應才在行動欄顯示 `.sending-note`「處理中…」(四語 `ui.sending`),避免本機快速回應時閃一下。回應(成功或失敗)時清除計時器與提示。

### D3 範圍

只包 `send()`:對局指令。金手指(已有 `CHEAT.busy`)、建房 / 加入、牌桌選擇不變。NPC 思考期間的等待提示照舊(那是對手的行動,不是送出中)。

## Risks / Trade-offs

- 回應遺失(連線中斷)時 `fetch` 會拋錯,`finally` 清除送出中狀態,不會卡住。
