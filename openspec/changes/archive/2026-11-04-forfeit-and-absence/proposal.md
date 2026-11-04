# Proposal

## Why

使用者要求(v1.3.0 修正線,接在 fix-reconnect 之後):對局可主動棄權;對手沒有回應時提醒並詢問繼續等或結束;雙方都沒有回應時關閉房間與牌桌。目前逾時只會代打、不判負,對手離開後對局會被一直代打到結束,牌桌也一直被佔著。

## What Changes

- 伺服器:棄權端點(對手獲勝,原因 forfeit;本機房不提供);對手沒有回應的判定(計時房連續逾時 2 次、不計時房輪到時斷線 60 秒)公開於房間資訊,另一方可選結束(原因 absent)或繼續等;雙方都沒有回應時關閉房間(WebSocket 以 4404 關閉),牌桌空出。引擎新增 `end_game`。
- 前端:頂欄「棄權」與確認;對手沒有回應時行動欄的提示與兩個選擇;連線以 4404 / 4401 關閉時不重連、回首頁並移除記錄;勝負原因加入棄權與沒有回應;四語。
- 不釋出(使用者指示)。

## Capabilities

### New Capabilities

(無)

### Modified Capabilities

- `online-room`:新增「棄權」「對手沒有回應」「雙方都沒有回應」。
- `battle-ui`:新增「棄權按鈕」「對手沒有回應的提示」「房間關閉」;修改「勝負原因文字」。
- `game-tables`:修改「牌桌房間的回收」(加上因雙方都沒有回應而關閉)。

## Impact

- `src/gash/engine/engine.py`、`src/gash/api/rooms.py`、`src/gash/api/app.py`;`frontend/app.js`、`index.html`、`style.css`、`i18n/*.json`。
- 測試:`tests/test_forfeit_absence.py`(API)、`tests/test_forfeit_absence_ui.py`(瀏覽器)。
