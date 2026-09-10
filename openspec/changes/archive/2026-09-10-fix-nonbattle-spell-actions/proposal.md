## Why

S-026 等非對戰術在卡片詳情被錯誤顯示為攻擊，且指示術識別與目前卡片資料不一致，導致無法從 UI 使用已實作的效果。卡片詳情的卡號也需要清楚可讀，方便玩家核對卡片。

## What Changes

- 非對戰術與事件卡統一顯示「使用」，非對戰術透過既有 use_book_card 指令使用，不提供攻擊或防禦選項。
- 依 effect_icon 分流，涵蓋 S-026、S-041、S-043、S-048、S-057；修正指示術的 コマンド 識別與前端使用條件。
- 快照提供持有者的本回合非對戰術使用卡號紀錄，讓 UI 顯示已使用、MP 不足、時機不符或缺少對應魔物等原因。
- 所有可辨識卡片的詳情清楚顯示卡號，涵蓋盤面與純展示入口、缺圖及窄螢幕。

## Capabilities

### New Capabilities

無。

### Modified Capabilities

- `battle-ui`: 非對戰術的使用入口、禁用原因、正確指示術判定，以及詳情卡號呈現。
- `battle-api`: 持有者快照新增非對戰術使用紀錄，供 UI 重繪與重連恢復。

## Impact

- frontend/app.js、frontend/style.css、frontend/i18n/zh-TW.json，必要時調整 frontend/index.html 的詳情結構。
- src/gash/api/views.py 的視角化快照與對應測試；不新增 API 端點或指令。
- 沿用引擎的效果、費用、回合限制與權限裁決；不修改卡片效果或資料格式，不新增執行期依賴。
